import asyncio
import io
import json
import struct
import wave
import pytest

import cloud_ai
import local_voice as voice
import voice_profiles


def wav():
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(b"\x01\x00" * 240)
    return buffer.getvalue()


class Process:
    def __init__(self, *, pending=False, returncode=0):
        self.returncode = None
        self.result = returncode
        self.pending = pending
        self.stopped = asyncio.Event()
        self.started = asyncio.Event()
        self.payload = None
        self.terminated = False
        self.stdout = asyncio.StreamReader()
        self.stdin = self
        self.requests = []

    def write(self, payload):
        self.payload = json.loads(payload)
        self.requests.append(self.payload)
        if "text" not in self.payload:
            self._frame(b"READY")
            return
        self.started.set()
        if self.result:
            self.returncode = self.result
            self.stdout.feed_eof()
        elif not self.pending:
            self._frame(wav())

    async def drain(self):
        return

    def _frame(self, value):
        self.stdout.feed_data(struct.pack(">I", len(value)) + value)

    def terminate(self):
        self.terminated = True
        self.returncode = -15
        self.stopped.set()
        self.stdout.feed_eof()

    def kill(self):
        self.terminate()

    async def wait(self):
        if self.returncode is None:
            await self.stopped.wait()
        return self.returncode


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(voice, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(voice, "available", lambda: True)
    monkeypatch.setattr(voice, "_active", None)
    monkeypatch.setattr(voice, "_worker", None)
    monkeypatch.setattr(voice, "_worker_loop", None)
    monkeypatch.setattr(voice, "_generation_done", None)
    monkeypatch.setattr(voice, "_cancel_serial", 0)


@pytest.mark.anyio
async def test_fixed_voice_and_private_cache(monkeypatch):
    calls = []
    async def spawn(*args, **kwargs):
        process = Process()
        calls.append((process, args, kwargs))
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    first = await voice.speech("Hello James.", speed=1.0)
    assert first == await voice.speech("Hello James.", speed=1.0)
    assert len(calls) == 1
    assert calls[0][0].payload["voice"] == "bf_emma"
    assert calls[0][0].payload["language"] == "en-gb"
    assert "OPENAI_API_KEY" not in calls[0][2]["env"]
    assert "Hello" not in calls[0][1]
    paths = list(voice.CACHE.glob("*.wav"))
    assert len(paths) == 1 and "Hello" not in paths[0].name
    assert paths[0].stat().st_mode & 0o777 == 0o600
    assert voice.CACHE.stat().st_mode & 0o777 == 0o700
    await voice.speech("Hello James.", speed=1.1)
    assert len(calls) == 1
    assert len(calls[0][0].requests) == 3  # one model load, two renders
    assert not calls[0][0].terminated
    await voice.shutdown()
    assert calls[0][0].terminated


@pytest.mark.anyio
async def test_only_one_generation_and_explicit_stop(monkeypatch):
    process = Process(pending=True)
    async def spawn(*args, **kwargs):
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    task = asyncio.create_task(voice.speech("First reply."))
    await process.started.wait()
    with pytest.raises(voice.LocalVoiceBusy, match="another reply"):
        await voice.speech("Second reply.")
    await voice.cancel_active()
    with pytest.raises(voice.LocalVoiceCancelled):
        await task
    assert process.terminated and not voice._generation.locked()
    assert not list(voice.CACHE.glob("*.wav"))


@pytest.mark.anyio
async def test_task_cancellation_terminates_child(monkeypatch):
    process = Process(pending=True)
    async def spawn(*args, **kwargs):
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    task = asyncio.create_task(voice.speech("A reply."))
    await process.started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert process.terminated and not voice._generation.locked()


@pytest.mark.anyio
async def test_deadline_terminates_child(monkeypatch):
    process = Process(pending=True)
    async def spawn(*args, **kwargs):
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    monkeypatch.setattr(voice, "TIMEOUT_SECONDS", 0.01)
    with pytest.raises(voice.LocalVoiceUnavailable, match="too long"):
        await voice.speech("A reply.")
    assert process.terminated and not voice._generation.locked()


@pytest.mark.anyio
async def test_idle_stop_keeps_warm_model_and_shutdown_releases_it(monkeypatch):
    calls = []
    async def spawn(*args, **kwargs):
        process = Process()
        calls.append(process)
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    assert await voice.warmup()
    assert len(calls[0].requests) == 1  # silent preloading, no utterance
    await voice.cancel_active()
    assert not calls[0].terminated
    assert await voice.speech("A new reply.") == wav()
    await voice.cancel_active()
    assert await voice.speech("Another reply.") == wav()
    assert len(calls) == 1
    await voice.shutdown()
    assert calls[0].terminated and voice._worker is None


@pytest.mark.anyio
async def test_stop_acknowledges_release_and_next_reply_starts_cleanly(monkeypatch):
    calls = []
    async def spawn(*args, **kwargs):
        process = Process(pending=not calls)
        calls.append(process)
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    task = asyncio.create_task(voice.speech("Interrupted reply."))
    while not calls:
        await asyncio.sleep(0)
    await calls[0].started.wait()
    assert not await voice.warmup()
    await voice.cancel_active()
    assert not voice._generation.locked()
    assert await voice.speech("New reply.") == wav()
    with pytest.raises(voice.LocalVoiceCancelled):
        await task
    assert len(calls) == 2 and calls[0].terminated
    await voice.shutdown()


@pytest.mark.anyio
async def test_stop_during_model_spawn_cannot_start_late_speech(monkeypatch):
    process = Process()
    spawning, proceed = asyncio.Event(), asyncio.Event()
    async def spawn(*args, **kwargs):
        spawning.set()
        await proceed.wait()
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    task = asyncio.create_task(voice.speech("A cancelled greeting."))
    await spawning.wait()
    stop = asyncio.create_task(voice.cancel_active())
    await asyncio.sleep(0)
    assert not stop.done()
    proceed.set()
    await stop
    with pytest.raises(voice.LocalVoiceCancelled):
        await task
    assert process.terminated and not process.requests
    assert not voice._generation.locked()


@pytest.mark.anyio
async def test_invalid_protocol_is_discarded_without_caching(monkeypatch):
    class InvalidProcess(Process):
        def _frame(self, value):
            if value == b"READY":
                super()._frame(value)
            else:
                self.stdout.feed_data(struct.pack(">I", voice.MAX_AUDIO_BYTES + 1))
    process = InvalidProcess()
    async def spawn(*args, **kwargs):
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(voice.LocalVoiceUnavailable):
        await voice.speech("A reply with an invalid audio frame.")
    assert process.terminated and voice._worker is None
    assert not list(voice.CACHE.glob("*.wav"))


@pytest.mark.anyio
async def test_worker_failure_releases_lock(monkeypatch):
    process = Process(returncode=1)
    async def spawn(*args, **kwargs):
        return process
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(voice.LocalVoiceUnavailable, match="could not prepare"):
        await voice.speech("A failed reply.")
    assert voice._worker is None and not voice._generation.locked()


@pytest.mark.anyio
async def test_failure_never_calls_cloud(monkeypatch):
    async def fail(*args, **kwargs):
        raise voice.LocalVoiceUnavailable("Local voice unavailable")
    def forbid(*args, **kwargs):
        pytest.fail("A failed local voice must never call a cloud provider")
    monkeypatch.setattr(voice, "speech", fail)
    monkeypatch.setattr(cloud_ai.httpx, "AsyncClient", forbid)
    with pytest.raises(voice.LocalVoiceUnavailable):
        await cloud_ai.speech("Hello", profile={"provider": "local-kokoro", "speed": 1.0})


@pytest.mark.anyio
async def test_saved_moneypenny_routes_every_passage_to_local(monkeypatch):
    calls = []
    async def synthesize(text, *, speed, voice):
        calls.append((text, speed, voice))
        return wav()
    def forbid(*args, **kwargs):
        pytest.fail("Moneypenny must not call cloud speech")
    monkeypatch.setattr(voice, "speech", synthesize)
    monkeypatch.setattr(voice_profiles, "current", lambda: {**voice_profiles.PROFILES['moneypenny'], 'speed': 1.0})
    monkeypatch.setattr(cloud_ai.httpx, "AsyncClient", forbid)
    monkeypatch.setattr(cloud_ai.usage_meter, 'record', lambda *args, **kwargs: None)
    for text in ("Hello James.", "Your daily briefing. " * 100):
        assert await cloud_ai.speech(text) == wav()
        assert calls[-1] == (text, 1.0, 'bf_emma')


@pytest.mark.anyio
async def test_male_and_female_voices_share_engine_but_never_share_cached_audio(monkeypatch):
    processes = []
    async def spawn(*args, **kwargs):
        process = Process()
        processes.append(process)
        return process
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    await voice.speech('Ready James.', voice='bf_emma')
    await voice.speech('Ready James.', voice='bm_george')
    await voice.speech('Ready James.', voice='bm_george')
    assert len(processes) == 1, 'Both voices use the one installed Kokoro engine'
    spoken = [row for row in processes[0].requests if 'text' in row]
    assert [row['voice'] for row in spoken] == ['bf_emma', 'bm_george']
    assert len(list(voice.CACHE.glob('*.wav'))) == 2, 'A male request cannot reuse the female voice cache entry'


@pytest.mark.anyio
async def test_jarvis_voice_is_local_and_does_not_read_cloud_credentials(monkeypatch):
    calls = []
    async def synthesize(text, *, speed, voice):
        calls.append((text, speed, voice))
        return wav()
    def forbid(*args, **kwargs):
        pytest.fail('Jarvis local speech must not contact a paid cloud service')
    monkeypatch.setattr(voice, 'speech', synthesize)
    monkeypatch.setattr(cloud_ai.httpx, 'AsyncClient', forbid)
    monkeypatch.setattr(cloud_ai, 'headers', forbid)
    monkeypatch.setattr(cloud_ai.usage_meter, 'record', lambda *args, **kwargs: None)
    await cloud_ai.speech('Good evening James.', profile={**voice_profiles.PROFILES['english'], 'speed': 1.0})
    assert calls == [('Good evening James.', 1.0, 'bm_george')]


@pytest.mark.anyio
async def test_unknown_voice_cannot_start_a_worker(monkeypatch):
    async def forbid(*args, **kwargs):
        pytest.fail('An unsupported voice must be rejected before starting any process')
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', forbid)
    with pytest.raises(ValueError, match='British assistant voice'):
        await voice.speech('Hello.', voice='unknown')


@pytest.mark.anyio
async def test_too_long_input_rejected_before_spawn(monkeypatch):
    async def forbid(*args, **kwargs):
        pytest.fail("Input must be validated before the worker starts")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbid)
    for text in ("", " ", "x" * 2401):
        with pytest.raises(ValueError):
            await voice.speech(text)


def test_cache_keeps_at_most_thirty_private_audio_files():
    for index in range(35):
        voice._store(voice.CACHE / (str(index) + ".wav"), wav())
    assert len(list(voice.CACHE.glob("*.wav"))) == 30
