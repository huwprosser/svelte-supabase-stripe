import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
from routes import payments, telemetry, user
from schemas import AuthUser


class FakeUsers:
    def __init__(self):
        self.docs = {}

    def _get_nested(self, doc, key):
        value = doc
        for part in key.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    def _set_nested(self, doc, key, value):
        target = doc
        parts = key.split(".")
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value

    def _matches(self, doc, query):
        if "$or" in query:
            return any(self._matches(doc, child) for child in query["$or"])
        return all(self._get_nested(doc, key) == value for key, value in query.items())

    def update_one(self, query, update, upsert=False):
        user_id = query["_id"]
        doc = self.docs.setdefault(user_id, {"_id": user_id}) if upsert else self.docs.get(user_id)
        if doc is None:
            return
        if "$setOnInsert" in update and len(doc) == 1:
            doc.update(update["$setOnInsert"])
        if "$set" in update:
            doc.update(update["$set"])

    def update_many(self, query, update):
        for doc in self.docs.values():
            if self._matches(doc, query) and "$set" in update:
                for key, value in update["$set"].items():
                    self._set_nested(doc, key, value)

    def find_one(self, query):
        doc = self.docs.get(query["_id"])
        return dict(doc) if doc else None

    def insert_one(self, doc):
        doc_id = doc.get("_id", str(len(self.docs)))
        if doc_id in self.docs:
            raise DuplicateKeyError("duplicate")
        self.docs[doc_id] = dict(doc)

    def delete_one(self, query):
        self.docs.pop(query["_id"], None)

    def delete_many(self, query):
        for doc_id, doc in list(self.docs.items()):
            if self._matches(doc, query):
                self.docs.pop(doc_id, None)


@pytest.fixture
def users(monkeypatch):
    fake = FakeUsers()
    monkeypatch.setattr(user, "users", fake)
    monkeypatch.setattr(payments, "users", fake)
    monkeypatch.setattr(telemetry, "users", fake)
    return fake


@pytest.fixture
def stripe_events(monkeypatch):
    fake = FakeUsers()
    monkeypatch.setattr(payments, "stripe_events", fake)
    monkeypatch.setattr(user, "stripe_events", fake)
    return fake


@pytest.fixture
def telemetry_actions(monkeypatch):
    fake = FakeUsers()
    monkeypatch.setattr(telemetry, "telemetry_actions", fake)
    monkeypatch.setattr(user, "telemetry_actions", fake)
    return fake


@pytest.fixture
def client(users, stripe_events, telemetry_actions, monkeypatch):
    monkeypatch.setattr(
        user,
        "user_from_authorization_header",
        lambda auth: AuthUser(id="user_123", email="test@example.com"),
    )
    return TestClient(main.app)


def test_plans_are_public_and_include_checkout_shape(client):
    plans = client.get("/plans").json()

    assert client.get("/plans").status_code == 200
    assert {plan["tier"] for plan in plans} == {"free", "plus", "pro"}
    assert all("price_id" not in plan for plan in plans)
    assert any(plan["checkout"] and plan["interval"] for plan in plans)


def test_me_creates_default_user_and_returns_existing_profile(client, users):
    response = client.get("/me", headers={"Authorization": "Bearer token"})
    assert response.json() == {
        "email": "test@example.com",
        "tier": "free",
        "interval": None,
        "tracking_enabled": False,
    }

    users.docs["user_123"].update({"tier": "pro", "interval": "year"})
    response = client.get("/me", headers={"Authorization": "Bearer token"})
    assert response.json() == {
        "email": "test@example.com",
        "tier": "pro",
        "interval": "year",
        "tracking_enabled": False,
    }


def test_export_and_delete_user(client, users, monkeypatch):
    users.docs["user_123"] = {
        "_id": "user_123",
        "email": "test@example.com",
        "tier": "pro",
        "interval": "year",
        "tracking_enabled": True,
    }
    export = client.get("/me/export", headers={"Authorization": "Bearer token"})
    assert export.status_code == 200
    assert export.headers["content-disposition"] == 'attachment; filename="profile-data.json"'
    assert export.json() == {
        "email": "test@example.com",
        "tier": "pro",
        "interval": "year",
        "tracking_enabled": True,
    }

    deleted = []
    monkeypatch.setattr(user, "delete_supabase_user", lambda user_id: deleted.append(user_id))
    response = client.delete("/me", headers={"Authorization": "Bearer token"})
    assert response.json() == {"ok": True}
    assert deleted == ["user_123"]
    assert "user_123" not in users.docs


def test_telemetry_respects_user_tracking_preference(client, users, telemetry_actions):
    response = client.post(
        "/telemetry/action",
        headers={"Authorization": "Bearer token", "User-Agent": "pytest-browser"},
        json={"action": "page_view", "session_id": "session_123", "metadata": {"path": "/"}},
    )
    assert response.json() == {"ok": True, "tracked": False}
    assert telemetry_actions.docs == {}

    response = client.patch(
        "/me/preferences",
        headers={"Authorization": "Bearer token"},
        json={"tracking_enabled": True},
    )
    assert response.json()["tracking_enabled"] is True

    response = client.post(
        "/telemetry/action",
        headers={"Authorization": "Bearer token", "User-Agent": "pytest-browser"},
        json={"action": "page_view", "session_id": "session_123", "metadata": {"path": "/"}},
    )
    saved = next(iter(telemetry_actions.docs.values()))
    assert response.json() == {"ok": True, "tracked": True}
    assert saved["user_id"] == "user_123"
    assert saved["action"] == "page_view"
    assert saved["session_id"] == "session_123"
    assert saved["device"]["user-agent"] == "pytest-browser"


def test_checkout_requires_configured_price_and_sends_expected_stripe_payload(client, monkeypatch):
    created = {}

    def fake_create(**kwargs):
        created.update(kwargs)
        return SimpleNamespace(url="https://stripe.example/checkout")

    monkeypatch.setattr(payments, "price_id_for", lambda tier, interval: "price_plus_month")
    monkeypatch.setattr(payments.stripe.checkout.Session, "create", fake_create)

    response = client.post(
        "/create-checkout-session",
        headers={"Authorization": "Bearer token"},
        json={"tier": "plus", "interval": "month"},
    )

    assert response.json() == {"url": "https://stripe.example/checkout"}
    assert created["line_items"] == [{"price": "price_plus_month", "quantity": 1}]
    assert created["customer_email"] == "test@example.com"
    assert created["client_reference_id"] == "user_123"
    assert created["metadata"] == {
        "user_id": "user_123",
        "tier": "plus",
        "interval": "month",
        "price_id": "price_plus_month",
    }

    monkeypatch.setattr(payments, "price_id_for", lambda tier, interval: "price_replace_plus_month")
    response = client.post(
        "/create-checkout-session",
        headers={"Authorization": "Bearer token"},
        json={"tier": "plus", "interval": "month"},
    )
    assert response.status_code == 500


def test_stripe_webhook_updates_and_resets_subscription(client, users, stripe_events, monkeypatch):
    def fake_construct_event(payload, sig, secret):
        if b"completed" in payload:
            return {
                "id": "evt_completed",
                "created": 123,
                "livemode": False,
                "type": "checkout.session.completed",
                "data": {
                    "object": {
                        "client_reference_id": "user_123",
                        "customer": "cus_123",
                        "subscription": "sub_123",
                        "metadata": {
                            "tier": "pro",
                            "interval": "year",
                            "price_id": "price_pro_year",
                        },
                    }
                },
            }
        if b"deleted" in payload:
            return {
                "id": "evt_deleted",
                "created": 124,
                "livemode": False,
                "type": "customer.subscription.deleted",
                "data": {"object": {"status": "canceled", "metadata": {"user_id": "user_123"}}},
            }
        raise Exception("bad signature")

    monkeypatch.setattr(payments, "STRIPE_WEBHOOK_SECRET", "whsec_valid_secret_for_tests")
    monkeypatch.setattr(payments, "STRIPE_LIVE_MODE", False)
    monkeypatch.setattr(payments, "price_id_for", lambda tier, interval: f"price_{tier}_{interval}")
    monkeypatch.setattr(
        payments.stripe.Subscription,
        "retrieve",
        lambda *args, **kwargs: {
            "status": "active",
            "items": {"data": [{"price": {"id": "price_pro_year"}}]},
        },
    )
    monkeypatch.setattr(payments.stripe.Webhook, "construct_event", fake_construct_event)

    assert client.post("/stripe-webhook", json={"event": "completed"}).json() == {"ok": True}
    assert users.docs["user_123"] | {"_id": "user_123"} == {
        "_id": "user_123",
        "stripe_customer_id": "cus_123",
        "stripe_subscription_id": "sub_123",
        "tier": "pro",
        "interval": "year",
        "subscription_status": "active",
    }

    assert stripe_events.docs["evt_completed"]["processed"] is True

    assert client.post("/stripe-webhook", json={"event": "completed"}).json() == {
        "ok": True,
        "duplicate": True,
    }

    assert client.post("/stripe-webhook", json={"event": "deleted"}).json() == {"ok": True}
    assert users.docs["user_123"]["tier"] == "free"
    assert users.docs["user_123"]["interval"] is None
    assert users.docs["user_123"]["subscription_status"] == "canceled"

    assert client.post("/stripe-webhook", json={"event": "invalid"}).status_code == 400
