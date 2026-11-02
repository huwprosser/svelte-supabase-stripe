"""Server-verified mobile entitlements, independent of Stripe's web subscriptions."""
import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

from config import REVENUECAT_SECRET_KEY, REVENUECAT_ALLOW_SANDBOX, REVENUECAT_ENTITLEMENTS

# Match these store product identifiers to your App Store / Play products.
PRODUCT_INTERVALS = {
    "plus_month": "month", "plus_year": "year",
    "pro_month": "month", "pro_year": "year",
}


def request_customer(user_id: str, method: str = "GET") -> dict:
    if not REVENUECAT_SECRET_KEY:
        raise HTTPException(503, "Mobile billing is not configured")
    request = Request(
        f"https://api.revenuecat.com/v1/subscribers/{quote(user_id, safe='')}",
        method=method,
        headers={"Authorization": f"Bearer {REVENUECAT_SECRET_KEY}", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except HTTPError as error:
        if error.code == 404:
            return {}
        raise HTTPException(502, "RevenueCat could not verify the subscription") from error
    except (URLError, TimeoutError, ValueError) as error:
        raise HTTPException(502, "RevenueCat is temporarily unavailable") from error


def active_entitlement(customer: dict) -> dict:
    subscriber = customer.get("subscriber", {})
    now = datetime.now(timezone.utc)
    entitlements = subscriber.get("entitlements", {})
    subscriptions = subscriber.get("subscriptions", {})
    # Highest tier wins; cancellation does not revoke access before expiration.
    for tier in ("pro", "plus"):
        entitlement = entitlements.get(REVENUECAT_ENTITLEMENTS[tier])
        if not entitlement:
            continue
        expires = entitlement.get("expires_date")
        try:
            expires_at = datetime.fromisoformat(expires.replace("Z", "+00:00")) if expires else None
        except (ValueError, AttributeError):
            continue
        if expires_at and (expires_at.tzinfo is None or expires_at <= now):
            continue
        product_id = entitlement.get("product_identifier")
        subscription = subscriptions.get(product_id, {})
        if subscription.get("is_sandbox", False) and not REVENUECAT_ALLOW_SANDBOX:
            continue
        # Expiring entitlements must have a corresponding verified subscription.
        if expires_at and not subscription:
            continue
        return {"tier": tier, "interval": PRODUCT_INTERVALS.get(product_id), "expires_at": expires}
    return {"tier": "free", "interval": None, "expires_at": None}


def effective_subscription(doc: dict) -> tuple[str, str | None]:
    tier, interval = doc.get("tier", "free"), doc.get("interval")
    mobile = doc.get("revenuecat", {})
    mobile_tier = mobile.get("tier", "free")
    expires = mobile.get("expires_at")
    if expires:
        try:
            expiration = datetime.fromisoformat(expires.replace("Z", "+00:00"))
            if expiration.tzinfo is None or expiration <= datetime.now(timezone.utc):
                mobile_tier = "free"
        except (ValueError, AttributeError):
            mobile_tier = "free"
    rank = {"free": 0, "plus": 1, "pro": 2}
    if rank.get(mobile_tier, 0) > rank.get(tier, 0):
        return mobile_tier, mobile.get("interval")
    return tier, interval


def delete_customer(user_id: str):
    if REVENUECAT_SECRET_KEY:
        request_customer(user_id, "DELETE")
