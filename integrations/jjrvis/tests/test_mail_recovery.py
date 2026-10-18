"""Cached mailbox errors can recover without new scopes or interactive login."""
from types import SimpleNamespace

from workspace_data import MailReader


def test_failed_inbox_releases_cached_client_before_next_refresh(monkeypatch):
    reader = MailReader()
    closed = []
    old_application = object()
    reader.application = old_application
    reader.http = SimpleNamespace(close=lambda: closed.append(True))
    attempts = []
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return {'value': []}
    def headers():
        attempts.append(True)
        if len(attempts) == 1:
            raise ValueError('Synthetic cached sign-in failure')
        assert reader.application is None and reader.http is None
        reader.application = object()
        reader.http = SimpleNamespace(get=lambda *args, **kwargs: Response())
        return {'Authorization': 'Bearer synthetic-test-token-not-a-credential'}
    monkeypatch.setattr(reader, '_headers', headers)
    first = reader.inbox()
    assert first['state'] == 'unavailable' and first['error_category'] == 'ValueError'
    assert reader.application is None and reader.http is None and closed == [True]
    second = reader.inbox()
    assert second['state'] == 'connected' and second['messages'] == []
    assert len(attempts) == 2, 'One bounded attempt per user refresh, without automatic request retries'
