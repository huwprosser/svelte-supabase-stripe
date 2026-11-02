import hmac
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request

from config import REVENUECAT_WEBHOOK_AUTHORIZATION, REVENUECAT_ALLOW_SANDBOX
from database import users
from revenuecat import active_entitlement, request_customer
from routes.user import current_user, profile_for

router = APIRouter()


def sync_customer(user_id: str):
    # Never recreate deleted accounts from late store notifications.
    if users.find_one({"_id": user_id}) is None:
        return
    entitlement = active_entitlement(request_customer(user_id))
    users.update_one({"_id": user_id}, {"$set": {"revenuecat": entitlement}})


@router.post("/mobile/subscription/sync")
def sync_subscription(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    # No user id or entitlement data is accepted from the client.
    sync_customer(user.id)
    return profile_for(user)


@router.post("/revenuecat-webhook")
async def revenuecat_webhook(request: Request, authorization: str | None = Header(default=None)):
    if not REVENUECAT_WEBHOOK_AUTHORIZATION:
        raise HTTPException(503, "RevenueCat webhooks are not configured")
    if not hmac.compare_digest(authorization or "", REVENUECAT_WEBHOOK_AUTHORIZATION):
        raise HTTPException(401, "Invalid webhook authorization")
    try:
        payload = await request.json()
        event = payload.get("event", {})
        if not isinstance(event, dict) or not event.get("id") or not event.get("type"):
            raise ValueError()
        if event.get("environment") == "SANDBOX" and not REVENUECAT_ALLOW_SANDBOX:
            return {"ok": True, "ignored": True}
        candidates = [event.get("app_user_id"), event.get("original_app_user_id")]
        for field in ("aliases", "transferred_from", "transferred_to"):
            values = event.get(field, [])
            if not isinstance(values, list):
                raise ValueError()
            candidates.extend(values)
        user_ids = set()
        for candidate in candidates:
            if not isinstance(candidate, str) or candidate.startswith("$RCAnonymousID:"):
                continue
            try:
                user_ids.add(str(UUID(candidate)))
            except ValueError:
                continue
        if len(user_ids) > 100:
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(400, "Invalid RevenueCat event")
    # Fetch current state rather than trusting stale/out-of-order event payloads.
    # Repeated delivery is idempotent; errors remain retriable (no premature dedup).
    for user_id in sorted(user_ids):
        sync_customer(user_id)
    return {"ok": True}
