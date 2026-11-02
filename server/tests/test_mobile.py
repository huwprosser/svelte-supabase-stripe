from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi import HTTPException
import revenuecat
from routes import mobile, user
from test_main import client, users, stripe_events, telemetry_actions


def customer(tier='pro', expires=None, sandbox=False):
    expires = expires or (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    return {'subscriber': {'entitlements': {tier: {'product_identifier': f'{tier}_month', 'expires_date': expires}}, 'subscriptions': {f'{tier}_month': {'is_sandbox': sandbox}}}}


def test_entitlements_expire_without_removing_stripe(monkeypatch):
    monkeypatch.setattr(revenuecat, 'REVENUECAT_ALLOW_SANDBOX', False)
    active = revenuecat.active_entitlement(customer())
    assert active['tier'] == 'pro' and active['interval'] == 'month'
    assert revenuecat.effective_subscription({'tier': 'plus', 'interval': 'year', 'revenuecat': active}) == ('pro', 'month')
    active['expires_at'] = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    assert revenuecat.effective_subscription({'tier': 'plus', 'interval': 'year', 'revenuecat': active}) == ('plus', 'year')
    assert revenuecat.active_entitlement(customer(sandbox=True))['tier'] == 'free'
    assert revenuecat.active_entitlement(customer(expires=active['expires_at']))['tier'] == 'free'


def test_sync_uses_authenticated_identity(client, users, monkeypatch):
    monkeypatch.setattr(mobile, 'users', users)
    queried = []
    monkeypatch.setattr(mobile, 'request_customer', lambda uid: queried.append(uid) or customer())
    response = client.post('/mobile/subscription/sync', json={'user_id': 'other', 'tier': 'pro'})
    assert response.status_code == 200 and response.json()['tier'] == 'pro'
    assert queried == ['user_123']
    assert client.get('/me').json()['tier'] == 'pro'
    assert 'mobile_subscription' in client.get('/me/export').json()


def test_webhook_auth_transfers_duplicates_retries_and_deleted_users(client, users, monkeypatch):
    monkeypatch.setattr(mobile, 'users', users)
    monkeypatch.setattr(mobile, 'REVENUECAT_WEBHOOK_AUTHORIZATION', 'Bearer test-secret')
    first, second, deleted = str(uuid4()), str(uuid4()), str(uuid4())
    users.docs[first] = {'_id': first, 'tier': 'plus', 'interval': 'year'}
    users.docs[second] = {'_id': second, 'tier': 'free'}
    calls = []
    def fetch(uid):
        calls.append(uid)
        return customer() if uid == second else {}
    monkeypatch.setattr(mobile, 'request_customer', fetch)
    payload = {'event': {'id': 'event1', 'type': 'TRANSFER', 'transferred_from': [first], 'transferred_to': [second, deleted]}}
    assert client.post('/revenuecat-webhook', json=payload).status_code == 401
    headers = {'Authorization': 'Bearer test-secret'}
    assert client.post('/revenuecat-webhook', json=payload, headers=headers).status_code == 200
    assert set(calls) == {first, second}
    assert users.docs[first]['tier'] == 'plus'
    assert users.docs[first]['revenuecat']['tier'] == 'free'
    assert users.docs[second]['revenuecat']['tier'] == 'pro'
    assert deleted not in users.docs
    assert client.post('/revenuecat-webhook', json=payload, headers=headers).status_code == 200
    def unavailable(_): raise HTTPException(502, 'Try again')
    monkeypatch.setattr(mobile, 'request_customer', unavailable)
    assert client.post('/revenuecat-webhook', json=payload, headers=headers).status_code == 502
    assert client.post('/revenuecat-webhook', json={}, headers=headers).status_code == 400


def test_deletion_cleans_revenuecat_and_supabase(client, users, monkeypatch):
    users.docs['user_123'] = {'_id': 'user_123', 'tier': 'free', 'revenuecat': {'tier': 'pro'}}
    deleted = []
    monkeypatch.setattr(user, 'delete_customer', lambda uid: deleted.append(('revenuecat', uid)))
    monkeypatch.setattr(user, 'delete_supabase_user', lambda uid: deleted.append(('supabase', uid)))
    assert client.delete('/me').status_code == 200
    assert deleted == [('revenuecat', 'user_123'), ('supabase', 'user_123')]
    assert 'user_123' not in users.docs
