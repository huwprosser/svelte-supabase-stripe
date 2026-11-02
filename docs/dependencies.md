# Dependency update and validation — 2 November 2026

Package manifests and both existing lockfiles were refreshed against the package registries. The new Expo app includes its own committed npm lockfile. Updates target stable versions compatible with the framework's peer requirements; prereleases and unsupported forced overrides are excluded.

## Main changes

| Package / tool | Before | After |
| --- | --- | --- |
| Supabase JS | 2.105.3 | 2.118.0 (web and mobile) |
| SvelteKit | 2.59.1 | 3.1.1 |
| Static adapter | 3.0.10 | 4.0.1 |
| Vite Svelte plugin | 7.1.1 locked | 7.3.1 |
| Svelte | 5.55.5 locked | 5.57.3 |
| Vite | 8.0.10 | 8.3.5 |
| Svelte Check | 4.4.8 | 4.7.8 |
| Node type definitions | 25.6.0 | 26.6.6 |
| Docker Node build image | 22-alpine | 26-alpine (current LTS) |
| FastAPI | 0.136.1 | 0.162.0 |
| Uvicorn | 0.46.0 | 0.54.0 |
| PyMongo | 4.17.0 | 4.19.0 |
| python-dotenv | 1.2.2 | 1.2.4 |
| Stripe Python | 15.1.0 | 16.1.0 |
| PyJWT | 2.12.1 | 2.15.1 |
| pytest | 9.0.3 | 9.2.0 |
| cryptography (transitive) | 48.0.0 | 50.0.2 |
| Starlette (transitive) | 1.0.0 | 1.10.0 |

SvelteKit 3 configuration now lives in `client/vite.config.ts`, and TypeScript extends `$app/tsconfig`. The old cookie override was removed so SvelteKit can use its required cookie v2 API. The Docker frontend install disables npm lifecycle scripts.

TypeScript remains at 6.0.3: SvelteKit 3.1.1 requires TypeScript `^6.0.0`, and Expo SDK 58 recommends the same release. HTTPX 0.28.1, `@tsconfig/svelte` 5.0.8, h11, httpcore, and PyYAML already resolve to their latest compatible releases. Python's supported 3.12 container line is retained; Python interpreter-major migration is not part of the package update.

The new app uses the official SDK 58 tabs template: Expo 58.0.22, Expo Router 58.0.29, React 19.3.0, React Native 0.88.1, and RevenueCat `react-native-purchases` 11.0.0. Expo-managed React/native packages and ESLint use the SDK-compatible versions; forcing newer versions outside that matrix is intentionally avoided. Expo Doctor validates the matrix.

## Advisory snapshot

| Dependency tree | Result |
| --- | --- |
| Original web npm lockfile | 10 affected packages: 6 high, 2 moderate, 2 low |
| Updated web, including test dependencies | 4 low affected packages, all cascading from one underlying `deepmerge` advisory; 0 high/critical |
| Expo mobile npm lockfile | 26 moderate affected packages, cascading from two underlying `glob` / `minimatch` advisories in Expo configuration/build and linting chains; 0 high/critical |
| Updated Python environment (`pip-audit`) | No known vulnerabilities reported |

Remaining upstream advisories:

- [deepmerge prototype poisoning](https://github.com/advisories/GHSA-gcqx-w48m-w2h4). Its latest published 4.3.1 is affected, through the Svelte Vite plugin.
- [glob cancellation/timeout bypass](https://github.com/advisories/GHSA-3g3m-2fjr-6pw4), through Expo tooling.
- [minimatch denial of service](https://github.com/advisories/GHSA-g3hv-75wg-m249), through Expo tooling and ESLint plugins.

The Expo tree still requires older major versions of these tools. No automatic force downgrade or cross-major override was applied. Audit findings remain visible, and `npm audit` returns a nonzero exit code for these advisories. Audit databases cannot prove the absence of compromised packages or unknown vulnerabilities.

## Validation

- Web: `npm test` passes 8 simulated auth scenarios (login, error/retry, signup validation, confirmation-required signup, immediate-session signup, reset email, password update, expired-session state, and duplicate-submit handling are covered across those checks).
- Web: `npm run check` has zero errors/warnings, and `npm run build` succeeds with all three routes.
- Backend: `uv run pytest -q` passes 10 tests, covering existing account/payment/privacy behavior plus mobile entitlement expiration, shared profiles, webhook authentication/transfers/retries, ignored deleted users and RevenueCat deletion.
- Python: `uv lock --check` and `pip-audit` pass.
- Mobile: `npm test` verifies RevenueCat identification, serialized account switches, logout and retry after a failed identity change using a mock SDK.
- Mobile: TypeScript and ESLint pass, `expo install --check` reports compatible dependencies, and Expo Doctor passes 20/20 checks.
- Both iOS and Android JavaScript/Hermes bundles export successfully. These are bundle checks, not signed native builds.
- `git diff --check` passes.

No live project secrets, production users, or real purchases were used. Supabase email delivery/confirmation/recovery, native deep-link handoff, the OS share sheet, and RevenueCat App Store/Play sandbox purchases still require configured project credentials and device testing. A full Docker image was not built in this environment. Starlette currently emits a deprecation warning recommending `httpx2` for its test client; the existing latest HTTPX tests pass.
