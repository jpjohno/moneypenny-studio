"""Search challenges are a browser handoff, never invented sources or a retry loop."""
import asyncio
import httpx
import jjrvis_core as module
from jarvis_comm_broker import Settings
from test_core import core, TOKEN


def test_search_verification_challenge_is_explicit_and_does_not_run_the_model(core, tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'HERE', tmp_path)
    original = httpx.AsyncClient
    calls=[]
    def handler(request):
        calls.append(request)
        assert request.method == 'GET' and request.url.host == 'html.duckduckgo.com'
        return httpx.Response(202, text='<form class="anomaly-modal"><p>Captcha</p></form>')
    monkeypatch.setattr(module.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result=asyncio.run(core.ask('Search the web for official browser documentation.',Settings(token=TOKEN)))
    assert result['mode']=='live_web_unavailable'
    assert result['web_state']=='browser_verification_needed'
    assert result['web_query']=='official browser documentation.'
    assert result['web_results']==[] and result['actions_executed'] is False
    assert 'browser verification' in result['answer']
    assert len(calls)==1


def test_normal_search_result_still_works_without_a_challenge(core, tmp_path, monkeypatch):
    monkeypatch.setattr(module, 'HERE', tmp_path)
    original=httpx.AsyncClient
    def handler(request):
        assert request.url.host=='html.duckduckgo.com'
        return httpx.Response(200, text='<a class="result__a" href="https://example.invalid/guide">Documentation</a><a class="result__snippet">Public guide.</a>')
    monkeypatch.setattr(module.httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    result=asyncio.run(core.ask('Search online for official browser documentation.', Settings(token=TOKEN)))
    assert result['mode']=='live_web_results' and len(result['web_results'])==1
