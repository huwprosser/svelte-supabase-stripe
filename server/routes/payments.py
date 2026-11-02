import json
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Header, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from config import (
    FRONTEND_URL,
    STRIPE_LIVE_MODE,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    price_id_for,
    public_plans,
    require_configured_stripe_webhook_secret,
)
from database import stripe_events, users
from routes.user import onboarded_user
from schemas import CheckoutRequest, PublicPlan

stripe.api_key = STRIPE_SECRET_KEY
router = APIRouter()


@router.get("/plans", response_model=list[PublicPlan])
def plans():
    return public_plans()


@router.post("/create-checkout-session")
def create_checkout_session(
    body: CheckoutRequest, authorization: str | None = Header(default=None)
):
    user = onboarded_user(authorization)
    price_id = price_id_for(body.tier, body.interval)
    if not price_id or price_id.startswith("price_replace_"):
        raise HTTPException(500, "Stripe price ID not configured in server/config.py")

    checkout = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=user.email,
        client_reference_id=user.id,
        metadata={
            "user_id": user.id,
            "tier": body.tier,
            "interval": body.interval,
            "price_id": price_id,
        },
        subscription_data={
            "metadata": {
                "user_id": user.id,
                "tier": body.tier,
                "interval": body.interval,
                "price_id": price_id,
            }
        },
        success_url=f"{FRONTEND_URL}/?checkout=success",
        cancel_url=f"{FRONTEND_URL}/?checkout=cancelled",
    )
    return {"url": checkout.url}


def stripe_get(obj, key: str, default=None):
    if hasattr(obj, "get"):
        try:
            return obj.get(key, default)
        except TypeError:
            pass
    return getattr(obj, key, default)


def subscription_price_ids(subscription: dict) -> set[str]:
    items = stripe_get(stripe_get(subscription, "items", {}), "data", []) or []
    price_ids = set()
    for item in items:
        price = stripe_get(item, "price", {})
        price_id = stripe_get(price, "id")
        if price_id:
            price_ids.add(price_id)
    return price_ids


def validate_completed_checkout(session: dict) -> tuple[str, str, str]:
    metadata = stripe_get(session, "metadata", {}) or {}
    tier = stripe_get(metadata, "tier")
    interval = stripe_get(metadata, "interval")
    user_id = stripe_get(metadata, "user_id")
    client_reference_id = stripe_get(session, "client_reference_id")
    expected_price_id = price_id_for(tier, interval) if tier and interval else None

    if user_id and user_id != client_reference_id:
        raise ValueError("Checkout user metadata does not match client reference")

    if not expected_price_id or expected_price_id.startswith("price_replace_"):
        raise ValueError("Checkout metadata does not map to a configured plan")
    if stripe_get(metadata, "price_id") != expected_price_id:
        raise ValueError("Checkout price metadata does not match configured plan")
    if stripe_get(session, "mode") not in {None, "subscription"}:
        raise ValueError("Checkout session is not a subscription")

    subscription_id = stripe_get(session, "subscription")
    if not subscription_id:
        raise ValueError("Checkout session is missing a subscription")

    subscription = stripe.Subscription.retrieve(
        subscription_id, expand=["items.data.price"]
    )
    status = stripe_get(subscription, "status")
    if status not in {"active", "trialing"}:
        raise ValueError("Stripe subscription is not active")
    if expected_price_id not in subscription_price_ids(subscription):
        raise ValueError("Stripe subscription price does not match checkout plan")

    return tier, interval, status


def process_stripe_event(event: dict):
    event_type = stripe_get(event, "type")
    event_object = stripe_get(stripe_get(event, "data", {}), "object", {})
    if event_type == "checkout.session.completed":
        session = event_object
        tier, interval, subscription_status = validate_completed_checkout(session)
        users.update_one(
            {"_id": stripe_get(session, "client_reference_id")},
            {
                "$set": {
                    "stripe_customer_id": stripe_get(session, "customer"),
                    "stripe_subscription_id": stripe_get(session, "subscription"),
                    "tier": tier,
                    "interval": interval,
                    "subscription_status": subscription_status,
                }
            },
            upsert=True,
        )

    if event_type in [
        "customer.subscription.deleted",
        "customer.subscription.paused",
    ]:
        sub = event_object
        user_id = stripe_get(stripe_get(sub, "metadata", {}), "user_id")
        if user_id:
            users.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "tier": "free",
                        "interval": None,
                        "subscription_status": stripe_get(sub, "status"),
                    }
                },
            )


@router.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    try:
        require_configured_stripe_webhook_secret(STRIPE_WEBHOOK_SECRET)
    except RuntimeError as e:
        raise HTTPException(500, str(e))

    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(400, str(e))

    if bool(stripe_get(event, "livemode")) != STRIPE_LIVE_MODE:
        raise HTTPException(400, "Unexpected Stripe livemode")

    event_id = stripe_get(event, "id")
    if not event_id:
        raise HTTPException(400, "Stripe event is missing an id")
    try:
        stripe_events.insert_one(
            {
                "_id": event_id,
                "type": stripe_get(event, "type"),
                "created": stripe_get(event, "created"),
                "livemode": stripe_get(event, "livemode"),
                "payload": json.loads(payload),
                "processed": False,
                "received_at": datetime.now(timezone.utc),
                "processed_at": None,
                "error": None,
            }
        )
    except DuplicateKeyError:
        return {"ok": True, "duplicate": True}

    try:
        process_stripe_event(event)
    except Exception as e:
        stripe_events.update_one(
            {"_id": event_id},
            {"$set": {"processed": False, "error": str(e)}},
        )
        raise

    stripe_events.update_one(
        {"_id": event_id},
        {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc)}},
    )
    return {"ok": True}
