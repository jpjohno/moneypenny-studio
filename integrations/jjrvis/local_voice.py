"""Fixed local British speech in a private, warm and cancellable process.

No text or audio is sent to another service. The private cache holds at most
thirty WAV files, named from the text and complete synthesis configuration.
"""
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import threading
import wave

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / ".runtime"
PYTHON = RUNTIME / "kokoro-env/bin/python"
WORKER = HERE / "local_voice_worker.py"
CACHE = RUNTIME / "local-voice-cache"
TIMEOUT_SECONDS = 120
MAX_CHARACTERS = 2400
MAX_CACHE_FILES = 30
MAX_AUDIO_BYTES = 24_000_044
ENGINE = {
    "engine": "kokoro-onnx", "engine_version": "0.6.1", "worker_version": 4,
    "model_sha256": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
    "voices_sha256": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
    "voice": "bf_emma", "language": "en-gb", "sample_rate": 24000,
    "threads": 4,
}
ALLOWED_VOICES = frozenset({'bf_emma', 'bm_george'})
_generation = threading.Lock()
_active = None
_worker = None
_worker_loop = None
_generation_done = None
_cancel_serial = 0


class LocalVoiceUnavailable(OSError):
    pass


class LocalVoiceBusy(LocalVoiceUnavailable):
    pass


class LocalVoiceCancelled(LocalVoiceUnavailable):
    pass


def available():
    return (PYTHON.is_file() and WORKER.is_file()
            and (RUNTIME / "kokoro-models/kokoro-v1.0.onnx").is_file()
            and (RUNTIME / "kokoro-models/voices-v1.0.bin").is_file())


def _validate_audio(value):
    if not 44 < len(value) <= MAX_AUDIO_BYTES:
        raise LocalVoiceUnavailable("The local voice returned invalid audio. Please retry.")
    try:
        with wave.open(io.BytesIO(value), "rb") as audio:
            if (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) != (1, 2, 24000):
                raise ValueError("Invalid WAV format")
            if audio.getnframes() < 1 or len(audio.readframes(audio.getnframes())) != audio.getnframes() * 2:
                raise ValueError("Incomplete WAV")
    except (wave.Error, EOFError, ValueError) as exc:
        raise LocalVoiceUnavailable("The local voice returned invalid audio. Please retry.") from exc
    return value


def _cached(path):
    try:
        if path.stat().st_size > MAX_AUDIO_BYTES:
            return None
        value = _validate_audio(path.read_bytes())
        os.utime(path, None)
        return value
    except (OSError, ValueError):
        return None


def _store(path, value):
    CACHE.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(CACHE, 0o700)
    fd, temporary = tempfile.mkstemp(prefix=".voice-", dir=CACHE)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(value)
        os.replace(temporary, path)
        for old in sorted(CACHE.glob("*.wav"), key=lambda item: item.stat().st_mtime, reverse=True)[MAX_CACHE_FILES:]:
            old.unlink(missing_ok=True)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


async def _terminate(process):
    if process is None or process.returncode is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=2)
    except asyncio.TimeoutError:
        try:
            process.kill()
        except ProcessLookupError:
            pass
        await process.wait()


async def cancel_active():
    """Stop an active render, retaining an idle warm model for the next reply."""
    global _cancel_serial
    _cancel_serial += 1
    process = _active
    done = _generation_done
    await _terminate(process)
    # A Stop acknowledgement means the old request released ownership too.
    # This prevents an immediately following click racing into a busy response.
    if done is not None and not done.done():
        await asyncio.shield(done)


async def shutdown():
    """Release the resident model when the broker itself exits."""
    global _worker, _worker_loop
    await cancel_active()
    process, _worker = _worker, None
    _worker_loop = None
    await _terminate(process)


async def _read_frame(process):
    size = struct.unpack(">I", await process.stdout.readexactly(4))[0]
    if not 0 < size <= MAX_AUDIO_BYTES:
        raise LocalVoiceUnavailable("The local voice returned invalid audio. Please retry.")
    return await process.stdout.readexactly(size)


async def _send_request(process, config):
    process.stdin.write(json.dumps(config, ensure_ascii=False).encode() + b"\n")
    await process.stdin.drain()
    return await _read_frame(process)


async def _get_worker(serial):
    """Caller owns _generation, so no second model can start concurrently."""
    global _active, _worker, _worker_loop
    loop = asyncio.get_running_loop()
    if _worker is not None and _worker.returncode is None and _worker_loop is loop:
        _active = _worker
        return _worker
    # A stopped or failed render is discarded; the next request gets a clean
    # protocol stream, never a late result from the cancelled request.
    previous, _worker = _worker, None
    await _terminate(previous)
    process = await asyncio.create_subprocess_exec(
        str(PYTHON), str(WORKER), "--persistent", stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL,
        env={"HOME": str(Path.home()), "PATH": "/usr/bin:/bin",
             "LANG": "en_GB.UTF-8", "PYTHONNOUSERSITE": "1"},
    )
    _worker, _worker_loop, _active = process, loop, process
    if serial != _cancel_serial:
        raise LocalVoiceCancelled("Voice preparation stopped.")
    if await _send_request(process, ENGINE) != b"READY":
        raise LocalVoiceUnavailable("The British voice could not start. Please retry.")
    if serial != _cancel_serial:
        raise LocalVoiceCancelled("Voice preparation stopped.")
    return process


async def warmup():
    """Load the selected local model ahead of a click, without playing audio.

    A busy voice is already warm or warming; startup must not interrupt it.
    """
    global _active, _worker, _worker_loop, _generation_done
    if not available():
        return False
    if not _generation.acquire(blocking=False):
        return False
    done = _generation_done = asyncio.get_running_loop().create_future()
    ready = False
    serial = _cancel_serial
    try:
        await asyncio.wait_for(_get_worker(serial), timeout=TIMEOUT_SECONDS)
        ready = serial == _cancel_serial
        return ready
    except (OSError, asyncio.IncompleteReadError, asyncio.TimeoutError):
        return False
    finally:
        process, _active = _active, None
        if not ready:
            if _worker is process:
                _worker, _worker_loop = None, None
            await _terminate(process)
        _generation.release()
        done.set_result(None)


async def speech(text, *, speed=1.0, voice='bf_emma'):
    global _active, _worker, _worker_loop, _generation_done
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_CHARACTERS:
        raise ValueError("Speech must contain between 1 and 2,400 characters.")
    if isinstance(speed, bool) or not isinstance(speed, (int, float)) or not .8 <= speed <= 1.5:
        raise ValueError("Voice speed must be between 0.8 and 1.5.")
    if voice not in ALLOWED_VOICES:
        raise ValueError("Choose an installed British assistant voice.")
    config = {**ENGINE, "voice": voice, "speed": float(speed), "text": text}
    digest = hashlib.sha256(json.dumps(config, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    cache_path = CACHE / (digest + ".wav")
    if cached := _cached(cache_path):
        return cached
    if not available():
        raise LocalVoiceUnavailable("The British voice is not installed on this Mac.")
    if not _generation.acquire(blocking=False):
        raise LocalVoiceBusy("The selected assistant is preparing another reply. Stop it or wait, then retry.")
    done = _generation_done = asyncio.get_running_loop().create_future()
    completed = False
    serial = _cancel_serial
    try:
        # Concurrent identical requests can reuse the first result once its
        # generation has finished; no second speaker is used on any failure.
        if cached := _cached(cache_path):
            return cached
        async def generate():
            process = await _get_worker(serial)
            return await _send_request(process, config)
        try:
            stdout = await asyncio.wait_for(generate(), timeout=TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            raise LocalVoiceUnavailable("The British voice took too long to prepare. Please try a shorter reply.") from exc
        except (OSError, asyncio.IncompleteReadError) as exc:
            if serial != _cancel_serial:
                raise LocalVoiceCancelled("Voice preparation stopped.") from exc
            raise LocalVoiceUnavailable("The British voice could not prepare this reply. Please retry.") from exc
        if serial != _cancel_serial:
            raise LocalVoiceCancelled("Voice preparation stopped.")
        if _active.returncode:
            raise LocalVoiceUnavailable("The British voice could not prepare this reply. Please retry.")
        value = _validate_audio(stdout)
        _store(cache_path, value)
        completed = True
        return value
    finally:
        process, _active = _active, None
        if not completed:
            if _worker is process:
                _worker, _worker_loop = None, None
            await _terminate(process)
        _generation.release()
        done.set_result(None)
