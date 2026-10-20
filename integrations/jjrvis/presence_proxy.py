"""Owner-only render transport to the fixed local Moneypenny studio.

This module publishes no new host and grants no avatar asset licence. It forwards
only the renderer's inert GET/HEAD requests, never studio writes or credentials.
"""
from __future__ import annotations

import asyncio
import re
import secrets
from html import escape
from html.parser import HTMLParser
from urllib.parse import urlencode

import anyio
import httpx
from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse, Response, StreamingResponse

UPSTREAM = "http://127.0.0.1:8090/"
MAX_ASSET_BYTES = 70 * 1024 * 1024
MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_STREAM_SECONDS = 120
STATIC_FILES = frozenset({
    'seat-support.js', 'rig-view.js', 'live.js', 'motion.js', 'studio-paths.js',
    'studio-tools.js', 'appearance.js', 'studio.js', 'record-worklet.js',
    'presence-audio.js', 'action-commands.js', 'model-choice.js', 'studio.css',
    'correctives.js', 'rig.js', 'motion-library.js', 'render-budget.js',
    'recorder.js', 'wardrobe.js',
})
ASSET_SUFFIXES = frozenset({'.js', '.mjs', '.css', '.wasm', '.bin', '.onnx',
                           '.glb', '.gltf', '.png', '.jpg', '.jpeg', '.webp',
                           '.gif', '.svg', '.json', '.ktx2'})


def _safe_path(path: str) -> bool:
    if not re.fullmatch(r'[A-Za-z0-9_./-]*', path) or any(
            segment in {'.', '..'} or segment.startswith('.') for segment in path.split('/') if segment):
        return False
    if '//' in path:
        return False
    if not path:
        return True
    if path in {'api/status', 'api/appearance', 'api/character/default', 'api/motion/library'}:
        return True
    if re.fullmatch(r'api/motion/assets/[A-Za-z0-9_-]{1,100}(?:\.(?:glb|gltf|json))?', path):
        return True
    if path.startswith('static/') and path[7:] in STATIC_FILES:
        return True
    prefix = next((prefix for prefix in (
        'static/vendor/talkinghead/', 'static/vendor/headaudio/', 'static/avatars/',
        'static/motions/', 'vendor/three/build/', 'vendor/three/examples/jsm/',
        'vendor/vad/', 'vendor/onnx/',
    ) if path.startswith(prefix)), None)
    return prefix is not None and any(path.endswith(suffix) for suffix in ASSET_SUFFIXES)


def _range(value: str | None) -> str | None:
    if value is None:
        return None
    match = re.fullmatch(r'bytes=(\d{1,9})-(\d{0,9})', value)
    suffix = re.fullmatch(r'bytes=-(\d{1,9})', value)
    if match:
        start = int(match[1]); end = int(match[2]) if match[2] else None
        if start >= MAX_ASSET_BYTES or (end is not None and (end < start or end >= MAX_ASSET_BYTES)):
            raise HTTPException(416, 'Asset range outside permitted bounds')
        return value
    if suffix and 0 < int(suffix[1]) <= MAX_ASSET_BYTES:
        return value
    raise HTTPException(416, 'A single bounded asset range is required')


def _query(request: Request, path: str) -> str:
    items = list(request.query_params.multi_items())
    if len(items) > 3 or any(len(key) > 20 or len(value) > 100 for key, value in items):
        raise HTTPException(400, 'Unsupported render query')
    if not path:
        if any(key != 'embed' or value != 'jarvis' for key, value in items):
            raise HTTPException(400, 'Only the embedded renderer is available')
        return 'embed=jarvis'
    if path == 'api/status':
        if any(key != 'quick' or value != '1' for key, value in items):
            raise HTTPException(400, 'Only the quick renderer status is available')
        return 'quick=1'
    if any(key not in {'v', 'rev', 'version'} or not re.fullmatch(r'[A-Za-z0-9._-]*', value) for key, value in items):
        raise HTTPException(400, 'Unsupported render query')
    return urlencode(items)


def _same_origin(request: Request):
    origin = request.headers.get('origin')
    expected = f'{request.url.scheme}://{request.url.netloc}'
    if origin is not None and origin != expected:
        raise HTTPException(403, 'Same-origin render request required')
    if request.headers.get('sec-fetch-site') not in {None, 'same-origin', 'none'}:
        raise HTTPException(403, 'Same-origin render request required')


def _rewrite_url(value: str) -> str:
    return '/presence' + value if value.startswith(('/static/', '/vendor/', '/api/')) else value


class _StudioHTML(HTMLParser):
    """Nonce existing trusted-local script blocks without allowing remote URLs."""
    def __init__(self, nonce):
        super().__init__(convert_charrefs=False)
        self.nonce = nonce
        self.out = []
        self.in_script = False
        self.in_head = False

    def handle_starttag(self, tag, attrs):
        attrs = [(key, value) for key, value in attrs if key != 'nonce']
        if tag == 'script':
            attrs.append(('nonce', self.nonce))
            self.in_script = True
        rebuilt=[]
        for key, value in attrs:
            if value is not None and key in {'src', 'href'}:
                value = _rewrite_url(value)
            rebuilt.append(' '+key if value is None else ' '+key+'="'+escape(value, quote=True)+'"')
        self.out.append('<'+tag+''.join(rebuilt)+'>')
        if tag == 'head':
            self.in_head = True
            self.out.append('<meta name="studio-base" content="/presence/">')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.out[-1] = self.out[-1][:-1] + '/>'

    def handle_endtag(self, tag):
        self.out.append('</'+tag+'>')
        if tag == 'script':
            self.in_script = False
        if tag == 'head':
            self.in_head = False

    def handle_data(self, data):
        if self.in_script:
            data = re.sub(r'(?<=["\'])(/(?:static|vendor|api)/)', '/presence\\1', data)
        self.out.append(data)

    def handle_entityref(self, name):
        self.out.append('&'+name+';')

    def handle_charref(self, name):
        self.out.append('&#'+name+';')

    def handle_comment(self, data):
        self.out.append('<!--'+data+'-->')

    def handle_decl(self, decl):
        self.out.append('<!'+decl+'>')


def _html(data: bytes, nonce: str) -> bytes:
    parser = _StudioHTML(nonce)
    parser.feed(data.decode('utf-8'))
    parser.close()
    if not any('name="studio-base"' in part for part in parser.out):
        raise ValueError('Studio document has no head')
    return ''.join(parser.out).encode('utf-8')


def _headers(upstream: httpx.Response, path: str) -> dict:
    output = {'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'}
    for key in ('etag', 'last-modified'):
        value = upstream.headers.get(key)
        if value is not None and len(value) <= 300 and not re.search(r'[\x00-\x1f\x7f]', value):
            output[key] = value
    content_type = upstream.headers.get('content-type', '').strip()
    if not content_type or len(content_type) > 160:
        raise ValueError('Missing render content type')
    expected = 'text/html' if not path else 'application/json' if path in {'api/status','api/appearance','api/motion/library'} else None
    if expected and content_type.split(';')[0].strip() != expected:
        raise ValueError('Unexpected render content type')
    if path and content_type.split(';')[0].strip() in {'text/html','application/xhtml+xml'}:
        raise ValueError('Unexpected render document')
    output['Content-Type'] = content_type
    if upstream.headers.get('content-encoding', 'identity') != 'identity':
        raise ValueError('Encoded render transfer unsupported')
    length = upstream.headers.get('content-length')
    if length is not None:
        if not length.isdigit() or int(length) > (MAX_HTML_BYTES if not path else MAX_ASSET_BYTES):
            raise ValueError('Render asset too large')
        output['Content-Length'] = length
    if upstream.status_code == 206:
        value = upstream.headers.get('content-range', '')
        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', value)
        if not match or not 0 <= int(match[1]) <= int(match[2]) < int(match[3]) <= MAX_ASSET_BYTES:
            raise ValueError('Invalid asset range')
        if length is not None and int(length) != int(match[2])-int(match[1])+1:
            raise ValueError('Invalid asset range length')
        output['Content-Range'] = value
    if upstream.headers.get('accept-ranges') == 'bytes':
        output['Accept-Ranges'] = 'bytes'
    return output


class PresenceProxy:
    def __init__(self, transport=None):
        self.transport = transport
        self.slots = asyncio.Semaphore(12)

    async def canonical(self, request: Request):
        _same_origin(request)
        _query(request, '')
        return RedirectResponse('/presence/?embed=jarvis', status_code=307)

    async def serve(self, request: Request, path: str = ''):
        _same_origin(request)
        if not _safe_path(path) or re.search(rb'%|\\', request.scope.get('raw_path', b'')):
            raise HTTPException(404, 'Renderer route unavailable')
        query = _query(request, path)
        headers = {'Accept-Encoding':'identity'}
        if path:
            requested_range = _range(request.headers.get('range'))
            if requested_range:
                headers['Range'] = requested_range
        elif request.headers.get('range'):
            raise HTTPException(416, 'Document ranges are unavailable')
        request.state.presence_frame = True
        nonce = secrets.token_urlsafe(24)
        request.state.presence_csp = (
            "default-src 'self'; base-uri 'none'; object-src 'none'; form-action 'none'; "
            f"script-src 'self' 'nonce-{nonce}' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; connect-src 'self' blob:; media-src 'self' blob:; "
            "worker-src 'self' blob:; frame-src 'none'; frame-ancestors 'self'")
        try:
            await asyncio.wait_for(self.slots.acquire(), 2)
        except TimeoutError:
            raise HTTPException(429, 'Renderer busy; retry shortly')
        client = httpx.AsyncClient(timeout=httpx.Timeout(20, connect=3), trust_env=False,
                                   follow_redirects=False, transport=self.transport)
        upstream = None
        closed = False
        async def close():
            nonlocal closed
            if closed:
                return
            closed = True
            with anyio.CancelScope(shield=True):
                try:
                    if upstream is not None:
                        await upstream.aclose()
                finally:
                    try:
                        await client.aclose()
                    finally:
                        self.slots.release()
        try:
            upstream = await client.send(client.build_request(request.method, UPSTREAM+path+('?' + query if query else ''), headers=headers), stream=True)
            if upstream.status_code not in {200, 206}:
                raise HTTPException(502, 'Local renderer asset unavailable')
            output = _headers(upstream, path)
            if not path and request.method != 'HEAD':
                data=bytearray()
                async with asyncio.timeout(15):
                    async for chunk in upstream.aiter_raw():
                        data.extend(chunk)
                        if len(data)>MAX_HTML_BYTES:
                            raise ValueError('Studio document too large')
                body=_html(bytes(data), nonce)
                output.pop('Content-Length',None)
                await close()
                return Response(body, status_code=200, headers=output)
            if request.method == 'HEAD':
                await close()
                return Response(status_code=upstream.status_code, headers=output)
            async def chunks():
                size=0
                try:
                    async with asyncio.timeout(MAX_STREAM_SECONDS):
                        async for chunk in upstream.aiter_raw(64*1024):
                            size+=len(chunk)
                            if size>MAX_ASSET_BYTES:
                                raise ValueError('Render asset exceeded transfer cap')
                            yield chunk
                finally:
                    await close()
            return StreamingResponse(chunks(), status_code=upstream.status_code, headers=output)
        except (httpx.HTTPError, ValueError, UnicodeError, TimeoutError):
            await close()
            raise HTTPException(502, 'Local renderer unavailable') from None
        except BaseException:
            await close()
            raise


def register_routes(app, secure, *, transport=None):
    service = PresenceProxy(transport=transport)
    app.add_api_route('/presence', service.canonical, methods=['GET','HEAD'], dependencies=secure)
    app.add_api_route('/presence/', service.serve, methods=['GET','HEAD'], dependencies=secure)
    app.add_api_route('/presence/{path:path}', service.serve, methods=['GET','HEAD'], dependencies=secure)
    app.state.presence_proxy = service
    return service
