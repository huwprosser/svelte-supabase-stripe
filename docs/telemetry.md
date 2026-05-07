# Telemetry

Telemetry records product actions for users who explicitly enable activity tracking.

## Client flow

The client can send an action with metadata:

```txt
POST /telemetry/action
```

Example body:

```json
{
  "action": "checkout_started",
  "session_id": "browser-session-id",
  "metadata": {
    "tier": "pro",
    "interval": "month"
  }
}
```

The browser automatically includes device/browser headers such as `User-Agent`. The backend stores a small allowlist of those headers with each action.

## User preference

The user's MongoDB document stores:

```py
{
  "tracking_enabled": True
}
```

Default is `False`.

The client settings section updates this through:

```txt
PATCH /me/preferences
```

If tracking is disabled, `/telemetry/action` returns success but does not store anything:

```json
{ "ok": true, "tracked": false }
```

## Sessions

Telemetry is session-based. The client stores a session id in `sessionStorage`.

A session survives page refreshes but ends when either:

- the browser tab/window closes, or
- the user is inactive for 30 minutes

After 30 minutes of inactivity, the next tracked action creates a new session id.

## Stored action shape

Actions are stored in `telemetry_actions`:

```py
{
  "user_id": "supabase-user-id",
  "action": "page_view",
  "session_id": "browser-session-id",
  "metadata": {"path": "/"},
  "device": {"user-agent": "..."},
  "timestamp": datetime
}
```

## Indexes

`server/scripts/init_db.py` creates indexes for searching by:

- `action`
- `user_id`
- `session_id`
- `timestamp`
- combined `user_id + action + timestamp`
- combined `user_id + session_id + timestamp`
