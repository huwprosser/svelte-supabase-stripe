import json
from urllib.error import HTTPError, URLError
from urllib.request import Request as UrlRequest
from urllib.request import urlopen

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import Response

from auth import user_from_authorization_header
from config import SUPABASE_SECRET_KEY, SUPABASE_URL
from database import stripe_events, telemetry_actions, users
from schemas import AuthUser, UserPreferencesUpdate, UserProfile

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


def profile_for(user: AuthUser) -> UserProfile:
    doc = users.find_one({"_id": user.id}) or {}
    return UserProfile(
        email=user.email,
        tier=doc.get("tier", "free"),
        interval=doc.get("interval"),
        tracking_enabled=doc.get("tracking_enabled", False),
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


@router.get("/me/export")
def export_me(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    doc = users.find_one({"_id": user.id}) or {}
    export = {
        "email": doc.get("email", user.email),
        "tier": doc.get("tier", "free"),
        "interval": doc.get("interval"),
        "tracking_enabled": doc.get("tracking_enabled", False),
    }
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
    delete_supabase_user(user.id)
    delete_user_related_data(user.id)
    users.delete_one({"_id": user.id})
    return {"ok": True}
