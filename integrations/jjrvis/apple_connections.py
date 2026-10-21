"""Read-only Apple setup checks, without Apple ID passwords or permission grants.

Provider checks use existing sign-ins and request inbox counts only. Local Mac
counts prove database access, not current sync or delivery. A paired web browser
is deliberately not presented as native access to an iPhone or Apple services.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import imaplib
from pathlib import Path
import ssl
import time
from urllib.parse import urlsplit

import httpx
from fastapi import Request

from cloud_mail_accounts import ACCOUNT, IMAP_HOSTS, SCOPES

HERE = Path(__file__).resolve().parent
CHECK_TIMEOUT = 6.0
CACHE_SECONDS = 120
MAX_PROVIDER_CHECKS = 8


def stamp():
    return datetime.now(timezone.utc).isoformat()


def masked_address(value):
    local, separator, domain = str(value or '').partition('@')
    return (local[:1] + '•••@' + domain) if separator else 'Saved account'


class AppleConnections:
    def __init__(self, settings, native, cloud_mail, *, root=HERE, transport=None):
        self.settings, self.native, self.cloud_mail = settings, native, cloud_mail
        self.root, self.transport = Path(root), transport
        self.cache, self.pending = {}, {}

    async def _bounded(self, key, function):
        """Reuse slow in-flight checks instead of queuing repeated sign-in work."""
        now = time.monotonic()
        cached = self.cache.get(key)
        if cached and now - cached[0] < CACHE_SECONDS:
            return {**cached[1], 'cached': True}
        task = self.pending.get(key)
        if task is None:
            async def run():
                try:
                    return await asyncio.to_thread(function)
                except Exception:
                    return {'state': 'unavailable', 'reason': 'connection_or_sign_in', 'checked_at': stamp()}
            task = asyncio.create_task(run())
            self.pending[key] = task
        try:
            value = await asyncio.wait_for(asyncio.shield(task), CHECK_TIMEOUT)
        except asyncio.TimeoutError:
            return {'state': 'unavailable', 'reason': 'timeout', 'checked_at': stamp(), 'cached': False}
        except Exception:
            value = {'state': 'unavailable', 'reason': 'connection_or_sign_in', 'checked_at': stamp()}
        if task.done():
            self.pending.pop(key, None)
        self.cache[key] = (time.monotonic(), value)
        return {**value, 'cached': False}

    def _provider_counts(self, row):
        account = self.cloud_mail.account(row['id'])
        saved = self.cloud_mail.saved(account)
        provider = account['provider']
        if provider in IMAP_HOSTS:
            if not saved or not saved.get('app_password'):
                raise ValueError('Existing sign-in required')
            connection = imaplib.IMAP4_SSL(IMAP_HOSTS[provider], port=993,
                                          ssl_context=ssl.create_default_context(), timeout=4)
            try:
                connection.login(account['address'], saved['app_password'])
                state, counts = connection.select('INBOX', readonly=True)
                if state != 'OK' or not counts or not counts[0].isdigit():
                    raise ValueError('Inbox count unavailable')
                result = {'inbox_count': int(counts[0]), 'unread_count': None}
            finally:
                try:
                    connection.logout()
                except Exception:
                    pass
        elif account['address'].lower() == ACCOUNT and not saved:
            legacy = self.cloud_mail.legacy
            with legacy.lock:
                headers = legacy._headers()
                response = legacy.http.get('https://graph.microsoft.com/v1.0/me/mailFolders/inbox',
                                           headers=headers, params={'$select': 'totalItemCount,unreadItemCount'},
                                           allow_redirects=False, timeout=(3, 4))
                response.raise_for_status()
                data = response.json()
                result = self._graph_counts(data)
        else:
            if not saved:
                raise ValueError('Existing sign-in required')
            app, _cache, session = self.cloud_mail._ms_app(account, existing=True)
            try:
                identities = app.get_accounts(username=account['address'])
                token = app.acquire_token_silent_with_error(SCOPES, account=identities[0]) if identities else None
                if not token or not token.get('access_token'):
                    raise ValueError('Existing sign-in expired')
                response = session.get('https://graph.microsoft.com/v1.0/me/mailFolders/inbox',
                                       headers={'Authorization': 'Bearer ' + token['access_token']},
                                       params={'$select': 'totalItemCount,unreadItemCount'}, allow_redirects=False)
                response.raise_for_status()
                result = self._graph_counts(response.json())
            finally:
                session.close()
        self.cloud_mail.last_checks[account['id']] = {
            'state': 'connected', 'checked_at': stamp(),
            'detail': 'Inbox access verified with a count-only provider read. No messages were fetched.'}
        return {'state': 'ready', 'reason': None, 'checked_at': stamp(),
                'mode': 'provider_read_only', 'message_content_fetched': False, **result}

    @staticmethod
    def _graph_counts(data):
        count, unread = data.get('totalItemCount'), data.get('unreadItemCount')
        if type(count) is not int or count < 0 or type(unread) is not int or unread < 0:
            raise ValueError('Provider count unavailable')
        return {'inbox_count': count, 'unread_count': unread}

    def _local_count(self, kind):
        path, table = ((self.native.mail_db, 'messages') if kind == 'mac_mail'
                       else (self.native.messages_db, 'message'))
        try:
            with self.native.connection(path) as database:
                count = database.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]
            return {'state': 'ready', 'count': count, 'mode': 'mac_synced_read_only',
                    'checked_at': stamp(), 'cloud_sync_verified': False,
                    'detail': 'Local access works. This does not verify current sync or server delivery.'}
        except Exception:
            return {'state': 'action_needed', 'count': None, 'mode': 'mac_synced_read_only',
                    'checked_at': stamp(), 'reason': 'mac_source_or_permission',
                    'cloud_sync_verified': False,
                    'detail': 'Open the original Mac app and check its macOS access. JJRVIS has not changed permissions.'}

    async def _pwa(self):
        origins = tuple(getattr(self.settings, 'origins', ()) or ())
        origin = origins[0].rstrip('/') if origins else ''
        parsed = urlsplit(origin)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
            return {'state': 'action_needed', 'https_verified': False, 'manifest_ready': False,
                    'installed_on_iphone_verified': False, 'action': 'pair_device',
                    'detail': 'Configure a private HTTPS address before pairing an iPhone.'}
        now = time.monotonic()
        cached = self.cache.get('pwa')
        if cached and now-cached[0] < CACHE_SECONDS:
            return {**cached[1], 'cached': True}
        result = {'state': 'unavailable', 'https_verified': False, 'manifest_ready': False,
                  'installed_on_iphone_verified': False, 'action': 'pair_device',
                  'detail': 'The private HTTPS app could not be verified. Check the Mac connection and try again.'}
        try:
            async with httpx.AsyncClient(transport=self.transport, timeout=3, trust_env=False,
                                         follow_redirects=False) as client:
                async def check():
                    manifest, icon = await asyncio.gather(client.get(origin+'/manifest.webmanifest'),
                                                          client.get(origin+'/assets/app-icon-180.png'))
                    manifest.raise_for_status(); icon.raise_for_status()
                    data = manifest.json()
                    valid = (isinstance(data, dict) and data.get('display') == 'standalone'
                             and data.get('start_url') == '/workspace'
                             and data.get('scope') == '/' and isinstance(data.get('icons'), list)
                             and len(data['icons']) >= 2
                             and icon.headers.get('content-type', '').split(';')[0] == 'image/png')
                    return valid
                valid = await asyncio.wait_for(check(), timeout=4)
            result.update(state='ready_to_pair' if valid else 'action_needed', https_verified=True,
                          manifest_ready=valid,
                          detail='Open the private pairing link in Safari, then Share → Add to Home Screen → Open as Web App.'
                                 if valid else 'HTTPS works, but the app installation files need attention.')
        except (httpx.HTTPError, ValueError, TypeError, asyncio.TimeoutError):
            pass
        result['checked_at'] = stamp()
        self.cache['pwa'] = (time.monotonic(), result)
        return {**result, 'cached': False}

    async def snapshot(self, *, paired_browser_count=0):
        try:
            registered = self.cloud_mail.status().get('accounts', [])[:50]
            accounts_state = 'available'
        except Exception:
            registered, accounts_state = [], 'unavailable'

        checked_accounts = set([row['id'] for row in registered if row.get('can_open')][:MAX_PROVIDER_CHECKS])

        async def account_status(row):
            base = {'id': row['id'], 'provider': row['provider'],
                    'masked_address': masked_address(row.get('address')),
                    'action': 'accounts', 'can_send': False, 'inbox_count': None,
                    'unread_count': None, 'message_content_fetched': False}
            if not row.get('can_open'):
                return {**base, 'state': 'action_needed', 'reason': 'sign_in_needed',
                        'checked_at': None, 'detail': 'Connect this mailbox with its existing provider sign-in option.'}
            if row['id'] not in checked_accounts:
                return {**base, 'state': 'check_needed', 'reason': 'check_limit', 'checked_at': None,
                        'detail': 'Open this inbox to verify its saved sign-in. This overview checks at most eight provider accounts.'}
            result = await self._bounded('mail:'+row['id'], lambda: self._provider_counts(row))
            return {**base, **result, 'detail': 'Count-only inbox access verified.' if result['state'] == 'ready'
                    else 'The saved sign-in could not be verified. Open Accounts & passwords to reconnect or retry.'}

        accounts, mail, messages, iphone = await asyncio.gather(
            asyncio.gather(*(account_status(row) for row in registered)),
            self._bounded('mac_mail', lambda: self._local_count('mac_mail')),
            self._bounded('mac_messages', lambda: self._local_count('mac_messages')),
            self._pwa())
        return {'checked_at': stamp(), 'mode': 'single_owner', 'scope': 'read_only',
                'accounts_state': accounts_state, 'accounts': accounts,
                'summary': {'registered_mailboxes': len(accounts),
                            'verified_mailboxes': sum(row['state'] == 'ready' for row in accounts),
                            'mailboxes_needing_sign_in': sum(row.get('reason') == 'sign_in_needed' for row in accounts)},
                'capabilities': {
                    'mac_mail': mail, 'mac_messages': messages, 'iphone_web_app': iphone,
                    'paired_browsers': {'state': 'ready' if paired_browser_count else 'action_needed',
                                        'count': max(0, int(paired_browser_count)),
                                        'iphone_identity_verified': False, 'native_iphone_control': False},
                    'apple_account_sign_in': {'state': 'not_implemented', 'detail': 'Provider mail sign-in does not sign JJRVIS into an Apple Account.'},
                    'icloud_photos': {'state': 'not_connected'},
                    'apple_health': {'state': 'not_connected'},
                    'homekit': {'state': 'not_connected'},
                    'imessage_cloud': {'state': 'not_connected', 'detail': 'Messages are read only from the existing Mac sync.'},
                },
                'permission_statement': 'No Apple Account password is requested. This check grants no macOS or iPhone permissions, sends no messages, and activates no device.'}


def register_routes(app, secure, settings, native, cloud_mail, *, paired_count=None, root=HERE):
    service = AppleConnections(settings, native, cloud_mail, root=root)
    @app.get('/v1/workspace/apple-connections', dependencies=secure)
    async def connections(request: Request):
        count = paired_count(request) if paired_count else 0
        return await service.snapshot(paired_browser_count=count)
    return service
