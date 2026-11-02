from concurrent.futures import ThreadPoolExecutor
from datetime import date

import mongomock
import pytest
from fastapi import HTTPException

import eligibility
from routes import credits, user
from schemas import AuthUser
from test_main import client, users, stripe_events, telemetry_actions


@pytest.fixture
def clock(monkeypatch):
    today = [date(2026, 11, 2)]
    monkeypatch.setattr(eligibility, "utc_today", lambda: today[0])
    monkeypatch.setattr(credits, "utc_today", lambda: today[0])
    return today


def onboard(client, born="2000-01-01", source="Search"):
    return client.post("/me/onboarding", json={"date_of_birth": born, "discovery_source": source})


def test_age_gate_boundaries_and_validation(client, users, clock):
    assert onboard(client, "2012-11-03").status_code == 403
    assert "onboarding" not in users.docs["user_123"]  # Do not retain underage DOBs.
    assert onboard(client, "2026-11-03").status_code == 403
    for birthday in ["2010-02-30", "invalid", "2010-2-3", 1000]:
        assert onboard(client, birthday).status_code == 422
    for source in ["", "  ", "x" * 121]:
        assert onboard(client, source=source).status_code == 422
    response = onboard(client, "2012-11-02", "  A friend  ")
    assert response.status_code == 200
    assert response.json()["onboarding_complete"] is True
    assert response.json()["date_of_birth"] == "2012-11-02"
    assert response.json()["discovery_source"] == "A friend"
    assert onboard(client, "2012-11-02", "A friend").status_code == 200
    assert onboard(client, "2000-01-01").status_code == 409
    assert users.docs["user_123"]["onboarding"]["date_of_birth"] == "2012-11-02"
    assert client.get("/me/export").json()["onboarding"]["discovery_source"] == "A friend"


def test_leap_day_age():
    assert not eligibility.eligible_birth_date(date(2012, 2, 29), date(2026, 2, 28))
    assert eligibility.eligible_birth_date(date(2012, 2, 29), date(2026, 3, 1))


def test_onboarding_required_for_service_but_not_privacy(client, monkeypatch):
    assert client.get("/me").json()["onboarding_complete"] is False
    for path, body in [("/me/credits/consume", {}), ("/mobile/subscription/sync", {}), ("/create-checkout-session", {"tier": "plus", "interval": "month"}), ("/telemetry/action", {"action": "page_view", "session_id": "test"})]:
        assert client.post(path, json=body).status_code == 403
    assert client.get("/me/credits").status_code == 403
    assert client.get("/me/export").status_code == 200
    monkeypatch.setattr(user, "delete_customer", lambda _: None)
    monkeypatch.setattr(user, "delete_supabase_user", lambda _: None)
    assert client.delete("/me").status_code == 200


@pytest.fixture
def credit_db(monkeypatch, clock):
    db = mongomock.MongoClient().starter
    monkeypatch.setattr(credits, "config", db.config)
    monkeypatch.setattr(credits, "users", db.users)
    monkeypatch.setattr(user, "users", db.users)
    monkeypatch.setattr(user, "user_from_authorization_header", lambda _: AuthUser(id="credits-user", email="test@example.com"))
    db.users.insert_one({"_id": "credits-user", "tier": "free", "interval": None, "onboarding": {"date_of_birth": "2000-01-01", "discovery_source": "Search", "completed_at": "2026-11-02"}})
    return db


@pytest.mark.parametrize("tier,limit", [("free", 5), ("plus", 10), ("pro", 40)])
def test_daily_allowance_and_exhaustion(credit_db, tier, limit):
    credit_db.users.update_one({"_id": "credits-user"}, {"$set": {"tier": tier}})
    for i in range(limit):
        result = credits.consume_credit("token")
        assert result.used == i + 1 and result.remaining == limit - i - 1
    with pytest.raises(HTTPException) as error:
        credits.consume_credit("token")
    assert error.value.status_code == 429
    config = credit_db.config.find_one({"_id": "daily_limits"})
    assert {k: config[k] for k in ("free", "plus", "pro")} == {"free": 5, "plus": 10, "pro": 40}


def test_dynamic_database_limits_upgrade_and_next_day(credit_db, clock):
    assert credits.consume_credit("token").used == 1
    credit_db.config.update_one({"_id": "daily_limits"}, {"$set": {"free": 2}})
    assert credits.consume_credit("token").remaining == 0
    credit_db.users.update_one({"_id": "credits-user"}, {"$set": {"tier": "plus"}})
    assert credits.get_credits("token").remaining == 8  # Upgrade doesn't reset usage.
    credit_db.users.update_one({"_id": "credits-user"}, {"$set": {"tier": "free"}})
    assert credits.get_credits("token").remaining == 0
    clock[0] = date(2026, 11, 3)
    before = credits.get_credits("token")
    assert before.used == 0 and before.remaining == 2
    assert before.resets_at.isoformat() == "2026-11-04T00:00:00+00:00"
    assert credits.consume_credit("token").used == 1
    assert credit_db.config.find_one({"_id": "daily_limits"})["free"] == 2
    # A delayed pre-midnight request must never roll a newer counter backwards.
    clock[0] = date(2026, 11, 2)
    with pytest.raises(HTTPException): credits.consume_credit("token")
    assert credit_db.users.find_one({"_id": "credits-user"})["daily_credits"]["day"] == "2026-11-03"


def test_zero_invalid_configuration_and_mobile_tier(credit_db):
    credits.configured_limits()
    credit_db.config.update_one({"_id": "daily_limits"}, {"$set": {"free": 0}})
    with pytest.raises(HTTPException) as error: credits.consume_credit("token")
    assert error.value.status_code == 429
    credit_db.config.update_one({"_id": "daily_limits"}, {"$set": {"free": True}})
    with pytest.raises(HTTPException) as error: credits.get_credits("token")
    assert error.value.status_code == 503
    credit_db.config.update_one({"_id": "daily_limits"}, {"$set": {"free": 5}})
    credit_db.users.update_one({"_id": "credits-user"}, {"$set": {"revenuecat": {"tier": "pro", "interval": "month", "expires_at": "2099-01-01T00:00:00Z"}}})
    assert credits.get_credits("token").limit == 40


def test_concurrent_spending_never_exceeds_limit(credit_db):
    def spend(_):
        try: credits.consume_credit("token"); return 1
        except HTTPException as e:
            assert e.status_code == 429
            return 0
    with ThreadPoolExecutor(max_workers=16) as pool:
        assert sum(pool.map(spend, range(100))) == 5
    assert credits.get_credits("token").used == 5


def test_credit_endpoint_ignores_forged_tier_and_amount(client, credit_db):
    result = client.post('/me/credits/consume', json={'user_id': 'someone-else', 'tier': 'pro', 'limit': 999, 'amount': -100})
    assert result.status_code == 200
    assert result.json()['limit'] == 5 and result.json()['used'] == 1
    assert credit_db.users.find_one({'_id': 'someone-else'}) is None
