import pytest
from workspace_assets import AssetProfiles

def test_profiles_do_not_imply_tracking(tmp_path):
    profiles = AssetProfiles(tmp_path/'profiles.json')
    assert {r['id'] for r in profiles.list()['assets']} == {'kit-bmw', 'enkidu'}
    result = profiles.add({'name':'Fixture person', 'kind':'person'})
    assert len(result['assets']) == 3
    assert all(not r['tracking_enabled'] and r['location_state']=='unavailable' for r in result['assets'])
    assert profiles.path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError): profiles.add({'name':'Fixture person', 'kind':'person'})
    with pytest.raises(ValueError): profiles.add({'name':'Someone', 'kind':'automatic_tracker'})

def test_asset_routes_require_owner_session(tmp_path, monkeypatch):
    import jarvis_comm_broker as broker
    from fastapi.testclient import TestClient
    monkeypatch.setattr(broker, 'HERE', tmp_path)
    app = broker.create_app(broker.Settings(token='isolated-fixture-token-for-testing-only'), task_path=tmp_path/'tasks.sqlite')
    client = TestClient(app, base_url='http://127.0.0.1:8766')
    assert client.get('/v1/workspace/assets').status_code == 401
    assert client.post('/v1/workspace/assets', json={'name':'Fixture','kind':'person'}).status_code == 401
    headers = {'Authorization':'Bearer isolated-fixture-token-for-testing-only'}
    assert client.post('/v1/workspace/assets', json={'name':'Fixture','kind':'person'},headers=headers).status_code == 200
    assert len(client.get('/v1/workspace/assets',headers=headers).json()['assets']) == 3
    client.close()
