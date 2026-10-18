import secrets

from fastapi.testclient import TestClient

from jarvis_comm_broker import Settings, create_app


def test_cross_site_local_login_cannot_create_owner_cookie():
    app = create_app(Settings(token=secrets.token_urlsafe(32)))
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        for headers in ({'Sec-Fetch-Site': 'cross-site'}, {'CF-Connecting-IP': '192.0.2.1'}, {'Forwarded': 'for=192.0.2.1'}):
            result = client.get('/workspace/local-connect', headers=headers, follow_redirects=False)
            assert result.status_code == 403 and 'jarvis_session' not in result.cookies


def test_pairing_size_is_checked_before_reading_and_security_headers_present():
    app = create_app(Settings(token=secrets.token_urlsafe(32), origins=('https://app.jjrvis.com',)))
    with TestClient(app, base_url='https://app.jjrvis.com') as client:
        assert client.post('/workspace/phone-connect?ticket=invalid', content=b'x'*2049).status_code == 413
        result = client.get('/workspace')
        assert result.headers['x-frame-options'] == 'DENY'
        assert 'camera=()' in result.headers['permissions-policy']
        assert result.headers['strict-transport-security'] == 'max-age=31536000'
        assert "object-src 'none'" in result.headers['content-security-policy']


def test_local_bootstrap_requires_actual_loopback_peer():
    app = create_app(Settings(token=secrets.token_urlsafe(32)))
    with TestClient(app, base_url='http://localhost:8766', client=('192.0.2.1', 50000)) as remote:
        assert remote.get('/workspace/local-connect', follow_redirects=False).status_code == 403
    with TestClient(app, base_url='http://127.0.0.1:8766', client=('127.0.0.1', 50000)) as local:
        assert local.get('/workspace/local-connect', follow_redirects=False).status_code == 303
