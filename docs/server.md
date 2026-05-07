# Server

The server is a FastAPI app in `server/`.

It handles:

- Supabase JWT verification
- user profile storage
- Stripe Checkout session creation
- Stripe webhook processing
- static SvelteKit frontend serving in Docker/production

## Key files

- `server/main.py` - app setup, CORS, routers, static frontend serving
- `server/routes/user.py` - user/profile route logic
- `server/routes/payments.py` - plans, checkout, webhooks
- `server/routes/telemetry.py` - user activity tracking endpoint
- `server/database.py` - MongoDB client and collections
- `server/auth.py` - Supabase JWT verification
- `server/config.py` - environment config and plan definitions
- `server/schemas.py` - shared Pydantic models and type aliases
- `server/scripts/init_db.py` - MongoDB collection/index setup
- `server/tests/test_main.py` - concise backend API tests

## Route layout

```txt
GET  /plans
GET  /me
GET  /me/export
DELETE /me
POST /create-checkout-session
POST /stripe-webhook
POST /telemetry/action
PATCH /me/preferences
```

## Database

MongoDB collections:

- `users`
- `stripe_events`
- `telemetry_actions`

Initialize them with:

```bash
cd server
uv run python scripts/init_db.py
```

## Local development

```bash
cd server
uv sync
uv run uvicorn main:app --reload
```

Server runs on:

```txt
http://localhost:8000
```

## Tests

```bash
cd server
uv run pytest
```

The tests mock Stripe, Supabase auth, and Mongo collections. They focus on high-value behavior rather than implementation details.

## Docker/production serving

The Dockerfile builds the SvelteKit client and copies `client/dist` into:

```txt
server/static
```

If `server/static` exists, FastAPI serves it as the frontend. Unknown paths fall back to `index.html` so the SPA can load correctly.

## Environment

Root `.env` values used by the server:

```bash
FRONTEND_URL=...
MONGODB_URI=...
MONGODB_DB=...
SUPABASE_URL=...
SUPABASE_SECRET_KEY=...
STRIPE_SECRET_KEY=...
STRIPE_WEBHOOK_SECRET=...
```
