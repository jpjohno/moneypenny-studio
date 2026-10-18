"""The inventory may inspect local readiness; it must never activate hardware."""
import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest

import connection_status as status


@pytest.fixture
def inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(status.voice_profiles, 'selected', lambda: {'model': 'ollama:uncensored-3b:latest'})
    monkeypatch.setattr(status.cloud_ai, 'enabled', lambda: True)
    monkeypatch.setattr(status.cloud_ai, 'key', lambda: 'PRIVATE_API_KEY')
    settings = SimpleNamespace(ollama_url='http://127.0.0.1:11434', model='fallback-local', origins=())
    infrastructure = SimpleNamespace(_registry=lambda: {'entities': [{'id': 'camera.front_door', 'disabled': False}]})
    return tmp_path, settings, infrastructure


def test_local_selection_stays_local_and_check_does_not_generate_or_expose_secrets(inventory):
    folder, settings, infrastructure = inventory
    (folder/'bmw-vehicle.json').write_text(json.dumps({'vin': 'PRIVATE_VIN', 'container_id': 'PRIVATE_CONTAINER'}))
    (folder/'bmw-tokens.json').write_text(json.dumps({'refresh_token': 'PRIVATE_TOKEN'}))
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == 'GET' and request.url.host == '127.0.0.1'
        if request.url.path == '/api/tags':
            return httpx.Response(200, json={'models': [{'name': 'uncensored-3b:latest'}]})
        if request.url.path == '/api/ps':
            return httpx.Response(200, json={'models': []})
        assert request.url.port == 8090 and request.url.path == '/api/status'
        assert request.url.params['quick'] == '1', 'Avatar readiness must not wait on a second Ollama inventory call'
        assert request.extensions['timeout']['read'] == status.STUDIO_TIMEOUT_SECONDS
        return httpx.Response(200, json={'avatar_ready': True, 'voice_ready': True, 'microphone_ready': True, 'character_revision': 'style-v26'})
    result = asyncio.run(status.snapshot(settings, infrastructure, runtime=folder, private_config=folder,
                                        transport=httpx.MockTransport(handler)))
    assert len(calls) == 3
    assert result['ai']['provider'] == 'ollama' and result['ai']['state'] == 'ready'
    assert result['ai']['selected_model_loaded'] is False
    assert result['ai']['cloud']['automatic_fallback'] is False
    assert result['ai']['cloud']['connection_verified'] is False
    assert result['cameras']['state'] == 'registered_only'
    assert result['cameras']['live_video_connected'] is False
    assert result['vehicle']['state'] == 'configured_unverified'
    assert result['vehicle']['network_request_by_this_check'] is False
    assert result['phones']['state'] == 'private_access_required'
    assert 'PRIVATE' not in json.dumps(result)


def test_unavailable_services_are_not_reported_ready(inventory):
    folder, settings, infrastructure = inventory
    transport = httpx.MockTransport(lambda request: httpx.Response(503))
    result = asyncio.run(status.snapshot(settings, infrastructure, runtime=folder, private_config=folder, transport=transport))
    assert result['ai']['state'] == 'unavailable'
    assert result['ai']['selected_model_installed'] is None
    assert result['ai']['catalogue_check']['reason'] == 'http_error'
    assert result['ai']['catalogue_check']['status_code'] == 503
    assert result['moneypenny']['state'] == 'unavailable'
    assert result['vehicle']['state'] == 'authorisation_required'


def test_cloud_disabled_uses_actual_local_fallback_model(inventory, monkeypatch):
    folder, settings, infrastructure = inventory
    monkeypatch.setattr(status.voice_profiles, 'selected', lambda: {'model': 'gpt-4.1-mini'})
    monkeypatch.setattr(status.cloud_ai, 'enabled', lambda: False)
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={'models': [{'name': 'fallback-local'}]}))
    result = asyncio.run(status.snapshot(settings, infrastructure, runtime=folder, private_config=folder, transport=transport))
    assert result['ai']['provider'] == 'ollama'
    assert result['ai']['selected_model'] == 'fallback-local'
    assert result['ai']['state'] == 'ready'


def test_slow_ollama_does_not_hide_ready_avatar_or_claim_missing_model(inventory, monkeypatch):
    folder, settings, infrastructure = inventory
    monkeypatch.setattr(status, 'OLLAMA_TIMEOUT_SECONDS', .02)
    calls = []
    async def handler(request):
        calls.append(request)
        assert request.method == 'GET' and request.url.host == '127.0.0.1'
        if request.url.port == 11434:
            await asyncio.sleep(1)
            pytest.fail('The outer deadline must cancel a stalled inventory request')
        assert request.url.params['quick'] == '1'
        return httpx.Response(200, json={'avatar_ready': True, 'voice_ready': True, 'microphone_ready': True})
    result = asyncio.run(status.snapshot(settings, infrastructure, runtime=folder, private_config=folder,
                                        transport=httpx.MockTransport(handler)))
    assert len(calls) == 3, 'One request per inventory endpoint, without retry or inference'
    assert result['moneypenny']['state'] == 'ready'
    assert result['moneypenny']['check']['state'] == 'ready'
    assert result['ai']['state'] == 'unavailable'
    assert result['ai']['selected_model_installed'] is None
    assert result['ai']['selected_model_loaded'] is None
    assert result['ai']['catalogue_check']['reason'] == 'timeout'
    assert result['ai']['loaded_models_check']['reason'] == 'timeout'


@pytest.mark.parametrize('payload', [{}, {'models': 'not-a-model-list'}, []])
def test_invalid_catalogue_is_unavailable_rather_than_a_missing_model(inventory, payload):
    folder, settings, infrastructure = inventory
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    result = asyncio.run(status.snapshot(settings, infrastructure, runtime=folder, private_config=folder, transport=transport))
    assert result['ai']['state'] == 'unavailable'
    assert result['ai']['selected_model_installed'] is None
    assert result['ai']['catalogue_check']['reason'] == 'invalid_response'


def test_valid_empty_catalogue_identifies_missing_weights(inventory):
    folder, settings, infrastructure = inventory
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={'models': []}))
    result = asyncio.run(status.snapshot(settings, infrastructure, runtime=folder, private_config=folder, transport=transport))
    assert result['ai']['state'] == 'model_missing'
    assert result['ai']['selected_model_installed'] is False
    assert result['ai']['catalogue_check']['state'] == 'ready'


def test_connections_endpoint_requires_authentication(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from jarvis_comm_broker import Settings, create_app
    import persistent_sessions
    original_store = persistent_sessions.SessionStore
    monkeypatch.setattr(persistent_sessions, 'SessionStore', lambda path: original_store(tmp_path/'sessions.sqlite3'))
    async def fake_snapshot(*args, **kwargs):
        return {'ai': {'state': 'unavailable'}}
    monkeypatch.setattr(status, 'snapshot', fake_snapshot)
    token = 'isolated-connection-test-token-not-a-real-credential'
    with TestClient(create_app(Settings(token=token)), base_url='http://127.0.0.1:8766') as client:
        assert client.get('/v1/workspace/connections').status_code == 401
        response = client.get('/v1/workspace/connections', headers={'Authorization': 'Bearer '+token})
        assert response.status_code == 200
        assert response.json() == {'ai': {'state': 'unavailable'}}
