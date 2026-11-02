from datetime import date, datetime, timezone

from fastapi import HTTPException


def utc_today() -> date:
    return datetime.now(timezone.utc).date()


def eligible_birth_date(value: date, today: date | None = None) -> bool:
    today = today or utc_today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    return value <= today and age >= 14


def onboarding_complete(doc: dict) -> bool:
    onboarding = doc.get("onboarding", {})
    try:
        born = date.fromisoformat(onboarding["date_of_birth"])
    except (KeyError, TypeError, ValueError):
        return False
    return bool(onboarding.get("completed_at") and onboarding.get("discovery_source") and eligible_birth_date(born))


def require_onboarding(doc: dict):
    if not onboarding_complete(doc):
        raise HTTPException(403, "Complete onboarding first. You must be at least 14 to use the service.")
