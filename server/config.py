import os

from schemas import PublicPlan

ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
IS_PRODUCTION = ENVIRONMENT in {"prod", "production"}

MAX_REQUEST_BODY_BYTES = int(os.getenv("MAX_REQUEST_BODY_BYTES", "1048576"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "starter")
SUPABASE_URL = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_JWT_AUDIENCE = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_LIVE_MODE = os.getenv(
    "STRIPE_LIVE_MODE", "true" if STRIPE_SECRET_KEY.startswith("sk_live_") else "false"
).lower() in {"1", "true", "yes", "on"}

_PLACEHOLDER_STRIPE_WEBHOOK_SECRETS = {
    "",
    "whsec_xxx",
    "whsec_your_webhook_secret",
    "whsec_replace_me",
}


def is_configured_stripe_webhook_secret(secret: str | None = None) -> bool:
    checked_secret = STRIPE_WEBHOOK_SECRET if secret is None else secret
    return (
        checked_secret.startswith("whsec_")
        and len(checked_secret) >= 20
        and checked_secret not in _PLACEHOLDER_STRIPE_WEBHOOK_SECRETS
    )


def require_configured_stripe_webhook_secret(secret: str | None = None) -> None:
    if not is_configured_stripe_webhook_secret(secret):
        raise RuntimeError("STRIPE_WEBHOOK_SECRET must be a real Stripe whsec_ signing secret")

# Put your Stripe recurring Price IDs here after creating them in Stripe.
# These are intentionally code config, not environment variables, so the
# available plans are obvious and easy to read in one place.
PLANS = [
    {
        "tier": "free",
        "interval": None,
        "name": "Free",
        "label": "Free",
        "price_id": None,
        "checkout": False,
    },
    {
        "tier": "plus",
        "interval": "month",
        "name": "Plus",
        "label": "Plus monthly",
        "price_id": "price_replace_plus_month",
        "checkout": True,
    },
    {
        "tier": "plus",
        "interval": "year",
        "name": "Plus",
        "label": "Plus annual",
        "price_id": "price_replace_plus_year",
        "checkout": True,
    },
    {
        "tier": "pro",
        "interval": "month",
        "name": "Pro",
        "label": "Pro monthly",
        "price_id": "price_replace_pro_month",
        "checkout": True,
    },
    {
        "tier": "pro",
        "interval": "year",
        "name": "Pro",
        "label": "Pro annual",
        "price_id": "price_replace_pro_year",
        "checkout": True,
    },
]


def public_plans() -> list[PublicPlan]:
    """Plans safe to send to the frontend. Never expose Stripe price IDs."""
    return [
        PublicPlan(**{k: v for k, v in plan.items() if k != "price_id"})
        for plan in PLANS
    ]


def price_id_for(tier: str, interval: str) -> str | None:
    for plan in PLANS:
        if plan["tier"] == tier and plan["interval"] == interval and plan["checkout"]:
            return plan["price_id"]
    return None
