# Auth

Authentication is handled by Supabase email OTP on the client and verified by the FastAPI server.

## Client flow

1. User enters their email.
2. `supabase.auth.signInWithOtp()` sends a one-time code.
3. User enters the code.
4. `supabase.auth.verifyOtp()` creates a Supabase session.
5. API calls include the Supabase access token as a bearer token.

The auth UI lives in:

- `client/src/routes/+page.svelte`
- `client/src/supabase.ts`
- `client/src/api.ts`

## Server verification

Protected endpoints read the `Authorization` header:

```txt
Authorization: Bearer <supabase-access-token>
```

`server/auth.py` verifies modern Supabase access tokens using the project's JWKS endpoint.

The server extracts:

- `sub` as the user id
- `email` as the user's email

It returns an `AuthUser` model from `server/schemas.py`.

## User profile creation

When an authenticated user calls `/me` or starts checkout, `current_user()` ensures a MongoDB user document exists:

```py
{
  "_id": "supabase-user-id",
  "email": "user@example.com",
  "tier": "free",
  "interval": None
}
```

This means every new authenticated user starts on the free tier.

## Important config

Root `.env` needs:

```bash
VITE_SUPABASE_URL=...
VITE_SUPABASE_PUBLISHABLE_KEY=...
```

For account deletion, set the Supabase secret/service-role key. This is used server-side only to remove the Supabase auth user:

```bash
SUPABASE_SECRET_KEY=...
```

The backend uses `VITE_SUPABASE_URL` or `SUPABASE_URL` to fetch the project's JWKS.

In Supabase, set the site URL to your frontend URL.
