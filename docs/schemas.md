# Schemas

Shared backend models live in `server/schemas.py`.

They keep route inputs, route outputs, and internal auth data consistent.

## Type aliases

```py
Tier = Literal["free", "plus", "pro"]
PaidTier = Literal["plus", "pro"]
BillingInterval = Literal["month", "year"]
```

These avoid repeating string unions across the server.

## AuthUser

Represents the authenticated Supabase user after JWT verification.

```py
class AuthUser(BaseModel):
    id: str
    email: str
```

Used by:

- `server/auth.py`
- `server/routes/user.py`
- `server/routes/payments.py`

## UserProfile

Public profile returned by `GET /me`.

```py
class UserProfile(BaseModel):
    email: str
    tier: Tier = "free"
    interval: BillingInterval | None = None
    tracking_enabled: bool = False
```

This is the client-safe representation of a user subscription.

## UserPreferencesUpdate

Input for `PATCH /me/preferences`.

```py
class UserPreferencesUpdate(BaseModel):
    tracking_enabled: bool
```

## CheckoutRequest

Input for `POST /create-checkout-session`.

```py
class CheckoutRequest(BaseModel):
    tier: PaidTier
    interval: BillingInterval
```

Only paid tiers are accepted. The free tier does not go through Stripe Checkout.

## PublicPlan

Public plan shape returned by `GET /plans`.

```py
class PublicPlan(BaseModel):
    tier: Tier
    interval: BillingInterval | None
    name: str
    label: str
    checkout: bool
```

Stripe `price_id` is deliberately excluded from this model so price ids are never exposed to the browser.

## TelemetryAction

Input for `POST /telemetry/action`.

```py
class TelemetryAction(BaseModel):
    action: str
    session_id: str
    metadata: dict[str, Any]
```

## Why this file exists

Central schemas make it easier to:

- understand the domain
- validate API inputs and outputs
- keep route files smaller
- reduce accidental string/type drift
