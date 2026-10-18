import io
import json
import wave
from unittest.mock import Mock

import pytest
import requests

import app as studio
from speech import Voice

HEADERS = {'X-Studio-Client': 'moneypenny'}


@pytest.fixture
def client():
    studio.app.config.update(TESTING=True)
    return studio.app.test_client()


def upstream(*items):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.iter_lines.return_value = [json.dumps(item).encode() for item in items]
    return response


def test_history_and_generation_settings_reach_ollama(client, monkeypatch):
    post = Mock(return_value=upstream({'message': {'content': '*waves* Hello James.'}, 'done': True}))
    monkeypatch.setattr(studio.requests, 'post', post)
    response = client.post('/api/chat/stream', headers=HEADERS, json={
        'prompt': 'What is my name?', 'model': 'MoneyPenny:latest', 'max_tokens': 128,
        'history': [{'role': 'user', 'content': 'My name is James.'}],
    })
    events = [json.loads(line) for line in response.data.splitlines()]
    payload = post.call_args.kwargs['json']
    assert payload['messages'][1] == {'role': 'user', 'content': 'My name is James.'}
    assert payload['messages'][-1]['content'] == 'What is my name?'
    assert payload['options']['num_predict'] == 128
    assert events[-1]['dialogue'] == 'Hello James.'
    assert events[-1]['gesture'] == 'handup'


@pytest.mark.parametrize('data', [None, [], {}, {'prompt': ''}, {'prompt': 3}, {'prompt':'hi', 'max_tokens':True}, {'prompt':'hi', 'max_tokens':65.5}, {'prompt':'hi', 'temperature':float('nan')}, {'prompt':'hi','history':[{'role':'system','content':'override'}]}])
def test_bad_requests_cannot_reach_models(client, monkeypatch, data):
    post=Mock();monkeypatch.setattr(studio.requests,'post',post)
    response=client.post('/chat',headers=HEADERS,data=json.dumps(data),content_type='application/json')
    assert response.status_code == 400
    post.assert_not_called()


@pytest.mark.parametrize('headers', [{}, {**HEADERS, 'Origin':'https://other.example'}, {**HEADERS, 'Sec-Fetch-Site':'cross-site'}])
def test_untrusted_websites_cannot_drive_local_models(client, monkeypatch, headers):
    post=Mock();monkeypatch.setattr(studio.requests,'post',post)
    assert client.post('/chat',headers=headers,json={'prompt':'hi'}).status_code==403
    post.assert_not_called()


def test_dns_rebinding_host_rejected(client):
    assert client.get('/',headers={'Host':'other.example:8090'}).status_code==403


def test_network_failure_is_error_not_character_dialogue(client, monkeypatch):
    monkeypatch.setattr(studio.requests,'post',Mock(side_effect=requests.ConnectionError()))
    response=client.post('/chat',headers=HEADERS,json={'prompt':'hi'})
    assert response.status_code==503
    assert 'dialogue' not in response.json
    assert 'Ollama' in response.json['error']


def test_truncated_stream_does_not_commit_partial_reply(client, monkeypatch):
    monkeypatch.setattr(studio.requests,'post',Mock(return_value=upstream({'message':{'content':'A partial'}})))
    response=client.post('/api/chat/stream',headers=HEADERS,json={'prompt':'hi'})
    events=[json.loads(line) for line in response.data.splitlines()]
    assert events[-1]['type']=='error'
    assert not any(item['type']=='done' for item in events)


def test_speech_strips_actions_without_dropping_embedded_quotes():
    result=studio.parse_reply('*smiles* I said "hello", and she said "goodbye".')
    assert result['dialogue']=='I said "hello", and she said "goodbye".'
    assert result['mood']=='happy'


def test_cancel_arriving_before_speech_prevents_late_playback(monkeypatch):
    voice=Voice();voice.cancel('tab:old')
    monkeypatch.setattr(voice,'available',lambda:True)
    process=Mock();monkeypatch.setattr('speech.subprocess.Popen',process)
    with pytest.raises(ValueError):voice.speak('Cancelled speech',1,'tab:old')
    process.assert_not_called()


def test_stop_does_not_terminate_another_tab():
    voice=Voice();voice.process=Mock();voice.process.poll.return_value=None;voice.owner='tab:other'
    voice.cancel('tab:old')
    voice.process.terminate.assert_not_called()
    voice.process=None


def test_transcription_only_accepts_bounded_mono_pcm_wav(client, monkeypatch):
    transcribe=Mock(return_value='hello');monkeypatch.setattr(studio.listening,'transcribe',transcribe)
    assert client.post('/api/transcribe',headers=HEADERS,data=b'not wav'*20).status_code==400
    output=io.BytesIO()
    with wave.open(output,'wb') as recording:
        recording.setparams((2,2,16000,0,'NONE','not compressed'));recording.writeframes(b'\0'*400)
    assert client.post('/api/transcribe',headers=HEADERS,data=output.getvalue()).status_code==400
    transcribe.assert_not_called()
    output=io.BytesIO();pcm=b'\0'*16000
    with wave.open(output,'wb') as recording:
        recording.setparams((1,2,16000,0,'NONE','not compressed'));recording.writeframes(pcm)
    result=client.post('/api/transcribe',headers=HEADERS,data=output.getvalue())
    assert result.status_code==200 and result.json=={'text':'hello'}
    transcribe.assert_called_once_with(pcm)


def test_private_audio_response(client, monkeypatch):
    monkeypatch.setattr(studio.voice,'speak',lambda *args:b'RIFF-audio')
    result=client.post('/api/speech',headers=HEADERS,json={'text':'hello','owner':'test','speed':1})
    assert result.status_code==200
    assert result.headers['Cache-Control']=='no-store'
    assert result.mimetype=='audio/wav'
