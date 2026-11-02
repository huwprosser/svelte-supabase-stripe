import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response

from auth import user_from_authorization_header
from config import SUPABASE_SECRET_KEY, SUPABASE_URL
from database import stripe_events, telemetry_actions, users
from eligibility import eligible_birth_date, onboarding_complete, require_onboarding
from revenuecat import delete_customer, effective_subscription
from schemas import AuthUser, UserPreferencesUpdate, UserProfile, OnboardingRequest

router = APIRouter()


def current_user(authorization: str | None) -> AuthUser:
    user = user_from_authorization_header(authorization)
    users.update_one(
        {"_id": user.id},
        {
            "$setOnInsert": {
                "email": user.email,
                "tier": "free",
                "interval": None,
                "tracking_enabled": False,
            }
        },
        upsert=True,
    )
    return user


def onboarded_user(authorization: str | None) -> AuthUser:
    user = current_user(authorization)
    require_onboarding(users.find_one({"_id": user.id}) or {})
    return user


def profile_for(user: AuthUser) -> UserProfile:
    doc = users.find_one({"_id": user.id}) or {}
    tier, interval = effective_subscription(doc)
    return UserProfile(
        email=user.email,
        tier=tier,
        interval=interval,
        tracking_enabled=doc.get("tracking_enabled", False),
        onboarding_complete=onboarding_complete(doc),
        date_of_birth=doc.get("onboarding", {}).get("date_of_birth"),
        discovery_source=doc.get("onboarding", {}).get("discovery_source"),
    )


def delete_user_related_data(user_id: str):
    telemetry_actions.delete_many({"user_id": user_id})
    stripe_events.update_many(
        {
            "$or": [
                {"payload.data.object.client_reference_id": user_id},
                {"payload.data.object.metadata.user_id": user_id},
            ]
        },
        {
            "$set": {
                "user_deleted": True,
                "payload.data.object.client_reference_id": "[deleted]",
                "payload.data.object.customer_email": None,
                "payload.data.object.customer_details.email": None,
                "payload.data.object.metadata.user_id": "[deleted]",
                "payload.data.object.subscription_data.metadata.user_id": "[deleted]",
            }
        },
    )


def delete_supabase_user(user_id: str):
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise HTTPException(500, "SUPABASE_URL and SUPABASE_SECRET_KEY are required")

    request = UrlRequest(
        f"{SUPABASE_URL.rstrip('/')}/auth/v1/admin/users/{user_id}",
        method="DELETE",
        headers={
            "apikey": SUPABASE_SECRET_KEY,
            "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
        },
    )
    try:
        urlopen(request, timeout=10).read()
    except HTTPError as e:
        raise HTTPException(
            e.code, e.read().decode() or "Failed to delete Supabase user"
        )
    except URLError as e:
        raise HTTPException(502, f"Failed to reach Supabase: {e.reason}")


@router.get("/me", response_model=UserProfile)
def me(authorization: str | None = Header(default=None)):
    return profile_for(current_user(authorization))


@router.post("/me/onboarding", response_model=UserProfile)
def complete_onboarding(body: OnboardingRequest, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if not eligible_birth_date(body.date_of_birth):
        raise HTTPException(403, "You must be at least 14 to use this service.")
    result = users.update_one(
        {"_id": user.id, "onboarding.completed_at": {"$exists": False}},
        {"$set": {"onboarding": {
            "date_of_birth": body.date_of_birth.isoformat(),
            "discovery_source": body.discovery_source,
            "completed_at": datetime.now(timezone.utc),
        }}},
    )
    if not result.modified_count:
        existing = (users.find_one({"_id": user.id}) or {}).get("onboarding", {})
        if existing.get("date_of_birth") == body.date_of_birth.isoformat() and existing.get("discovery_source") == body.discovery_source:
            return profile_for(user)  # Safe retry after a lost successful response.
        raise HTTPException(409, "Onboarding is already complete. Contact support to correct your date of birth.")
    return profile_for(user)


@router.get("/me/export")
def export_me(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    doc = users.find_one({"_id": user.id}) or {}
    tier, interval = effective_subscription(doc)
    export = {
        "email": doc.get("email", user.email),
        "tier": tier,
        "interval": interval,
        "tracking_enabled": doc.get("tracking_enabled", False),
    }
    if doc.get("onboarding"):
        export["onboarding"] = doc["onboarding"]
    if doc.get("daily_credits"):
        export["daily_credits"] = doc["daily_credits"]
    if doc.get("revenuecat"):
        export["mobile_subscription"] = doc["revenuecat"]
    payload = json.dumps(export, default=str, indent=2)
    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="profile-data.json"',
            "Cache-Control": "no-store",
        },
    )


@router.patch("/me/preferences", response_model=UserProfile)
def update_preferences(
    body: UserPreferencesUpdate, authorization: str | None = Header(default=None)
):
    user = current_user(authorization)
    users.update_one(
        {"_id": user.id},
        {"$set": {"tracking_enabled": body.tracking_enabled}},
    )
    return profile_for(user)


@router.delete("/me")
def delete_me(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    delete_customer(user.id)
    delete_supabase_user(user.id)
    delete_user_related_data(user.id)
    users.delete_one({"_id": user.id})
    return {"ok": True}
