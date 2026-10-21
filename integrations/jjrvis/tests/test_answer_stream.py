"""Progressive answers preserve authentication, cancellation and validation."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import cloud_ai
import jarvis_comm_broker as broker
import jjrvis_core
from test_core import core

TOKEN = 'isolated-stream-test-token-not-a-real-credential'


@pytest.fixture
def anyio_backend():
    return 'asyncio'


def test_partial_answer_never_emits_json_or_split_escapes():
    assert jjrvis_core.partial_answer('{"source_ids":["S1"],"answer":"Hello') == 'Hello'
    assert jjrvis_core.partial_answer('{"answer":"Hello \\') == 'Hello '
    assert jjrvis_core.partial_answer('{"answer":"Hello \\u20') == 'Hello '
    assert jjrvis_core.partial_answer('{"answer":"Hello \\u2014 \\uD83D') == 'Hello — '
    assert jjrvis_core.partial_answer('{"answer":"Hello \\u2014 \\uD83D\\uDE00"}') == 'Hello — 😀'
    assert jjrvis_core.partial_answer('{"answer":"A \\"quote\\".","source_ids":["S1"]}') == 'A "quote".'


@pytest.mark.anyio
async def test_local_stream_stays_local_and_captures_selection(monkeypatch):
    chosen = {'model': 'ollama:fixture-local', 'profile': 'moneypenny', 'speed': 1.0}
    monkeypatch.setattr(cloud_ai.voice_profiles, 'selected', lambda: dict(chosen))
    monkeypatch.setattr(cloud_ai.voice_profiles, 'resolved_model', lambda model=None: model.removeprefix('ollama:'))
    monkeypatch.setenv('JJRVIS_CLOUD_AI', '1')
    calls, metering = [], []
    monkeypatch.setattr(cloud_ai.usage_meter, 'record', lambda *args, **kwargs: metering.append(args))

    def handler(request):
        calls.append(request)
        body = json.loads(request.content)
        assert request.url.host == '127.0.0.1'
        assert 'authorization' not in request.headers
        assert body['model'] == 'fixture-local'
        assert body['stream'] is True and body['keep_alive'] == '2h'
        assert body['options']['num_ctx'] == 4096
        return httpx.Response(200, text='\n'.join(json.dumps(row) for row in [
            {'message': {'content': '{"answer":"Hello'}, 'done': False},
            {'message': {'content': ' James"}'}, 'done': True, 'done_reason': 'stop'},
        ]))

    async with cloud_ai.answer_selection():
        chosen['model'] = 'gpt-4.1-mini'
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            parts = [part async for part in cloud_ai.chat_stream(client, 'http://127.0.0.1:11434/api/chat', json={'messages': []})]
        assert cloud_ai.selected_answer_model() == 'fixture-local'
    assert cloud_ai.selected_answer_model() == 'gpt-4.1-mini'
    assert ''.join(part['text'] for part in parts) == '{"answer":"Hello James"}'
    assert len(calls) == 1 and len(metering) == 1


def test_local_payload_uses_stable_context_and_preserves_large_review_window():
    assert cloud_ai.local_payload({'options': {'num_ctx': 1536, 'num_predict': 90}}, 'fixture')['options'] == {'num_ctx': 4096, 'num_predict': 90}
    assert cloud_ai.local_payload({'options': {'num_ctx': 2048}}, 'fixture')['options']['num_ctx'] == 4096
    assert cloud_ai.local_payload({'options': {'num_ctx': 16384}}, 'fixture')['options']['num_ctx'] == 16384


@pytest.mark.anyio
async def test_stream_cloud_compatibility_is_final_only(monkeypatch):
    monkeypatch.setattr(cloud_ai.voice_profiles, 'selected', lambda: {'model': 'gpt-4.1-mini'})
    monkeypatch.setenv('JJRVIS_CLOUD_AI', '1')
    monkeypatch.setenv('OPENAI_API_KEY', 'isolated-fixture-key')
    calls = []
    def handler(request):
        calls.append(request)
        assert request.url.host == 'api.openai.com'
        assert json.loads(request.content).get('stream') is not True
        return httpx.Response(200, json={'choices': [{'finish_reason': 'stop', 'message': {'content': '{"answer":"A reply"}'}}]})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        parts = [part async for part in cloud_ai.chat_stream(client, 'http://127.0.0.1:11434/api/chat', json={'messages': []})]
    assert parts == [{'text': '{"answer":"A reply"}', 'done': True, 'done_reason': 'stop'}]
    assert len(calls) == 1


@pytest.mark.anyio
async def test_closing_partial_ollama_stream_closes_upstream_without_retry(monkeypatch):
    monkeypatch.setattr(cloud_ai.voice_profiles, 'selected', lambda: {'model': 'ollama:fixture-local'})
    monkeypatch.setattr(cloud_ai.voice_profiles, 'resolved_model', lambda model=None: model.removeprefix('ollama:'))
    closed, calls = asyncio.Event(), []
    class Body(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'{"message":{"content":"{\\"answer\\":\\"Hello "},"done":false}\n'
            await asyncio.Event().wait()
        async def aclose(self):
            closed.set()
    def handler(request):
        calls.append(request)
        return httpx.Response(200, stream=Body())
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        stream = cloud_ai.chat_stream(client, 'http://127.0.0.1:11434/api/chat', json={'messages': []})
        first = await asyncio.wait_for(anext(stream), 1)
        assert first['text'] == '{"answer":"Hello '
        assert not first['done'] and not closed.is_set()
        await stream.aclose()
        assert closed.is_set()
    assert len(calls) == 1


@pytest.mark.anyio
async def test_plain_chat_delivers_delta_before_generation_finishes(core, monkeypatch):
    emitted, release, first = [], asyncio.Event(), asyncio.Event()
    async def streaming(*args, **kwargs):
        yield {'text': '{"answer":"Hello ', 'done': False}
        first.set()
        await release.wait()
        yield {'text': 'James."}', 'done': True, 'done_reason': 'stop'}
    def unused(*args, **kwargs):
        raise AssertionError('Conversation should not read workspace sources or classify twice')
    monkeypatch.setattr(cloud_ai, 'chat_stream', streaming)
    monkeypatch.setattr(core, 'plan', unused)
    monkeypatch.setattr(core.workspace, 'services', unused)
    task = asyncio.create_task(core.ask('Explain why leaves are green.', broker.Settings(token=TOKEN), emit=emitted.append))
    await asyncio.wait_for(first.wait(), 1)
    assert not task.done()
    assert emitted == [
        {'type':'status','text':'Replying','voice_stream_allowed':True,'provisional':True},
        {'type': 'delta', 'text': 'Hello ', 'provisional': True}]
    release.set()
    result = await task
    assert result['answer'] == 'Hello James.'
    assert result['mode'] == 'local_conversation'
    assert ''.join(item['text'] for item in emitted if item['type']=='delta') == result['answer']


@pytest.mark.anyio
async def test_grounded_stream_rejects_invalid_final_citations(core, monkeypatch):
    calls, emitted = [], []
    async def streaming(*args, **kwargs):
        calls.append(kwargs['json'])
        yield {'text': '{"answer":"A provisional summary.",', 'done': False}
        yield {'text': '"source_ids":["S999"]}', 'done': True, 'done_reason': 'stop'}
    monkeypatch.setattr(cloud_ai, 'chat_stream', streaming)
    with pytest.raises(HTTPException) as failure:
        await core.ask('trading status', broker.Settings(token=TOKEN), emit=emitted.append)
    assert failure.value.status_code == 503
    assert all(event['provisional'] is True for event in emitted)
    assert ''.join(event['text'] for event in emitted) == 'A provisional summary.'
    assert len(calls) == 1


@pytest.mark.anyio
async def test_broken_stream_does_not_retry_with_second_generation(core, monkeypatch):
    calls = []
    async def streaming(*args, **kwargs):
        calls.append(True)
        yield {'text': '{"answer":"An unfinished', 'done': False}
    monkeypatch.setattr(cloud_ai, 'chat_stream', streaming)
    with pytest.raises(HTTPException) as failure:
        await core.ask('Explain why leaves are green.', broker.Settings(token=TOKEN), emit=lambda event: None)
    assert failure.value.status_code == 503 and len(calls) == 1


def make_app(tmp_path, monkeypatch):
    monkeypatch.setattr(broker, 'HERE', tmp_path)
    return broker.create_app(broker.Settings(token=TOKEN), task_path=tmp_path/'tasks.db')


def test_stream_endpoint_is_authenticated_and_final_shape_is_stable(tmp_path, monkeypatch):
    async def answer(self, question, *args, emit=None, **kwargs):
        emit({'type': 'delta', 'text': 'Hello', 'provisional': True})
        return {'answer': 'Hello James.', 'model': 'fixture-local', 'sources': [], 'actions_executed': False}
    monkeypatch.setattr(jjrvis_core.Core, 'ask', answer)
    app = make_app(tmp_path, monkeypatch)
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        assert client.post('/v1/workspace/ask/stream', json={'question': 'Hello'}).status_code == 401
        response = client.post('/v1/workspace/ask/stream', headers={'Authorization': 'Bearer '+TOKEN}, json={'question': 'Hello'})
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/x-ndjson')
    assert response.headers['cache-control'] == 'no-store'
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[0]['type'] == 'status'
    assert events[1] == {'type': 'delta', 'text': 'Hello', 'provisional': True}
    assert events[2]['type'] == 'final' and events[2]['data']['answer'] == 'Hello James.'


def test_cookie_stream_requires_same_origin(tmp_path, monkeypatch):
    app = make_app(tmp_path, monkeypatch)
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        ticket = client.post('/v1/workspace/session-ticket', headers={'Authorization': 'Bearer '+TOKEN}, json={}).json()['ticket']
        assert client.get('/workspace/connect', params={'ticket': ticket}, follow_redirects=False).status_code == 303
        assert client.post('/v1/workspace/ask/stream', json={'question': 'Hello'}).status_code == 403


def test_stream_internal_error_is_sanitised(tmp_path, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError('Authorization: Bearer private-diagnostic-key')
    monkeypatch.setattr(jjrvis_core.Core, 'ask', broken)
    app = make_app(tmp_path, monkeypatch)
    with TestClient(app, base_url='http://127.0.0.1:8766') as client:
        response = client.post('/v1/workspace/ask/stream', headers={'Authorization': 'Bearer '+TOKEN}, json={'question': 'Hello'})
    events = [json.loads(line) for line in response.text.splitlines()]
    assert events[-1]['type'] == 'error' and events[-1]['status'] == 503
    assert 'private-diagnostic' not in response.text


@pytest.mark.anyio
async def test_stream_close_cancels_inference_and_releases_shared_gate(tmp_path, monkeypatch):
    started, cancelled = asyncio.Event(), asyncio.Event()
    async def answer(self, question, *args, **kwargs):
        if question == 'New question':
            return {'answer': 'A new answer'}
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    monkeypatch.setattr(jjrvis_core.Core, 'ask', answer)
    app = make_app(tmp_path, monkeypatch)
    stream = next(route.endpoint for route in app.routes if route.path == '/v1/workspace/ask/stream')
    ordinary = next(route.endpoint for route in app.routes if route.path == '/v1/workspace/ask')
    class Request:
        async def is_disconnected(self):
            return False
    response = await stream(broker.AssistantQuestion(question='Old question'), Request())
    iterator = response.body_iterator
    assert json.loads(await anext(iterator))['type'] == 'status'
    await asyncio.wait_for(started.wait(), 1)
    with pytest.raises(HTTPException) as failure:
        await ordinary(broker.AssistantQuestion(question='New question'), Request())
    assert failure.value.status_code == 409
    await iterator.aclose()
    assert cancelled.is_set()
    assert await ordinary(broker.AssistantQuestion(question='New question'), Request()) == {'answer': 'A new answer'}


@pytest.mark.anyio
@pytest.mark.parametrize('question,history', [
    ('Explain compound interest simply.', []),
    ('Tell a short joke about a penguin.', [{'role':'user','content':'My private inbox has a bank statement.'}]),
    ('Tell a short joke about a penguin.', [{'role':'user','content':'The fixture password=DO_NOT_READ_ALOUD is private.'}]),
])
async def test_sensitive_conversation_never_opts_into_early_speech(core, monkeypatch, question, history):
    async def streaming(*args, **kwargs):
        yield {'text':'{"answer":"A concise reply."}', 'done':True, 'done_reason':'stop'}
    monkeypatch.setattr(cloud_ai, 'chat_stream', streaming)
    events=[]
    result=await core.ask(question, broker.Settings(token=TOKEN), history=history, emit=events.append)
    assert result['mode']=='local_conversation'
    assert not any(event.get('voice_stream_allowed') for event in events)


@pytest.mark.anyio
async def test_cloud_conversation_does_not_opt_into_early_local_speech(core, monkeypatch):
    monkeypatch.setattr(cloud_ai.voice_profiles, 'selected', lambda: {'model':'gpt-4.1-mini','profile':'moneypenny','speed':1.0})
    monkeypatch.setenv('JJRVIS_CLOUD_AI','1')
    async def streaming(*args, **kwargs):
        yield {'text':'{"answer":"A concise reply."}', 'done':True, 'done_reason':'stop'}
    monkeypatch.setattr(cloud_ai, 'chat_stream', streaming)
    events=[]
    await core.ask('Explain why leaves are green.', broker.Settings(token=TOKEN), emit=events.append)
    assert not any(event.get('voice_stream_allowed') for event in events)


@pytest.mark.anyio
async def test_complete_conversation_json_at_token_limit_is_usable(core, monkeypatch):
    calls=[]
    async def streaming(*args, **kwargs):
        calls.append(kwargs['json'])
        yield {'text':'{"answer":"Leaves look green because chlorophyll reflects green light."}', 'done':True, 'done_reason':'length'}
    monkeypatch.setattr(cloud_ai, 'chat_stream', streaming)
    result=await core.ask('Explain why leaves are green.', broker.Settings(token=TOKEN), emit=lambda event:None)
    assert result['answer']=='Leaves look green because chlorophyll reflects green light.'
    assert len(calls)==1
    assert '25–45 words' in calls[0]['messages'][0]['content']


@pytest.mark.anyio
@pytest.mark.parametrize('content', ['{"answer":"Unfinished', '{"answer":"Complete.","unexpected":"field"}'])
async def test_incomplete_or_extra_conversation_fields_still_fail(core, monkeypatch, content):
    async def streaming(*args, **kwargs):
        yield {'text':content, 'done':True, 'done_reason':'length'}
    monkeypatch.setattr(cloud_ai, 'chat_stream', streaming)
    with pytest.raises(HTTPException) as failure:
        await core.ask('Explain why leaves are green.', broker.Settings(token=TOKEN), emit=lambda event:None)
    assert failure.value.status_code==503
