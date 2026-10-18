"""The paired-owner renderer is a read-only fixed-host asset boundary."""
import asyncio
import json
from urllib.parse import urlsplit, parse_qs

import httpx
import pytest
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.testclient import TestClient

import presence_proxy

TOKEN='synthetic-presence-owner-token-not-a-credential'
AUTH={'Authorization':'Bearer '+TOKEN}
BASE='http://127.0.0.1:8766'


class Body(httpx.AsyncByteStream):
    def __init__(self, *chunks):
        self.chunks=chunks
        self.closed=False
        self.read=False
    async def __aiter__(self):
        self.read=True
        for chunk in self.chunks:
            yield chunk
    async def aclose(self):
        self.closed=True


def make_app(handler):
    app=FastAPI()
    async def owner(request:Request):
        if request.headers.get('authorization')!='Bearer '+TOKEN:
            raise HTTPException(401,'Owner required')
    service=presence_proxy.register_routes(app,[Depends(owner)],transport=httpx.MockTransport(handler))
    # Mirrors the root boundary's intentionally scoped frame/header integration.
    @app.middleware('http')
    async def frame_headers(request, call_next):
        response=await call_next(request)
        response.headers['Content-Security-Policy']=getattr(request.state,'presence_csp',"default-src 'none'")
        response.headers['X-Frame-Options']='SAMEORIGIN' if getattr(request.state,'presence_frame',False) else 'DENY'
        return response
    return app,service


def response(body, kind='application/javascript', status=200, headers=None):
    return httpx.Response(status,stream=Body(body),headers={'Content-Type':kind,**(headers or {})})


def test_html_is_nonce_scoped_and_asset_paths_are_same_origin():
    calls=[]
    document=b'''<!doctype html><html><head><link href="/static/studio.css" rel="stylesheet"><script type="importmap">{"imports":{"three":"/vendor/three/build/three.module.js"}}</script></head><body><script>const status="/api/status";</script><script type="module" src="/static/studio.js"></script></body></html>'''
    def handler(request):
        calls.append(request)
        assert str(request.url)=='http://127.0.0.1:8090/?embed=jarvis'
        assert 'authorization' not in request.headers and 'cookie' not in request.headers
        assert request.headers['accept-encoding']=='identity'
        return response(document,'text/html; charset=utf-8',headers={'Set-Cookie':'forbidden=1','Access-Control-Allow-Origin':'*'})
    app,_=make_app(handler)
    with TestClient(app,base_url=BASE) as client:
        result=client.get('/presence/?embed=jarvis',headers={**AUTH,'Cookie':'jarvis_session=owner-private'})
    assert result.status_code==200
    assert '<meta name="studio-base" content="/presence/">' in result.text
    assert '/presence/static/studio.css' in result.text and '/presence/vendor/three/' in result.text
    assert '"/presence/api/status"' in result.text
    assert result.text.count('nonce=')==3
    nonce=result.text.split('nonce="')[1].split('"')[0]
    assert f"'nonce-{nonce}'" in result.headers['content-security-policy']
    assert "'wasm-unsafe-eval'" in result.headers['content-security-policy']
    assert 'script-src' in result.headers['content-security-policy']
    assert result.headers['x-frame-options']=='SAMEORIGIN'
    assert 'set-cookie' not in result.headers and 'access-control-allow-origin' not in result.headers
    assert len(calls)==1


def test_every_asset_needs_owner_auth_and_preview_cookie_is_not_owner():
    calls=[]
    def handler(request):
        calls.append(request)
        return response(b'asset')
    app,_=make_app(handler)
    with TestClient(app,base_url=BASE) as client:
        for path in ('/presence/','/presence/static/studio.js','/presence/api/character/default'):
            assert client.get(path).status_code==401
            assert client.get(path,headers={'Cookie':'jjrvis_preview=not-owner'}).status_code==401
    assert calls==[]


@pytest.mark.parametrize('path',[
    'chat','api/chat/stream','api/speech','api/speech/stop','api/transcribe','api/personas','api/reminders',
    'api/motion/plan','api/listening/warm','static/config.json','config.json','vendor/three/package.json',
    'http://example.com/asset.glb','static/%2e%2e/app.py','static/%252e%252e/app.py',
    'static/vendor/headaudio/%2fetc/passwd','static/vendor/headaudio/secret.txt',
])
def test_only_inert_render_route_allowlist_can_reach_upstream(path):
    calls=[]
    app,_=make_app(lambda request:calls.append(request) or response(b'blocked'))
    with TestClient(app,base_url=BASE) as client:
        result=client.get('/presence/'+path,headers=AUTH)
    assert result.status_code==404 and not calls


@pytest.mark.parametrize('headers',[{'Origin':'https://other.invalid'},{'Origin':'null'},{'Sec-Fetch-Site':'cross-site'},{'Sec-Fetch-Site':'same-site'}])
def test_cross_origin_fetches_are_denied_even_with_owner_authorization(headers):
    calls=[]
    app,_=make_app(lambda request:calls.append(request) or response(b'blocked'))
    with TestClient(app,base_url=BASE) as client:
        assert client.get('/presence/static/studio.js',headers={**AUTH,**headers}).status_code==403
    assert calls==[]


def test_mutating_methods_and_target_query_are_unavailable():
    calls=[]
    app,_=make_app(lambda request:calls.append(request) or response(b'blocked'))
    with TestClient(app,base_url=BASE) as client:
        for method in ('post','put','patch','delete'):
            assert getattr(client,method)('/presence/api/character/default',headers=AUTH).status_code==405
        assert client.get('/presence/?target=http://example.com',headers=AUTH).status_code==400
        assert client.get('/presence/api/status?quick=0',headers=AUTH).status_code==400
        assert client.get('/presence/static/studio.js?path=../../secret',headers=AUTH).status_code==400
    assert calls==[]


def test_assets_stream_ranges_and_head_without_forwarding_credentials():
    calls=[];bodies=[]
    def handler(request):
        calls.append(request)
        assert 'authorization' not in request.headers and 'cookie' not in request.headers
        body=Body(b'glb-');bodies.append(body)
        return httpx.Response(206,stream=body,headers={'Content-Type':'model/gltf-binary','Content-Length':'4','Content-Range':'bytes 0-3/12','Accept-Ranges':'bytes','ETag':'"fixture"'})
    app,_=make_app(handler)
    with TestClient(app,base_url=BASE) as client:
        result=client.get('/presence/api/character/default',headers={**AUTH,'Range':'bytes=0-3'})
        assert result.status_code==206 and result.content==b'glb-'
        assert result.headers['content-range']=='bytes 0-3/12'
        assert result.headers['etag']=='"fixture"' and bodies[0].closed
        head=client.head('/presence/api/character/default',headers={**AUTH,'Range':'bytes=0-3'})
        assert head.status_code==206 and head.content==b'' and bodies[1].closed and not bodies[1].read
        for value in ('bytes=0-1,5-6','bytes=999999999-','bytes=-0','bytes=9-3'):
            assert client.get('/presence/api/character/default',headers={**AUTH,'Range':value}).status_code==416
    assert len(calls)==2 and all(request.headers['range']=='bytes=0-3' for request in calls)


@pytest.mark.parametrize('kind,status,extra',[
    ('text/html',200,{}),
    ('model/gltf-binary',302,{'Location':'https://other.invalid/'}),
    ('model/gltf-binary',200,{'Content-Length':str(presence_proxy.MAX_ASSET_BYTES+1)}),
    ('model/gltf-binary',206,{'Content-Range':'bytes 0-3/999999999'}),
    ('model/gltf-binary',200,{'Content-Encoding':'gzip'}),
])
def test_redirects_oversized_transfers_and_wrong_types_fail_closed(kind,status,extra):
    body=Body(b'test')
    app,_=make_app(lambda request:httpx.Response(status,stream=body,headers={'Content-Type':kind,**extra}))
    with TestClient(app,base_url=BASE) as client:
        result=client.get('/presence/api/character/default',headers=AUTH)
    assert result.status_code==502 and body.closed
    assert 'location' not in result.headers and 'other.invalid' not in result.text


@pytest.mark.anyio
async def test_unknown_length_asset_cap_closes_stream_and_releases_slot(monkeypatch):
    monkeypatch.setattr(presence_proxy,'MAX_ASSET_BYTES',8)
    body=Body(b'12345',b'67890')
    app,service=make_app(lambda request:httpx.Response(200,stream=body,headers={'Content-Type':'model/gltf-binary'}))
    request=Request({'type':'http','method':'GET','path':'/presence/api/character/default','raw_path':b'/presence/api/character/default','query_string':b'','headers':[],'scheme':'http','server':('127.0.0.1',8766)})
    result=await service.serve(request,'api/character/default')
    with pytest.raises(ValueError,match='transfer cap'):
        _=[part async for part in result.body_iterator]
    assert body.closed and service.slots._value==12


@pytest.mark.anyio
async def test_disconnect_closes_upstream_without_buffering_entire_model():
    body=Body(b'x'*65536,b'y'*65536,b'z'*65536)
    app,service=make_app(lambda request:httpx.Response(200,stream=body,headers={'Content-Type':'model/gltf-binary'}))
    request=Request({'type':'http','method':'GET','path':'/presence/api/character/default','raw_path':b'/presence/api/character/default','query_string':b'','headers':[],'scheme':'http','server':('127.0.0.1',8766)})
    result=await service.serve(request,'api/character/default')
    iterator=result.body_iterator
    assert len(await anext(iterator))==65536 and not body.closed
    await iterator.aclose()
    assert body.closed and service.slots._value==12


@pytest.fixture
def anyio_backend():
    return 'asyncio'


def test_full_broker_owner_and_valid_preview_authorities_stay_separate(tmp_path,monkeypatch):
    import jarvis_comm_broker as broker
    import persistent_sessions
    import tester_preview
    monkeypatch.setattr(broker,'HERE',tmp_path)
    original=persistent_sessions.SessionStore
    monkeypatch.setattr(persistent_sessions,'SessionStore',lambda path:original(tmp_path/'owner.sqlite3'))
    app=broker.create_app(broker.Settings(token=TOKEN),task_path=tmp_path/'tasks.sqlite3')
    calls=[]
    handler=lambda request:calls.append(request) or response(b'asset')
    service=getattr(app.state,'presence_proxy',None)
    if service is None:
        dependencies=next(route.dependencies for route in app.routes if route.path=='/v1/workspace')
        service=presence_proxy.register_routes(app,dependencies,transport=httpx.MockTransport(handler))
    else:
        service.transport=httpx.MockTransport(handler)
    # The preview database is isolated alongside the mocked owner session store.
    with TestClient(app,base_url=BASE) as client:
        assert client.get('/presence/static/studio.js').status_code==401
        invited=client.post('/v1/workspace/preview-invites',headers={**AUTH,'Origin':BASE},json={'label':'Synthetic preview','days':1})
        assert invited.status_code==200
        invitation=invited.json()['url'].split('#invite=')[1]
        connected=client.post('/v1/preview/connect',headers={'Origin':BASE},json={'invite':invitation})
        assert connected.status_code==200 and tester_preview.COOKIE in client.cookies
        assert client.get('/presence/api/character/default').status_code==401
        assert client.get('/presence/static/studio.js',headers=AUTH).status_code==200
        assert client.post('/presence/api/speech',headers={**AUTH,'Origin':BASE},json={}).status_code==405
    assert len(calls)==1


def test_canonical_document_redirect_keeps_relative_urls_under_authenticated_prefix():
    calls=[]
    app,_=make_app(lambda request:calls.append(request) or response(b'blocked'))
    with TestClient(app,base_url=BASE) as client:
        assert client.get('/presence',follow_redirects=False).status_code==401
        result=client.get('/presence',headers=AUTH,follow_redirects=False)
        assert result.status_code==307 and result.headers['location']=='/presence/?embed=jarvis'
        assert client.get('/presence?embed=other',headers=AUTH,follow_redirects=False).status_code==400
    assert calls==[]
