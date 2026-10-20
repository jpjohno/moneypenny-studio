"""Selected document answers must not acquire unrelated workspace context."""
import asyncio,json
import httpx,pytest
from fastapi import HTTPException
import jjrvis_core as module
from jjrvis_core import Core
from jarvis_comm_broker import Settings
TOKEN='synthetic-selected-document-test-token'
@pytest.fixture
def core(tmp_path):return Core(object(),object(),task_path=tmp_path/'tasks.sqlite')
def fake_model(monkeypatch,content):
    monkeypatch.setenv('JJRVIS_CLOUD_AI','0');requests=[];original=httpx.AsyncClient
    def handler(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={'done':True,'message':{'content':json.dumps(content)}})
    monkeypatch.setattr(module.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    return requests


def test_selected_document_question_uses_only_its_bounded_text_and_no_other_tools(core,monkeypatch):
    monkeypatch.setattr(core,'read_file',lambda key:{'name':'Fixture.pdf','text':'JJRVIS document preview check','modified_at':'2026-10-20T00:00:00+00:00','truncated':False})
    requests=fake_model(monkeypatch,{'answer':'JJRVIS document preview check'})
    result=asyncio.run(core.ask('What phrase is written?',Settings(token=TOKEN),selected_file='fixture'))
    assert result['answer']=='JJRVIS document preview check';assert result['mode']=='selected_document_answer'
    assert len(requests)==1
    evidence=json.loads(requests[0]['messages'][-1]['content'])['evidence']
    assert len(evidence)==1 and evidence[0]['text']=='JJRVIS document preview check'
    assert result['sources'][0]['modified_at'].endswith('+00:00')
    assert result['actions_executed'] is False

def test_selected_document_expiry_returns_a_read_error_without_invoking_model(core,monkeypatch):
    def missing(key):raise HTTPException(404,'Search again to reopen this document')
    monkeypatch.setattr(core,'read_file',missing);requests=fake_model(monkeypatch,{'answer':'must not run'})
    result=asyncio.run(core.ask('Summarise',Settings(token=TOKEN),selected_file='expired'))
    assert result['mode']=='selected_document_unavailable';assert requests==[]
