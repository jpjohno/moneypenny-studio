import asyncio
import httpx
import cloud_ai

def test_cloud_chat_keeps_schema_and_credentials_server_side(monkeypatch):
    monkeypatch.setattr(cloud_ai.voice_profiles,'selected',lambda:{'model':'gpt-4.1-mini'})
    monkeypatch.setenv('JJRVIS_CLOUD_AI','1')
    monkeypatch.setenv('OPENAI_API_KEY','test-secret')
    def respond(request):
        import json
        body=json.loads(request.content)
        assert request.url.host=='api.openai.com'
        assert request.headers['authorization']=='Bearer test-secret'
        assert body['store'] is False
        assert body['response_format']['json_schema']['schema']=={'type':'object'}
        return httpx.Response(200,json={'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as c:
            r=await cloud_ai.chat(c,'http://localhost',json={'messages':[],'format':{'type':'object'}})
            assert r.json()=={'done':True,'done_reason':'stop','message':{'content':'{}'}}
    asyncio.run(run())


def test_local_selection_never_sends_to_cloud(monkeypatch):
    monkeypatch.setattr(cloud_ai.voice_profiles,'selected',lambda:{'model':'local-moneypenny'})
    def respond(request):
        import json
        assert request.url.host=='127.0.0.1'
        assert 'authorization' not in request.headers
        assert json.loads(request.content)['model']=='MoneyPenny:latest'
        assert json.loads(request.content)['options']['num_ctx']==4096
        return httpx.Response(200,json={'message':{'content':'local answer'}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as c:
            r=await cloud_ai.chat(c,'http://127.0.0.1:11434/api/chat',json={'messages':[]})
            assert r.json()['message']['content']=='local answer'
    asyncio.run(run())

def test_selected_answer_model_reports_ollama_engine(monkeypatch):
    monkeypatch.setattr(cloud_ai.voice_profiles,'selected',lambda:{'model':'ollama:uncensored-3b:latest'})
    assert cloud_ai.selected_answer_model()=='uncensored-3b:latest'
