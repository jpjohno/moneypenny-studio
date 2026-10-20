"""Voice-route regression checks; no generated speech or real speaker playback."""
import asyncio
import io
from pathlib import Path
import threading
import wave

import httpx
import pytest

import cloud_ai
import jarvis_comm_broker as broker
import local_voice
import voice_profiles

TOKEN = "isolated-voice-route-review-test-token"
ROUTES = {
    "/v1/workspace/voice/audio": {"text": "A private test reply."},
    "/v1/workspace/voice/preview": {"profile": "moneypenny", "speed": 1.0},
    "/v1/workspace/voice/say": {"text": "A private test reply."},
}


def audio_fixture():
    result = io.BytesIO()
    with wave.open(result, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(24000)
        audio.writeframes(b"\x00\x00" * 240)
    return result.getvalue()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(broker, "HERE", tmp_path)
    monkeypatch.setattr(voice_profiles, "PATH", tmp_path / "preferences.json")
    async def cancel():
        pass
    monkeypatch.setattr(local_voice, "cancel_active", cancel)
    monkeypatch.setattr(cloud_ai, "enabled", lambda: True)
    def forbidden_player(*args, **kwargs):
        pytest.fail("This test must not launch a real speaker")
    monkeypatch.setattr(broker.subprocess, "Popen", forbidden_player)
    return broker.create_app(broker.Settings(token=TOKEN), task_path=tmp_path / "tasks.sqlite3")


def client(app, *, authenticated=True):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
        base_url="http://127.0.0.1:8766",
        headers={"Authorization": "Bearer " + TOKEN} if authenticated else {})


@pytest.mark.anyio
async def test_all_voice_routes_require_auth_and_reject_other_origins(isolated, monkeypatch):
    async def forbidden(*args, **kwargs):
        pytest.fail("Unauthorised requests must not synthesize speech")
    monkeypatch.setattr(cloud_ai, "speech", forbidden)
    async with client(isolated, authenticated=False) as request:
        for route, body in {**ROUTES, "/v1/workspace/voice/stop": {}}.items():
            assert (await request.post(route, json=body)).status_code == 401
    async with client(isolated) as request:
        for route, body in {**ROUTES, "/v1/workspace/voice/stop": {}}.items():
            result = await request.post(route, json=body, headers={"Origin": "https://untrusted.invalid"})
            assert result.status_code == 403


@pytest.mark.anyio
@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("error,status", [
    (local_voice.LocalVoiceUnavailable, 503),
    (local_voice.LocalVoiceBusy, 409),
    (local_voice.LocalVoiceCancelled, 409),
    (httpx.ReadTimeout, 503),
    (OSError, 503),
])
async def test_voice_failure_is_closed_without_another_voice(isolated, monkeypatch, route, error, status):
    calls = []
    async def fail(text, **kwargs):
        calls.append((text, kwargs))
        raise error("Private source text and diagnostic must never be returned")
    monkeypatch.setattr(cloud_ai, "speech", fail)
    async with client(isolated) as request:
        result = await request.post(route, json=ROUTES[route])
    assert result.status_code == status
    assert len(calls) == 1
    assert "Private source" not in result.text
    assert result.headers["cache-control"] == "no-store"


@pytest.mark.anyio
async def test_stop_during_legacy_synthesis_prevents_late_mac_playback(isolated, monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()
    async def pending(text, **kwargs):
        started.set()
        await release.wait()
        return audio_fixture()
    monkeypatch.setattr(cloud_ai, "speech", pending)
    async with client(isolated) as request:
        speech = asyncio.create_task(request.post("/v1/workspace/voice/say", json={"text": "A delayed reply."}))
        await asyncio.wait_for(started.wait(), 2)
        assert (await request.post("/v1/workspace/voice/stop", json={})).status_code == 204
        release.set()
        result = await asyncio.wait_for(speech, 2)
    assert result.status_code == 409
    assert not list((broker.HERE / ".runtime/voice-playback").glob("*.wav"))


class FakePlayer:
    def __init__(self, *, pending=False):
        self.returncode = None if pending else 0
        self.finished = threading.Event()
        self.terminated = False
        if not pending:
            self.finished.set()

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15
        self.finished.set()

    def kill(self):
        self.terminate()

    def wait(self, timeout=None):
        if not self.finished.wait(timeout):
            raise broker.subprocess.TimeoutExpired("isolated-player", timeout)
        return self.returncode


@pytest.mark.anyio
async def test_newer_legacy_say_cannot_be_replaced_by_older_synthesis(isolated, monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()
    players = []
    async def pending(text, **kwargs):
        if text == "Old reply.":
            started.set()
            await release.wait()
        return audio_fixture()
    def player(*args, **kwargs):
        result = FakePlayer()
        players.append(result)
        return result
    monkeypatch.setattr(cloud_ai, "speech", pending)
    monkeypatch.setattr(broker.subprocess, "Popen", player)
    async with client(isolated) as request:
        old = asyncio.create_task(request.post("/v1/workspace/voice/say", json={"text": "Old reply."}))
        await asyncio.wait_for(started.wait(), 2)
        assert (await request.post("/v1/workspace/voice/say", json={"text": "New reply."})).status_code == 204
        release.set()
        assert (await asyncio.wait_for(old, 2)).status_code == 409
        await asyncio.gather(*list(isolated.state.voice_cleanup_tasks))
    assert len(players) == 1


@pytest.mark.anyio
async def test_preview_startup_and_briefing_use_identical_selected_local_voice(isolated, monkeypatch):
    calls = []
    voice_profiles.save("moneypenny", 1.0, "gpt-4.1-mini")
    async def local(text, *, speed, voice):
        calls.append((text, speed, voice_profiles.current()["provider"], voice))
        return audio_fixture()
    def forbid_cloud_headers():
        pytest.fail("Moneypenny must not obtain cloud speech credentials")
    monkeypatch.setattr(local_voice, "speech", local)
    monkeypatch.setattr(cloud_ai, "headers", forbid_cloud_headers)
    monkeypatch.setattr(cloud_ai.usage_meter, "record", lambda *args, **kwargs: None)
    async with client(isolated) as request:
        for text in ("Hello James. Moneypenny here.", "Your briefing: two appointments today."):
            result = await request.post("/v1/workspace/voice/audio", json={"text": text})
            assert result.status_code == 200 and result.content == audio_fixture()
            assert result.headers["cache-control"] == "no-store"
        result = await request.post("/v1/workspace/voice/preview", json={"profile": "moneypenny", "speed": 1.0})
        assert result.status_code == 200 and result.content == audio_fixture()
    assert len(calls) == 3
    assert {row[1:] for row in calls} == {(1.0, "local-kokoro", "bf_emma")}


@pytest.mark.anyio
async def test_shutdown_stops_legacy_player_and_removes_private_audio(isolated, monkeypatch):
    players, paths = [], []
    async def synthesize(text, **kwargs):
        return audio_fixture()
    def player(argv, **kwargs):
        assert argv[0] == "/usr/bin/afplay"
        path = Path(argv[1])
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700
        assert path.read_bytes() == audio_fixture()
        paths.append(path)
        result = FakePlayer(pending=True)
        players.append(result)
        return result
    monkeypatch.setattr(cloud_ai, "speech", synthesize)
    monkeypatch.setattr(broker.subprocess, "Popen", player)
    async with isolated.router.lifespan_context(isolated):
        async with client(isolated) as request:
            assert (await request.post("/v1/workspace/voice/say", json={"text": "A fixture."})).status_code == 204
            assert players[0].poll() is None
    assert players[0].terminated
    assert isolated.state.say_process is None
    assert not any(path.exists() for path in paths)
    assert not isolated.state.voice_cleanup_tasks

@pytest.mark.anyio
async def test_explicit_offline_transcription_cannot_fall_through_to_cloud(isolated, monkeypatch):
    import local_speech
    monkeypatch.setattr(local_speech, 'transcribe', lambda pcm: 'offline fixture words')
    async def forbidden(*args, **kwargs):
        pytest.fail('Explicit local speech must never call the cloud')
    monkeypatch.setattr(cloud_ai, 'transcribe', forbidden)
    async with client(isolated) as request:
        result = await request.post('/v1/workspace/voice/transcribe?engine=local',content=b'\0\0'*1600,headers={'Content-Type':'application/octet-stream'})
        assert result.status_code == 200
        assert result.json() == {'text':'offline fixture words','engine':'vosk-local'}
        assert (await request.post('/v1/workspace/voice/transcribe?engine=unknown',content=b'\0\0',headers={'Content-Type':'application/octet-stream'})).status_code == 400

@pytest.mark.anyio
async def test_configured_transcription_retains_the_selected_provider(isolated, monkeypatch):
    async def synthetic(pcm):return 'configured fixture words'
    monkeypatch.setattr(cloud_ai, 'transcribe', synthetic)
    async with client(isolated) as request:
        result = await request.post('/v1/workspace/voice/transcribe',content=b'\0\0'*1600,headers={'Content-Type':'application/octet-stream'})
        assert result.json() == {'text':'configured fixture words','engine':'openai-transcribe'}
