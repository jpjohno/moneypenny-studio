import io
import json
import struct
import wave
from unittest.mock import Mock

import pytest
import requests

import app as studio
from speech import Voice

HEADERS = {'X-Studio-Client': 'moneypenny'}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(studio.appearance_settings, 'PATH', tmp_path / 'appearance.json')
    monkeypatch.setattr(studio, 'NATURAL_CHARACTER', tmp_path / 'missing-natural.glb')
    monkeypatch.setattr(studio, 'REFRESHED_CHARACTER', tmp_path / 'missing-refresh.glb')
    monkeypatch.setattr(studio, 'FITTED_CHARACTER', tmp_path / 'missing-fit.glb')
    monkeypatch.setattr(studio, 'FREE_SURFACE_CHARACTER', tmp_path / 'missing-free.glb')
    monkeypatch.setattr(studio, 'STYLED_CHARACTER', tmp_path / 'missing-style.glb')
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


@pytest.mark.parametrize('path', ['/api/personas', '/api/status', '/api/character/default', '/api/motion/library'])
@pytest.mark.parametrize('headers', [{'Origin':'https://other.example'}, {'Sec-Fetch-Site':'cross-site'}, {'Origin':'http://localhost:8766','Sec-Fetch-Site':'same-site'}])
def test_other_websites_cannot_probe_private_read_apis(client, monkeypatch, path, headers):
    get = Mock(side_effect=AssertionError('Untrusted API reads must be rejected before contacting services'))
    catalogue = Mock(side_effect=AssertionError('Untrusted reads must not run the WebUI catalogue subprocess'))
    monkeypatch.setattr(studio.requests, 'get', get)
    monkeypatch.setattr(studio.personas, 'catalogue', catalogue)
    response = client.get(path, headers=headers)
    assert response.status_code == 403
    assert response.headers['Cross-Origin-Resource-Policy'] == 'same-origin'
    assert response.headers.get('Access-Control-Allow-Origin') is None
    get.assert_not_called()
    catalogue.assert_not_called()


def test_trusted_parent_can_embed_but_cannot_directly_read_private_studio_apis(client):
    response = client.get('/?embed=jarvis', headers={'Sec-Fetch-Site':'same-site'})
    assert response.status_code == 200
    policy = response.headers['Content-Security-Policy']
    assert "frame-ancestors 'self' http://127.0.0.1:8766 http://localhost:8766" in policy
    assert "form-action 'self'" in policy
    assert client.get('/api/status?quick=1', headers={'Origin':'http://localhost','Sec-Fetch-Site':'same-origin'}).status_code == 200


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


def test_fixed_local_character_is_reported_and_served(client, monkeypatch, tmp_path):
    monkeypatch.setattr(studio, 'SURFACE_CHARACTER', tmp_path / 'missing-surface.glb')
    candidate = tmp_path / 'candidate.glb'
    payload = b'{}  '
    candidate.write_bytes(b'glTF' + struct.pack('<IIII', 2, 20 + len(payload), len(payload), 0x4e4f534a) + payload)
    monkeypatch.setattr(studio, 'LOCAL_CHARACTER', candidate)
    monkeypatch.setattr(studio.requests, 'get', Mock(side_effect=requests.ConnectionError()))
    status = client.get('/api/status').json
    assert status['character_candidate_ready'] is True
    assert status['character_source'] == 'local-performance-candidate'
    response = client.get('/api/character/default')
    assert response.status_code == 200
    assert response.mimetype == 'model/gltf-binary'
    assert response.data == candidate.read_bytes()


def test_missing_local_character_keeps_sample_fallback(client, monkeypatch, tmp_path):
    monkeypatch.setattr(studio, 'SURFACE_CHARACTER', tmp_path / 'missing-surface.glb')
    monkeypatch.setattr(studio, 'LOCAL_CHARACTER', tmp_path / 'missing.glb')
    monkeypatch.setattr(studio.requests, 'get', Mock(side_effect=requests.ConnectionError()))
    status = client.get('/api/status').json
    assert status['character_candidate_ready'] is False
    assert status['character_source'] == 'bundled-cc0-sample'
    assert client.get('/api/character/default').status_code == 404


def test_surface_candidate_preferred_and_corrupt_surface_falls_back(client, monkeypatch, tmp_path):
    original, surface = tmp_path / 'original.glb', tmp_path / 'surface.glb'
    def glb(payload):
        return b'glTF' + struct.pack('<IIII', 2, 20 + len(payload), len(payload), 0x4e4f534a) + payload
    original.write_bytes(glb(b'{}  '))
    surface.write_bytes(glb(b'{ } '))
    monkeypatch.setattr(studio, 'LOCAL_CHARACTER', original)
    monkeypatch.setattr(studio, 'SURFACE_CHARACTER', surface)
    assert client.get('/api/character/default').data == surface.read_bytes()
    surface.write_bytes(b'glTF' + b'broken')
    assert client.get('/api/character/default').data == original.read_bytes()


def test_free_candidate_preferred_then_previous_surface(client, monkeypatch, tmp_path):
    previous, free = tmp_path / 'previous.glb', tmp_path / 'free.glb'
    def glb(payload):
        return b'glTF' + struct.pack('<IIII', 2, 20 + len(payload), len(payload), 0x4e4f534a) + payload
    previous.write_bytes(glb(b'{}  '))
    free.write_bytes(glb(b'{ } '))
    monkeypatch.setattr(studio, 'SURFACE_CHARACTER', previous)
    monkeypatch.setattr(studio, 'FREE_SURFACE_CHARACTER', free)
    assert client.get('/api/character/default').data == free.read_bytes()
    free.write_bytes(b'not a glb')
    assert client.get('/api/character/default').data == previous.read_bytes()


def test_styled_candidate_and_status_match_with_safe_corrupt_fallback(client, monkeypatch, tmp_path):
    styled, previous = tmp_path / 'styled.glb', tmp_path / 'previous.glb'
    def glb(payload):
        return b'glTF' + struct.pack('<IIII', 2, 20 + len(payload), len(payload), 0x4e4f534a) + payload
    styled.write_bytes(glb(b'{ } '))
    previous.write_bytes(glb(b'{}  '))
    monkeypatch.setattr(studio, 'STYLED_CHARACTER', styled)
    monkeypatch.setattr(studio, 'SURFACE_CHARACTER', previous)
    monkeypatch.setattr(studio.requests, 'get', Mock(side_effect=requests.ConnectionError()))
    assert client.get('/api/status').json['character_revision'] == 'style-v26'
    assert client.get('/api/character/default').data == styled.read_bytes()
    styled.write_bytes(b'broken')
    assert client.get('/api/status').json['character_revision'] == 'surface-v9'
    assert client.get('/api/character/default').data == previous.read_bytes()


def test_fitted_candidate_is_preferred_with_a_verified_previous_fallback(client, monkeypatch, tmp_path):
    fitted, previous = tmp_path / 'fitted.glb', tmp_path / 'previous.glb'
    def glb(payload):
        return b'glTF' + struct.pack('<IIII', 2, 20 + len(payload), len(payload), 0x4e4f534a) + payload
    fitted.write_bytes(glb(b'{ } '))
    previous.write_bytes(glb(b'{}  '))
    monkeypatch.setattr(studio, 'FITTED_CHARACTER', fitted)
    monkeypatch.setattr(studio, 'STYLED_CHARACTER', previous)
    monkeypatch.setattr(studio.requests, 'get', Mock(side_effect=requests.ConnectionError()))
    assert client.get('/api/status').json['character_revision'] == 'style-v27'
    assert client.get('/api/character/default').data == fitted.read_bytes()
    fitted.write_bytes(b'broken')
    assert client.get('/api/status').json['character_revision'] == 'style-v26'
    assert client.get('/api/character/default').data == previous.read_bytes()


def test_quick_presence_status_does_not_wait_for_ollama(client, monkeypatch):
    get = Mock(side_effect=AssertionError('Presence readiness must not query Ollama'))
    monkeypatch.setattr(studio.requests, 'get', get)
    monkeypatch.setattr(studio.voice, 'available', lambda: True)
    monkeypatch.setattr(studio.listening, 'available', lambda: True)
    response = client.get('/api/status?quick=1')
    assert response.status_code == 200
    assert response.json['voice_ready'] is True
    assert response.json['microphone_ready'] is True
    assert 'avatar_ready' in response.json and 'character_revision' in response.json
    assert response.json['models_checked'] is False
    get.assert_not_called()


def test_shared_appearance_is_allowlisted_and_saved_without_account_data(client):
    assert client.get('/api/appearance').json['blouseColor']=='petrol'
    response=client.post('/api/appearance',headers=HEADERS,json={'blouseColor':'navy','hairTone':'brunette','lightBrightness':'0.9'})
    assert response.status_code==200
    assert client.get('/api/appearance').json['blouseColor']=='navy'
    assert client.post('/api/appearance',headers=HEADERS,json={'token':'not-supported'}).status_code==400
    assert client.post('/api/appearance',json={'blouseColor':'ivory'}).status_code==403


def test_latest_character_and_previous_comparison_are_distinct(client, monkeypatch, tmp_path):
    def glb(name, marker):
        payload = json.dumps({'asset': {'version': '2.0'}, 'extras': marker}).encode()
        payload += b' ' * ((-len(payload)) % 4)
        path = tmp_path / name
        path.write_bytes(b'glTF' + struct.pack('<IIII', 2, 20 + len(payload), len(payload), 0x4e4f534a) + payload)
        return path
    latest = glb('latest.glb', 'new')
    previous = glb('previous.glb', 'old')
    monkeypatch.setattr(studio, 'NATURAL_CHARACTER', latest)
    monkeypatch.setattr(studio, 'REFRESHED_CHARACTER', previous)
    monkeypatch.setattr(studio.requests, 'get', Mock(side_effect=requests.ConnectionError()))
    assert client.get('/api/status').json['character_revision'] == 'style-v32'
    assert client.get('/api/character/default').data == latest.read_bytes()
    assert client.get('/api/character/default?look=previous').data == previous.read_bytes()
    assert client.get('/api/character/default?look=../../private').status_code == 400
