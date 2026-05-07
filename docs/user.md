# User

A user is an authenticated Supabase account with a matching MongoDB profile document.

## Identity

Supabase owns authentication.

The Supabase user id is stored as the MongoDB document `_id`:

```py
{
  "_id": "supabase-user-id"
}
```

The backend extracts this id from the Supabase access token `sub` claim.

## MongoDB user document

Current user document shape:

```py
{
  "_id": "supabase-user-id",
  "email": "user@example.com",
  "tier": "free",             # free | plus | pro
  "interval": None,            # None | month | year
  "tracking_enabled": False,

  # Added after successful Stripe checkout
  "stripe_customer_id": "cus_...",
  "stripe_subscription_id": "sub_...",
  "subscription_status": "active"
}
```

New users are created lazily when they call an authenticated endpoint such as `/me`.

Default values:

```py
{
  "tier": "free",
  "interval": None,
  "tracking_enabled": False
}
```

## Public profile

The client receives a safe profile shape from `GET /me`:

```py
{
  "email": "user@example.com",
  "tier": "free",
  "interval": None,
  "tracking_enabled": False
}
```

Internal fields such as `_id`, Stripe ids, and subscription status are not returned by `/me`.

## GDPR export

`GET /me/export` returns only user-facing GDPR/profile data:

```py
{
  "email": "user@example.com",
  "tier": "free",
  "interval": None,
  "tracking_enabled": False
}
```

It intentionally excludes internal ids and Stripe identifiers.

## Deletion

`DELETE /me` deletes:

1. the Supabase auth user
2. the MongoDB user document

Telemetry deletion/anonymization policy should be confirmed before production based on legal requirements.
