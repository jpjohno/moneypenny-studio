"""Apple readiness proves only existing, read-only access; no grants or bodies."""
import asyncio
import json
import sqlite3
import threading
from types import SimpleNamespace

import httpx
import pytest

import apple_connections as apple
from native_communications import NativeCommunications


@pytest.fixture
def service(tmp_path):
    for name, table in [('mail.sqlite', 'messages'), ('messages.sqlite', 'message')]:
        with sqlite3.connect(tmp_path/name) as database:
            database.execute('CREATE TABLE '+table+' (text TEXT)')
            database.executemany('INSERT INTO '+table+' VALUES (?)', [('PRIVATE_CONTENT',)]*3)
    native = NativeCommunications(mail_db=tmp_path/'mail.sqlite', messages_db=tmp_path/'messages.sqlite',
                                  registry=tmp_path/'accounts.json')
    rows = [{'id': 'work', 'provider': 'microsoft365', 'address': 'owner@example.test', 'can_open': True},
            {'id': 'apple', 'provider': 'icloud', 'address': 'person@icloud.test', 'can_open': False}]
    cloud = SimpleNamespace(status=lambda: {'accounts': rows}, last_checks={})
    def transport(request):
        assert request.method == 'GET' and request.url.scheme == 'https'
        assert 'authorization' not in request.headers
        if request.url.path.endswith('webmanifest'):
            return httpx.Response(200, json={'display': 'standalone', 'start_url': '/workspace', 'scope': '/',
                                            'icons': [{'src': '/one.png'}, {'src': '/two.png'}]})
        assert request.url.path == '/assets/app-icon-180.png'
        return httpx.Response(200, content=b'PNG', headers={'content-type': 'image/png'})
    return apple.AppleConnections(SimpleNamespace(origins=('https://private.example.test',)), native, cloud,
                                  root=tmp_path, transport=httpx.MockTransport(transport))


def test_snapshot_masks_identity_counts_local_rows_and_never_claims_native_iphone(service, monkeypatch):
    calls = []
    def counts(row):
        calls.append(row['id'])
        return {'state': 'ready', 'inbox_count': 14, 'unread_count': 2, 'checked_at': apple.stamp()}
    monkeypatch.setattr(service, '_provider_counts', counts)
    result = asyncio.run(service.snapshot(paired_browser_count=2))
    assert calls == ['work'], 'Unconnected iCloud must never start sign-in or read'
    assert result['summary'] == {'registered_mailboxes': 2, 'verified_mailboxes': 1, 'mailboxes_needing_sign_in': 1}
    assert result['accounts'][0]['masked_address'] == 'o•••@example.test'
    assert result['accounts'][1]['reason'] == 'sign_in_needed'
    assert result['capabilities']['mac_mail']['count'] == 3
    assert result['capabilities']['mac_messages']['count'] == 3
    assert result['capabilities']['mac_messages']['cloud_sync_verified'] is False
    assert result['capabilities']['iphone_web_app']['state'] == 'ready_to_pair'
    assert result['capabilities']['iphone_web_app']['installed_on_iphone_verified'] is False
    assert result['capabilities']['paired_browsers']['native_iphone_control'] is False
    assert result['capabilities']['paired_browsers']['iphone_identity_verified'] is False
    for capability in ['icloud_photos', 'apple_health', 'homekit', 'imessage_cloud']:
        assert result['capabilities'][capability]['state'] == 'not_connected'
    encoded = json.dumps(result)
    assert 'PRIVATE_CONTENT' not in encoded and 'owner@example.test' not in encoded


def test_permission_denial_stays_action_needed_without_granting_access(service, monkeypatch):
    monkeypatch.setattr(service, '_provider_counts', lambda row: {'state': 'unavailable'})
    def denied(*args):
        raise PermissionError('PRIVATE_PATH')
    monkeypatch.setattr(service.native, 'connection', denied)
    result = asyncio.run(service.snapshot())
    assert result['capabilities']['mac_mail']['state'] == 'action_needed'
    assert result['capabilities']['mac_mail']['count'] is None
    assert 'PRIVATE_PATH' not in json.dumps(result)


def test_count_checks_are_cached_without_sign_in_retry(service, monkeypatch):
    calls = []
    def counts(row):
        calls.append(row['id'])
        return {'state': 'ready', 'inbox_count': 0}
    monkeypatch.setattr(service, '_provider_counts', counts)
    async def run():
        first = await service.snapshot()
        second = await service.snapshot()
        assert first['accounts'][0]['cached'] is False
        assert second['accounts'][0]['cached'] is True
        assert second['capabilities']['iphone_web_app']['cached'] is True
    asyncio.run(run())
    assert calls == ['work']


def test_timeout_is_bounded_and_one_slow_provider_check_is_reused(service, monkeypatch):
    monkeypatch.setattr(apple, 'CHECK_TIMEOUT', .02)
    gate, calls = threading.Event(), []
    def slow():
        calls.append(1)
        gate.wait(2)
        return {'state': 'ready', 'inbox_count': 4}
    async def run():
        try:
            first = await service._bounded('slow', slow)
            second = await service._bounded('slow', slow)
            assert first['state'] == second['state'] == 'unavailable'
            assert first['reason'] == second['reason'] == 'timeout'
            assert calls == [1]
        finally:
            gate.set()
            await service.pending['slow']
        assert (await service._bounded('slow', slow))['state'] == 'ready'
        assert calls == [1]
    asyncio.run(run())


@pytest.mark.parametrize('manifest', [[], {'display': 'browser'}, {'display': 'standalone', 'start_url': '/workspace', 'scope': '/', 'icons': 'ab'}])
def test_invalid_installation_files_never_report_ready(service, manifest):
    def handler(request):
        return httpx.Response(200, json=manifest) if request.url.path.endswith('webmanifest') else httpx.Response(200, headers={'content-type':'image/png'})
    service.transport = httpx.MockTransport(handler)
    result = asyncio.run(service._pwa())
    assert result['state'] == 'action_needed'
    assert result['manifest_ready'] is False


def test_public_redirect_is_not_followed_or_called_verified(service):
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(302, headers={'location': 'https://other.example.test/login'})
    service.transport = httpx.MockTransport(handler)
    result = asyncio.run(service._pwa())
    assert len(calls) == 2
    assert result['state'] == 'unavailable' and result['https_verified'] is False


def test_no_https_origin_does_not_make_any_network_request(service):
    service.settings.origins = ('http://local.example.test',)
    service.transport = httpx.MockTransport(lambda request: pytest.fail('No insecure network probe'))
    assert asyncio.run(service._pwa())['state'] == 'action_needed'


def test_imap_existing_password_is_used_readonly_without_fetch(service, monkeypatch):
    account = {'id': 'apple', 'address': 'someone@icloud.test', 'provider': 'icloud'}
    service.cloud_mail.account = lambda key: account
    service.cloud_mail.saved = lambda value: {'app_password': 'PRIVATE_PASSWORD'}
    calls = []
    class Connection:
        def __init__(self, host, **kwargs):
            assert host == 'imap.mail.me.com' and kwargs['port'] == 993 and kwargs['timeout'] == 4
        def login(self, address, password):
            assert address == account['address'] and password == 'PRIVATE_PASSWORD'
            calls.append('login')
        def select(self, folder, readonly):
            assert folder == 'INBOX' and readonly is True
            calls.append('select')
            return 'OK', [b'42']
        def logout(self):
            calls.append('logout')
    monkeypatch.setattr(apple.imaplib, 'IMAP4_SSL', Connection)
    result = service._provider_counts(account)
    assert result['state'] == 'ready' and result['inbox_count'] == 42
    assert result['message_content_fetched'] is False
    assert calls == ['login', 'select', 'logout']
    assert 'PRIVATE' not in json.dumps(result)


def test_graph_counts_reject_unverified_or_malformed_payloads():
    assert apple.AppleConnections._graph_counts({'totalItemCount': 0, 'unreadItemCount': 0}) == {'inbox_count':0, 'unread_count':0}
    for value in [{}, {'totalItemCount': True, 'unreadItemCount': 0}, {'totalItemCount': -1, 'unreadItemCount': 0}]:
        with pytest.raises(ValueError):
            apple.AppleConnections._graph_counts(value)


def test_authenticated_route_does_not_expose_owner_readiness_without_auth(service, monkeypatch):
    from fastapi import FastAPI, Depends, HTTPException
    from fastapi.testclient import TestClient
    app = FastAPI()
    async def secure(request: apple.Request):
        if request.headers.get('authorization') != 'Bearer isolated-test':
            raise HTTPException(401)
    monkeypatch.setattr(apple, 'AppleConnections', lambda *args, **kwargs: service)
    monkeypatch.setattr(service, '_provider_counts', lambda row: {'state': 'ready', 'inbox_count': 2})
    apple.register_routes(app, [Depends(secure)], service.settings, service.native, service.cloud_mail,
                          paired_count=lambda request: 3)
    with TestClient(app) as client:
        assert client.get('/v1/workspace/apple-connections').status_code == 401
        response = client.get('/v1/workspace/apple-connections', headers={'Authorization':'Bearer isolated-test'})
        assert response.status_code == 200
        assert response.json()['capabilities']['paired_browsers']['count'] == 3
