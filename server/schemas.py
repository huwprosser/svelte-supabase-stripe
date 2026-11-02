import json
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

Tier = Literal["free", "plus", "pro"]
PaidTier = Literal["plus", "pro"]
BillingInterval = Literal["month", "year"]

MAX_TELEMETRY_METADATA_BYTES = 4096
MAX_TELEMETRY_METADATA_DEPTH = 4
MAX_TELEMETRY_METADATA_KEYS = 50
MAX_TELEMETRY_STRING_LENGTH = 500


def validate_telemetry_metadata(value: Any, depth: int = 0) -> int:
    if depth > MAX_TELEMETRY_METADATA_DEPTH:
        raise ValueError("metadata is too deeply nested")

    if isinstance(value, dict):
        if len(value) > MAX_TELEMETRY_METADATA_KEYS:
            raise ValueError("metadata has too many keys")
        count = len(value)
        for key, child in value.items():
            if not isinstance(key, str):
                raise ValueError("metadata keys must be strings")
            if len(key) > MAX_TELEMETRY_STRING_LENGTH:
                raise ValueError("metadata key is too long")
            count += validate_telemetry_metadata(child, depth + 1)
        return count

    if isinstance(value, list):
        if len(value) > MAX_TELEMETRY_METADATA_KEYS:
            raise ValueError("metadata array is too long")
        return len(value) + sum(validate_telemetry_metadata(child, depth + 1) for child in value)

    if isinstance(value, str) and len(value) > MAX_TELEMETRY_STRING_LENGTH:
        raise ValueError("metadata string is too long")

    if value is None or isinstance(value, bool | int | float | str):
        return 1

    raise ValueError("metadata must contain only JSON values")


class AuthUser(BaseModel):
    id: str
    email: str


class UserProfile(BaseModel):
    email: str
    tier: Tier = "free"
    interval: BillingInterval | None = None
    tracking_enabled: bool = False
    onboarding_complete: bool = False
    date_of_birth: date | None = None
    discovery_source: str | None = None


class UserPreferencesUpdate(BaseModel):
    tracking_enabled: bool


class CheckoutRequest(BaseModel):
    tier: PaidTier
    interval: BillingInterval


class PublicPlan(BaseModel):
    tier: Tier
    interval: BillingInterval | None
    name: str
    label: str
    checkout: bool


class TelemetryAction(BaseModel):
    action: str = Field(min_length=1, max_length=120)
    session_id: str = Field(min_length=1, max_length=120)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def metadata_is_bounded(self):
        validate_telemetry_metadata(self.metadata)
        encoded = json.dumps(self.metadata, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_TELEMETRY_METADATA_BYTES:
            raise ValueError("metadata is too large")
        return self


class OnboardingRequest(BaseModel):
    date_of_birth: date
    discovery_source: str = Field(min_length=1, max_length=120)

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def iso_date(cls, value):
        import re
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Use a date in YYYY-MM-DD format")
        return value

    @field_validator("discovery_source", mode="before")
    @classmethod
    def trim_source(cls, value):
        return value.strip() if isinstance(value, str) else value


class DailyLimits(BaseModel):
    free: int = Field(ge=0, strict=True)
    plus: int = Field(ge=0, strict=True)
    pro: int = Field(ge=0, strict=True)


class CreditBalance(BaseModel):
    day: str
    tier: Tier
    limit: int
    used: int
    remaining: int
    resets_at: datetime
