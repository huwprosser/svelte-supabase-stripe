# Auth

Authentication uses Supabase email/password on the client and JWT verification in the FastAPI server. Passwords go directly to Supabase; the API and MongoDB never receive or store them.

## Client flow

1. The login form calls `supabase.auth.signInWithPassword({ email, password })`.
2. Create account switches to signup and calls `supabase.auth.signUp({ email, password, options: { emailRedirectTo } })`. Signup requires matching passwords with at least 8 characters; Supabase also enforces its configured password policy.
3. When email confirmation is enabled, signup asks the user to check their email. Confirmation links return to the homepage or `/settings`, depending on where signup started. The Supabase browser client processes the session from the URL. When confirmation is disabled, Supabase returns a session immediately.
4. API calls include the Supabase access token as a bearer token.
5. Logged-in users retain the homepage and manage their account at `/settings`.

The auth UI lives in:

- `client/src/components/AuthForm.svelte`
- `client/src/components/StarterPage.svelte`
- `client/src/routes/reset-password/+page.svelte`
- `client/src/supabase.ts`
- `client/src/api.ts`

## Password recovery and existing accounts

Forgot password sends a recovery email using `supabase.auth.resetPasswordForEmail()` with a redirect to `/reset-password`. After Supabase establishes the recovery session, that page presents a new-password form and calls `supabase.auth.updateUser({ password })`. An expired or invalid link lets the user request a fresh recovery email.

Existing OTP-only users can use Forgot password to set their first password on the same Supabase user, preserving their MongoDB profile and subscription. The normal signup/login flow no longer sends or accepts OTP codes.

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

In Supabase:

- Enable the Email auth provider and email/password signup. Keep email confirmation enabled if required by your application.
- Set Site URL to your frontend origin.
- Add the frontend homepage, `/settings`, and `/reset-password` URLs to the allowed Redirect URLs for each development and production origin (for example `http://localhost:5173/reset-password`).
- Use confirmation and password recovery email templates containing `{{ .ConfirmationURL }}` links. If templates were customized to show OTP codes, restore the link-based templates.
- Configure the password policy to match or exceed the UI's 8-character signup/reset minimum. Login does not impose that minimum, so existing shorter passwords can still authenticate if Supabase accepts them.

Live email delivery, confirmation, login, and recovery require a configured Supabase project.
