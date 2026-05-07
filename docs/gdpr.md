# GDPR

This project includes basic privacy controls for user data and product activity tracking.

## Activity tracking consent

Activity tracking is disabled by default.

Each user document stores:

```py
{
  "tracking_enabled": False
}
```

Users can enable or disable tracking from the client settings section.

The backend checks this value before storing telemetry. If tracking is disabled, `/telemetry/action` returns success but stores nothing.

## Data export

Users can download their stored MongoDB profile document from:

```txt
GET /me/export
```

The response is a JSON file attachment named:

```txt
profile-data.json
```

This export contains only user-facing profile/privacy data, not internal database fields like `_id` or Stripe identifiers.

Current exported fields:

- `email`
- `tier`
- `interval`
- `tracking_enabled`

## Account deletion

Users can delete their account through:

```txt
DELETE /me
```

The endpoint:

1. Verifies the user's Supabase access token.
2. Deletes the Supabase auth user using the server-side service role key.
3. Deletes the user's MongoDB document from the `users` collection.

Required server env:

```bash
SUPABASE_URL=...
SUPABASE_SECRET_KEY=...
```

`SUPABASE_SECRET_KEY` must never be exposed to the browser.

## Telemetry storage

When tracking is enabled, actions are stored in `telemetry_actions` with:

- user id
- action type
- metadata
- selected browser/device headers
- timestamp

## Stripe event storage

Stripe webhook events are stored in `stripe_events` for auditability, idempotency, and debugging.

## Limitations

This is a starter implementation. Before production, confirm your legal requirements for:

- retention windows
- deleting or anonymizing telemetry during account deletion
- deleting Stripe-side customer data if required
- privacy policy wording
- cookie consent requirements for your region
