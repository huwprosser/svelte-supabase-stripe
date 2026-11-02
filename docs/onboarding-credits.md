# Onboarding and daily credits

Web and mobile share onboarding state, subscription tier and credit usage through the existing authenticated account. Existing users without onboarding data must complete the same flow as new users. Password recovery, sign-out, data export and account deletion remain available before onboarding.

## Onboarding

`POST /me/onboarding` accepts:

```json
{
  "date_of_birth": "2000-01-01",
  "discovery_source": "A friend"
}
```

Date of birth must be a real ISO calendar date, and the user must be at least 14 on the server's current UTC date. The exact 14th birthday is accepted. A February 29 birthday reaches its new age on March 1 in non-leap years. Future and under-14 birth dates are rejected without storing the submitted birth date or discovery answer. This is a self-declared age gate, not identity/age verification.

The discovery answer is required, trimmed and limited to 120 characters. On success, the existing `users` document receives:

```json
{
  "onboarding": {
    "date_of_birth": "2000-01-01",
    "discovery_source": "A friend",
    "completed_at": "UTC timestamp"
  }
}
```

`GET /me` adds `onboarding_complete`, `date_of_birth` and `discovery_source`. Clients gate authenticated service screens until onboarding is complete. Backend credit consumption, subscription checkout/sync and optional activity telemetry independently require a complete, eligible account; bypassing the UI does not bypass those checks. Public homepage/login and account/privacy operations remain accessible.

Date of birth and the discovery answer are recorded once. Retrying the same successful payload is idempotent. Attempts to replace completed onboarding with different answers return 409; administrative corrections should update the existing account record. Neither answer is included in optional telemetry.

## Database configuration

Collection: **`config`**. Document ID: **`daily_limits`**.

```json
{
  "_id": "daily_limits",
  "free": 5,
  "plus": 10,
  "pro": 40
}
```

The document is seeded with these defaults on first credit access if absent. `$setOnInsert` preserves existing configuration. Values must be non-negative integers; zero disables spending for that tier. Missing, negative, boolean or otherwise invalid limits cause a 503 error rather than granting an unintended allowance. There are no client-side authority values or environment-variable quota overrides.

Edit the existing document to change the limits, for example:

```javascript
db.config.updateOne(
  { _id: "daily_limits" },
  { $set: { free: 5, plus: 10, pro: 40 } },
  { upsert: true }
)
```

Each API request reads the current configuration. No deployment or daily cron job is needed. Clients offer Refresh credits to update a displayed allowance after an operator edit or usage on another device.

## Credit endpoints and counting

- `GET /me/credits` returns `day`, `tier`, `limit`, `used`, `remaining` and `resets_at`.
- `POST /me/credits/consume` consumes exactly one credit and returns the new balance. The request accepts no authoritative user, tier, limit or amount; all are resolved server-side.
- Exhaustion returns 429. The clients show the error and refresh the server balance.

The default Free/Plus/Pro limits are **5 / 10 / 40**. Paid tier selection reuses the existing effective Stripe/RevenueCat subscription logic; it does not create a second subscription-tier system.

The existing `users` document stores one counter:

```json
{
  "daily_credits": { "day": "2026-11-02", "used": 3 }
}
```

A single MongoDB `find_one_and_update` checks the allowance and increments or rolls the day forward atomically. A delayed request for an older day cannot overwrite a newer day's counter. Usage is shared by all sessions, tabs and devices. Reads never consume credits. There is no duplicate daily-usage collection.

Days reset at **00:00 UTC**. A new day appears with zero used credits and is persisted on the next successful spend. Upgrades, downgrades and configuration edits retain that day's usage: upgrading from Free after 5 clicks to Plus gives 5 more, not a fresh 10. A downgrade or reduction below usage gives zero remaining. Credits do not accumulate or carry over.

Both homepages include a **Use 1 credit** placeholder button. Future metered actions should invoke the same server-side limit check/atomic consumption mechanism, not update counters in either client. Consumption is per successful request; callers should not automatically retry an ambiguously completed spend without adding idempotency for that future action.

## Privacy and validation

Onboarding data and the stored daily counter are included in `/me/export`. Both are embedded in the user profile and removed by existing account deletion. The mobile share-sheet and web download use the same export endpoint.

Regression coverage includes age/date boundaries, required discovery text, immutable/idempotent onboarding, pre-onboarding access restrictions and privacy access, all tier limits, zero/invalid config, database edits, tier changes, RevenueCat tier selection, next-day resets, delayed old-day requests, forged client values and concurrent spending. MongoDB query behavior is exercised using a MongoDB emulator (`mongomock`); these tests do not use a live database.
