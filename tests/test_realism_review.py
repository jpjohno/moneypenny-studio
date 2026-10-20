"""The private review serves fixed derived assets, never source projects."""
import json
import struct

import pytest

import app as studio


@pytest.fixture
def review(monkeypatch, tmp_path):
    monkeypatch.setattr(studio, 'REVIEW_ROOT', tmp_path)
    studio.app.config.update(TESTING=True)
    return studio.app.test_client(), tmp_path


def glb():
    return b'glTF' + struct.pack('<II', 2, 24) + b' ' * 12


def test_review_page_is_reachable_from_studio(review):
    client, _ = review
    assert b'href="/realism"' in client.get('/').data
    page = client.get('/realism')
    assert page.status_code == 200
    assert b'Recorded 4D' in page.data
    assert b'recorded performance' in page.data


def test_missing_assets_report_unavailable_without_exposing_paths(review):
    client, _ = review
    for path in ('scan.glb', '4d/manifest.json', '4d/frames/frame0000.glb'):
        result = client.get('/api/review-assets/' + path)
        assert result.status_code == 404
        assert b'.runtime' not in result.data


def test_only_fixed_scan_and_valid_frame_names_are_served(review):
    client, root = review
    scan = root / 'renderpeople-claudia/Claudia-private-talkinghead-prototype.glb'
    scan.parent.mkdir()
    scan.write_bytes(glb())
    frames = root / 'renderpeople-4d/browser-review/frames'
    frames.mkdir(parents=True)
    (frames / 'frame0000.glb').write_bytes(glb())
    (frames.parent / 'manifest.json').write_text(json.dumps({'fps': 15, 'frames': ['frames/frame0000.glb']}))
    for path in ('scan.glb', '4d/frames/frame0000.glb'):
        response = client.get('/api/review-assets/' + path)
        assert response.status_code == 200
        assert response.mimetype == 'model/gltf-binary'
        assert response.data == glb()
        assert response.headers['Cache-Control'] == 'no-store'
    assert client.get('/api/review-assets/4d/manifest.json').json['fps'] == 15
    for filename in ('source.blend', 'frame0000.fbx', 'frame0.glb', '..%2Fmanifest.json', '%2E%2E%2F%2E%2E%2Fsource.blend'):
        assert client.get('/api/review-assets/4d/frames/' + filename).status_code == 404
    scan.write_bytes(b'not-a-character')
    assert client.get('/api/review-assets/scan.glb').status_code == 404


def test_quality_is_allowlisted_and_selects_a_separate_private_sequence(review):
    client, root = review
    path = root / 'renderpeople-4d/browser-review-detail'
    (path / 'frames').mkdir(parents=True)
    (path / 'manifest.json').write_text(json.dumps({'fps': 15, 'textureSize': 1024, 'frames': ['frames/frame0000.glb']}))
    (path / 'frames/frame0000.glb').write_bytes(glb())
    assert client.get('/api/review-assets/4d/detail/manifest.json').json['textureSize'] == 1024
    assert client.get('/api/review-assets/4d/detail/frames/frame0000.glb').data == glb()
    assert client.get('/api/review-assets/4d/manifest.json').status_code == 404
    for quality in ('source', 'browser-review-detail', 'tex_2k'):
        assert client.get(f'/api/review-assets/4d/{quality}/manifest.json').status_code == 400
        assert client.get(f'/api/review-assets/4d/{quality}/frames/frame0000.glb').status_code == 400


@pytest.mark.parametrize('path', ['scan.glb', '4d/manifest.json', '4d/frames/frame0000.glb', '4d/detail/manifest.json', '4d/detail/frames/frame0000.glb'])
@pytest.mark.parametrize('headers', [
    {'Host': 'external.example:8090'},
    {'Origin': 'https://external.example'},
    {'Sec-Fetch-Site': 'cross-site'},
    {'Origin': 'http://127.0.0.1:8766', 'Sec-Fetch-Site': 'same-site'},
])
def test_private_review_cannot_be_read_from_other_websites(review, path, headers):
    client, _ = review
    response = client.get('/api/review-assets/' + path, headers=headers)
    assert response.status_code == 403
    assert response.headers.get('Access-Control-Allow-Origin') is None
    assert response.headers['Cross-Origin-Resource-Policy'] == 'same-origin'
