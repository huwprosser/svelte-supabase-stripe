# Client

The client is a SvelteKit app in `client/`.

It is built as a static SPA and served either by Vite in development or FastAPI in Docker/production.

## Key files

- `client/src/routes/+page.svelte` - homepage, with welcome copy after login
- `client/src/routes/settings/+page.svelte` - account, privacy preferences, plans, and checkout
- `client/src/components/StarterPage.svelte` - shared page UI and auth lifecycle
- `client/src/routes/+layout.svelte` - app update prompt
- `client/src/routes/+layout.ts` - disables SSR and enables prerendering
- `client/src/api.ts` - typed API helper
- `client/src/supabase.ts` - Supabase browser client
- `client/src/CookieConsent.svelte` - cookie consent banner
- `client/svelte.config.js` - static adapter and version polling

## Runtime behavior

On load, the page:

1. Fetches plans from `GET /plans` on the Settings page.
2. Reads the current Supabase session.
3. If logged in on `/settings`, fetches `/me`.
4. Subscribes to Supabase auth changes.
5. Loads Google Analytics only if cookie consent is accepted.
6. Allows the user to enable/disable product activity tracking in Settings.
7. Allows the user to download profile data or delete their account from Privacy & GDPR on `/settings`.

The homepage keeps its title and layout after login, replacing the signup form with welcome copy and a Settings navigation link. Account details and controls appear only on `/settings`. Opening `/settings` while logged out shows the OTP login form; signing in reveals settings.

## API calls

`client/src/api.ts` adds the Supabase access token to requests:

```txt
Authorization: Bearer <supabase-access-token>
```

The API base URL comes from:

```bash
VITE_API_URL
```

If missing, it defaults to:

```txt
http://localhost:8000
```

## Telemetry

When enabled by the user, the client sends lightweight product actions to:

```txt
POST /telemetry/action
```

Current tracked actions include page views, auth changes, and checkout starts.

## Cache/update handling

SvelteKit version polling is enabled in `client/svelte.config.js`.

`+layout.svelte` checks for updates and asks the user to reload when a new version is available.

This replaces the need for a React-style cache buster package.

## Development

```bash
cd client
npm install
npm run dev
```

Open:

```txt
http://localhost:5173
```

## Build

```bash
cd client
npm run build
```

Output goes to:

```txt
client/dist
```
