from fastapi.testclient import TestClient
from jarvis_comm_broker import Settings, create_app
import cloud_ai

def test_long_briefing_reaches_speech_and_returns_audio(monkeypatch):
    calls=[]
    async def speech(text, profile=None):
        assert profile['voice'] == 'bf_emma'
        calls.append(text)
        return b'ID3test'
    monkeypatch.setattr(cloud_ai,'speech',speech)
    token='isolated-voice-test-not-a-real-credential'
    app=create_app(Settings(token=token))
    with TestClient(app,base_url='http://127.0.0.1:8766',headers={'Authorization':'Bearer '+token}) as client:
        for size in (801,1600,2400):
            response=client.post('/v1/workspace/voice/audio',json={'text':'a'*size})
            assert response.status_code==200
            assert response.headers['content-type']=='audio/wav'
            assert response.headers['x-jjrvis-voice-provider']=='local-kokoro'
            assert len(calls[-1])==size
        assert client.post('/v1/workspace/voice/audio',json={'text':'a'*2401}).status_code==422
        assert len(calls)==3
