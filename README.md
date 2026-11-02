# Bare-bones Supabase Auth + MongoDB + Stripe starter

SvelteKit TypeScript web frontend, Expo SDK 58 tabs app, and a shared FastAPI backend.

Recommended deployment path:
- Supabase for Auth (required)
- MongoDB for database (required) [Recommended to deploy to railway for lowest cost, Atlas for production scale]
- Fly.io, Railway or AWS ECS for server deployment. 

Features:
- Supabase email/password signup/login and password recovery with JWKS-based JWT verification
- MongoDB user/profile storage
- Stripe subscription checkout on web; RevenueCat in-app subscriptions on mobile
- Shared email/password auth, account settings, and privacy controls across clients
- Date-of-birth onboarding (14+) and discovery question
- Shared daily credits, configured in MongoDB `config/daily_limits`
- User-controlled activity tracking via `/telemetry/action`
- Tiers: free, plus monthly/annual, pro monthly/annual
- Frontend loads plans from `GET /plans`
- Google Analytics loaded only after cookie consent
- All styling lives inside Svelte files

This project was built to make it easy to start commercial apps - and provide coding agents a solid base for success on the important stuff.

Out of the box you get user management, payments, database setup, telemetry foundations, and a frontend.

## Docs

See `docs/` for concise guides:

- `mobile/README.md` — Expo setup, RevenueCat, deep links, and store testing
- `docs/dependencies.md` — upgrade versions, audit findings, and validation
- `docs/onboarding-credits.md` — age 14+ onboarding and database-configured daily credits
- `docs/auth.md`
- `docs/payments.md`
- `docs/client.md`
- `docs/server.md`
- `docs/user.md`
- `docs/telemetry.md`
- `docs/gdpr.md`
- `docs/schemas.md`

## GDPR notes

Current privacy controls:

1. Users can opt in and out of product activity tracking from account settings.
2. The backend checks `tracking_enabled` before storing telemetry.
3. Telemetry is disabled by default for new users.

Implemented self-service privacy endpoints:

1. `GET /me/export` downloads the user's Mongo profile data.
2. `DELETE /me` deletes the Mongo user and Supabase auth user.
