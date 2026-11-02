# Expo mobile app

Created from the official Expo SDK 58 `tabs@latest` template. Routes are under `src/app/`, with Home, Subscription, and Settings tabs. It shares the web app's Supabase project, MongoDB profile, and FastAPI API. Mobile purchases use RevenueCat, not Stripe Checkout.

## Run

1. `cp .env.example .env` and fill in the public values. Use a LAN IP or deployed HTTPS backend URL, not localhost, on a physical phone.
2. `npm ci --ignore-scripts`
3. `npx expo start` for auth/account development in Expo Go.
4. For real purchases, make a development build with `npx eas-cli@latest build --profile development --platform ios` (or `android`), install it, then `npx expo start --dev-client`. Expo Go and web previews disable purchases/restores.

Change `com.example.supabasestarter` identifiers and the app scheme before publishing. Set your EAS project using your own account. No store signing credentials are included.

## Supabase

Use the same Supabase URL and publishable key as the web app. Enable email/password authentication. Allow `starterapp://auth/callback` in Supabase Redirect URLs. Keep confirmation and recovery templates link-based (`{{ .ConfirmationURL }}`). Development clients use that scheme; Expo Go may need its exact `exp://.../--/auth/callback` redirect allowlisted during testing.

Email confirmation and recovery links work for cold starts and an already-open app. Supabase's implicit session links are processed by the auth provider, tokens persist in chunked SecureStore entries on native, and refresh pauses while the app is inactive. Existing OTP accounts can set a password through Forgot password. The mobile web preview uses browser local storage.

## RevenueCat and stores

1. Connect App Store Connect and Google Play to one RevenueCat project and configure their subscription products.
2. Create `plus` and `pro` entitlements and attach monthly/annual products. Store identifiers default to `plus_month`, `plus_year`, `pro_month`, and `pro_year`; update `server/revenuecat.py:PRODUCT_INTERVALS` if your store identifiers differ. Entitlement names live in `server/config.py`.
3. Create a current offering containing the packages you want to display. The app uses localized store titles and prices from RevenueCat.
4. Put the platform's **public SDK key** in `mobile/.env`. Secret API keys stay on the backend only.
5. Set `REVENUECAT_SECRET_KEY` to a backend RevenueCat secret key with permission to read and delete customers. Set `REVENUECAT_WEBHOOK_AUTHORIZATION` to a random, high-entropy Authorization header value such as `Bearer <random-secret>` and configure the exact same value in the RevenueCat dashboard.
6. Configure the RevenueCat webhook URL as `https://YOUR_API/revenuecat-webhook`, with all purchase, renewal, expiration, cancellation and transfer events enabled. Sandbox is rejected by default; enable `REVENUECAT_ALLOW_SANDBOX=true` only on a test backend, using separate test credentials/data.
7. Use Supabase user UUIDs as App User IDs. The app configures RevenueCat with the signed-in UUID, serializes identity switches, and requires login before purchases/restores. Review RevenueCat's restore/transfer behavior to match your account policy.

After purchase or restore, `POST /mobile/subscription/sync` fetches authoritative entitlement state from RevenueCat using the authenticated Supabase UUID. If purchase succeeds but sync fails, the app offers an explicit retry. Webhooks also fetch current state, handle transferred identities, ignore deleted accounts, and remain safe to retry. Client-supplied tiers and user IDs never grant access.

Stripe's existing web subscription state remains separate. `/me` returns the highest active tier from either provider, and mobile expiration does not remove a Stripe entitlement. Avoid buying a second subscription when the account already has web access. The native app does not open Stripe checkout.

## Privacy and account controls

Settings includes opt-in activity tracking, data export through the OS share sheet, and permanent account deletion after confirmation. Exported files are removed from the app cache after the share sheet closes. Account deletion calls the shared API, removes the RevenueCat customer when configured, deletes the Supabase user, removes the Mongo profile and telemetry, and redacts stored Stripe event user references.

Deleting an account does **not** cancel an App Store/Play subscription. Cancel through the store's subscription manager first; the Subscription tab opens the management URL supplied by RevenueCat. Billing records retained by Apple, Google, Stripe, or RevenueCat follow those providers' retention policies. No Google Analytics or advertising SDK is bundled in this app; essential auth/billing processing is separate from optional product telemetry.

## Checks

- `npm test` (mock RevenueCat identity tests)
- `npm run check`
- `npm run lint`
- `npx expo install --check`
- `npx expo-doctor`
- `npx expo export --platform ios --platform android` (JavaScript bundle checks only)

StoreKit/Play sandbox transactions, native deep links and OS share sheets still need device testing with real project configuration. Native signed binaries require an EAS account or the platform toolchain.

## Onboarding and credits

All authenticated tabs require shared onboarding: date of birth (age 14+) and where the user found the service. Export/deletion and logout remain available during onboarding. Home includes a one-credit button with a server-provided balance shared with the web app. Default daily limits are Free 5, Plus 10 and Pro 40, stored in MongoDB `config/daily_limits`; reset is midnight UTC. See [onboarding and credit configuration](../docs/onboarding-credits.md).
