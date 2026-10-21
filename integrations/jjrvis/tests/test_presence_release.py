"""Release-level headers and authorities for the owner-only mobile renderer."""
import re
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient

import apple_connections
import cloud_mail_accounts
import jarvis_comm_broker as broker
import persistent_sessions
import workspace_data
from test_presence_proxy import Body

TOKEN='synthetic-presence-release-owner-token-not-a-credential'
AUTH={'Authorization':'Bearer '+TOKEN}
BASE='https://owner-fixture.invalid'


@pytest.fixture
def release(tmp_path,monkeypatch):
    monkeypatch.setattr(broker,'HERE',tmp_path)
    monkeypatch.setattr(cloud_mail_accounts,'HERE',tmp_path)
    monkeypatch.setattr(workspace_data,'read_json',lambda path:{})
    (tmp_path/'workspace.html').write_text('<!doctype html><html><head><meta charset="utf-8"></head><body>Owner workspace fixture</body></html>')
    original=persistent_sessions.SessionStore
    monkeypatch.setattr(persistent_sessions,'SessionStore',lambda path:original(tmp_path/'owner-sessions.sqlite3'))
    apple_calls=[]
    async def snapshot(self,**kwargs):
        apple_calls.append(kwargs)
        return {'scope':'synthetic-readiness','connected':False,'native_iphone_control':False}
    monkeypatch.setattr(apple_connections.AppleConnections,'snapshot',snapshot)
    app=broker.create_app(broker.Settings(token=TOKEN,origins=(BASE,)),task_path=tmp_path/'tasks.sqlite3')
    requests=[]
    def upstream(request):
        requests.append(request)
        assert request.url.host=='127.0.0.1' and request.url.port==8090
        assert 'authorization' not in request.headers and 'cookie' not in request.headers
        if request.url.path=='/':
            html=b'<!doctype html><html><head><script type="importmap">{"imports":{"three":"/vendor/three/build/three.module.js"}}</script></head><body><script>window.fixture=true;</script><script src="/static/studio.js"></script></body></html>'
            return httpx.Response(200,stream=Body(html),headers={'Content-Type':'text/html; charset=utf-8'})
        return httpx.Response(200,stream=Body(b'fixture-module'),headers={'Content-Type':'text/javascript'})
    app.state.presence_proxy.transport=httpx.MockTransport(upstream)
    return SimpleNamespace(app=app,requests=requests,apple_calls=apple_calls)


def owner_cookie(client):
    ticket=client.post('/v1/workspace/session-ticket',headers=AUTH,json={}).json()['ticket']
    assert client.get('/workspace/connect',params={'ticket':ticket},follow_redirects=False).status_code==303
    assert 'jarvis_session' in client.cookies


def test_global_boundary_retains_child_nonce_while_parent_is_unframeable(release):
    with TestClient(release.app,base_url=BASE) as client:
        owner_cookie(client)
        parent=client.get('/workspace')
        child=client.get('/presence/?embed=jarvis',headers={'Origin':BASE})
    assert parent.status_code==200 and child.status_code==200
    assert parent.headers['x-frame-options']=='DENY'
    assert "frame-src 'self'" in parent.headers['content-security-policy']
    assert "frame-ancestors 'none'" in parent.headers['content-security-policy']
    assert "connect-src 'self';" in parent.headers['content-security-policy']
    assert "connect-src 'self' blob:" not in parent.headers['content-security-policy']
    assert "'unsafe-inline'" not in parent.headers['content-security-policy']
    assert child.headers['x-frame-options']=='SAMEORIGIN'
    nonce=re.search(r'<script[^>]*nonce="([^"]+)"',child.text)[1]
    assert child.text.count('nonce=')==3
    csp=child.headers['content-security-policy']
    assert f"'nonce-{nonce}'" in csp and "'wasm-unsafe-eval'" in csp
    assert "frame-ancestors 'self'" in csp and "base-uri 'none'" in csp
    assert "connect-src 'self' blob:;" in csp, 'GLTF texture ImageBitmapLoader fetches internal blob URLs'
    assert "img-src 'self' data: blob:;" in csp
    assert "script-src 'self' 'nonce-" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert child.headers['cache-control']=='no-store'
    assert child.headers['strict-transport-security']=='max-age=31536000'
    assert child.headers['x-content-type-options']=='nosniff'
    assert len(release.requests)==1


def test_render_child_cannot_use_camera_mic_location_or_studio_writes(release):
    with TestClient(release.app,base_url=BASE) as client:
        owner_cookie(client)
        parent=client.get('/workspace')
        child=client.get('/presence/?embed=jarvis')
        assert 'camera=(self)' in parent.headers['permissions-policy'], 'Parent camera still requires a browser permission grant'
        for capability in ('camera','microphone','geolocation'):
            assert capability+'=()' in child.headers['permissions-policy'], 'Renderer is an inert presentation child, not a capture UI'
        count=len(release.requests)
        for path in ('api/speech','api/transcribe','api/listening/warm','api/motion/plan','api/reminders'):
            result=client.post('/presence/'+path,headers={'Origin':BASE},json={})
            assert result.status_code==405
        assert len(release.requests)==count


def test_valid_preview_cannot_render_or_reach_apple_owner_status(release):
    with TestClient(release.app,base_url=BASE) as owner:
        invitation=owner.post('/v1/workspace/preview-invites',headers={**AUTH,'Origin':BASE},json={'label':'Synthetic isolated preview','days':1}).json()['url'].split('#invite=')[1]
    with TestClient(release.app,base_url=BASE) as preview:
        assert preview.post('/v1/preview/connect',headers={'Origin':BASE},json={'invite':invitation}).status_code==200
        assert 'jjrvis_preview' in preview.cookies and 'jarvis_session' not in preview.cookies
        for path in ('/presence/','/presence/static/studio.js','/presence/api/character/default','/v1/workspace/apple-connections'):
            assert preview.get(path).status_code==401
    assert not release.requests and not release.apple_calls
    with TestClient(release.app,base_url=BASE) as owner:
        owner_cookie(owner)
        status=owner.get('/v1/workspace/apple-connections')
        assert status.status_code==200 and status.json()['scope']=='synthetic-readiness'
    assert len(release.apple_calls)==1


def test_renderer_origin_and_method_rejection_survive_global_boundary(release):
    with TestClient(release.app,base_url=BASE) as client:
        owner_cookie(client)
        for headers in ({'Origin':'https://other.invalid'},{'Sec-Fetch-Site':'cross-site'}):
            assert client.get('/presence/static/studio.js',headers=headers).status_code==403
        assert client.get('/presence/api/personas').status_code==404
        assert client.get('/presence/api/reminders').status_code==404
        assert client.get('/presence/?url=http://other.invalid').status_code==400
        assert client.post('/presence/api/speech',headers={'Origin':BASE},json={}).status_code==405
    assert not release.requests


def test_mac_preview_is_owner_authenticated_and_never_a_public_download(release,tmp_path):
    artifact=tmp_path/'native/apple/.build/JJRVIS-Mac-preview.zip'
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b'synthetic-development-build-fixture')
    with TestClient(release.app,base_url='http://127.0.0.1:8766') as client:
        assert client.get('/v1/workspace/mac-app').status_code==401
        response=client.get('/v1/workspace/mac-app',headers=AUTH)
        assert response.status_code==200
        assert response.content==artifact.read_bytes()
        assert 'no-store' in response.headers['cache-control']
    with TestClient(release.app,base_url=BASE) as client:
        assert client.get('/v1/workspace/mac-app',headers=AUTH).status_code==404
