import io
import json

import pytest

import app as studio
import motion_assets


def sequence(**changes):
    return {'version': 1, 'kind': 'sequence', 'name': 'Greeting',
            'steps': [{'skill': 'wave', 'duration': 4, 'side': 'left'},
                      {'skill': 'bow', 'duration': 3}], **changes}


def test_sequence_upload_library_and_reopen_use_validated_data(tmp_path, monkeypatch):
    monkeypatch.setattr(motion_assets, 'DIRECTORY', tmp_path / 'library')
    client = studio.app.test_client()
    value = sequence(unknown='never execute this')
    value['steps'][0].update(duration=999, intensity=-4, execute_python='not retained')
    response = client.post('/api/motion/library', headers={'X-Studio-Client': 'moneypenny'},
                           data={'name': 'Saved greeting',
                                 'file': (io.BytesIO(json.dumps(value).encode()), 'greeting.sequence.json')})
    assert response.status_code == 200
    record = response.get_json()
    assert record['format'] == 'sequence'
    assert any(item['id'] == record['id'] for item in client.get('/api/motion/library').get_json()['motions'])
    saved = client.get(record['url']).get_json()
    assert saved == {'version': 1, 'kind': 'sequence', 'name': 'Saved greeting', 'steps': [
        {'skill': 'wave', 'duration': 20, 'intensity': .1, 'side': 'left'},
        {'skill': 'bow', 'duration': 3, 'intensity': .6, 'side': 'right'}]}


@pytest.mark.parametrize('value', [
    sequence(version=True), sequence(kind='script'), sequence(steps=[]),
    sequence(steps=[{'skill': 'wave'}] * 9),
    sequence(steps=[{'skill': 'custom', 'frames': []}]),
    sequence(steps=[{'skill': 'execute_python'}]),
    sequence(steps=[{'skill': 'wave', 'duration': True}]),
    sequence(steps=[{'skill': 'wave', 'duration': float('nan')}]),
])
def test_invalid_sequences_never_create_an_asset(tmp_path, monkeypatch, value):
    monkeypatch.setattr(motion_assets, 'DIRECTORY', tmp_path / 'library')
    with pytest.raises(ValueError):
        motion_assets.add('Bad', 'bad.sequence.json', json.dumps(value).encode())
    assert not motion_assets.DIRECTORY.exists()
