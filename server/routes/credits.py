from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import ValidationError
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from database import config, users
from eligibility import utc_today
from routes.user import onboarded_user
from revenuecat import effective_subscription
from schemas import CreditBalance, DailyLimits

router = APIRouter()
DEFAULT_LIMITS = {"free": 5, "plus": 10, "pro": 40}


def configured_limits() -> DailyLimits:
    # Seed once; never overwrite an operator's database settings.
    try:
        config.update_one({"_id": "daily_limits"}, {"$setOnInsert": DEFAULT_LIMITS}, upsert=True)
    except DuplicateKeyError:
        pass  # Another request created the singleton first.
    try:
        return DailyLimits.model_validate(config.find_one({"_id": "daily_limits"}) or {})
    except ValidationError as error:
        raise HTTPException(503, "The daily_limits configuration is invalid. Contact support.") from error


def balance(doc: dict, tier: str, limit: int, day: str, used: int | None = None) -> CreditBalance:
    usage = doc.get("daily_credits", {})
    if used is None:
        used = usage.get("used", 0) if usage.get("day") == day else 0
    reset = datetime.combine(date.fromisoformat(day) + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return CreditBalance(day=day, tier=tier, limit=limit, used=used, remaining=max(0, limit - used), resets_at=reset)


@router.get("/me/credits", response_model=CreditBalance)
def get_credits(authorization: str | None = Header(default=None)):
    user = onboarded_user(authorization)
    doc = users.find_one({"_id": user.id}) or {}
    tier, _ = effective_subscription(doc)
    limit = getattr(configured_limits(), tier)
    return balance(doc, tier, limit, utc_today().isoformat())


@router.post("/me/credits/consume", response_model=CreditBalance)
def consume_credit(authorization: str | None = Header(default=None)):
    user = onboarded_user(authorization)
    doc = users.find_one({"_id": user.id}) or {}
    tier, _ = effective_subscription(doc)
    limit = getattr(configured_limits(), tier)
    day = utc_today().isoformat()
    used = {"$cond": [
        {"$eq": [{"$ifNull": ["$daily_credits.day", ""]}, day]},
        {"$ifNull": ["$daily_credits.used", 0]},
        0,
    ]}
    # The limit predicate and increment/reset are one MongoDB document operation.
    # Concurrent tabs/devices cannot both spend the same final credit.
    updated = users.find_one_and_update(
        {"_id": user.id, "$or": [
            {"daily_credits.day": {"$exists": False}},
            {"daily_credits.day": {"$lte": day}},
        ], "$expr": {"$lt": [used, limit]}},
        [{"$set": {"daily_credits": {"day": day, "used": {"$add": [used, 1]}}}}],
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise HTTPException(429, "Daily credit limit reached. Credits reset at midnight UTC.")
    return balance(updated, tier, limit, day)
