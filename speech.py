"""Own resident voice process; shares model files, never a running broker."""
import atexit
from collections import deque
import io
import json
from pathlib import Path
import select
import struct
import subprocess
import threading
import time
import wave

ROOT = Path(__file__).resolve().parent


def voice_config():
    try:
        return json.loads((ROOT / ".runtime/machine.json").read_text())
    except (OSError, ValueError):
        return {}


class Voice:
    def __init__(self):
        self.process = None
        self.owner = None
        self.lock = threading.Lock()
        self.state = threading.Lock()
        self.cancelled = deque(maxlen=1000)
        atexit.register(self.close)

    def available(self):
        config = voice_config()
        return bool(config.get("voice_python") and Path(config["voice_python"]).is_file()
                    and (Path(config.get("voice_models", "__missing__")) / "kokoro-v1.0.onnx").is_file()
                    and (Path(config.get("voice_models", "__missing__")) / "voices-v1.0.bin").is_file())

    def close(self):
        with self.state:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
            self.process = None

    def cancel(self, owner):
        active = False
        with self.state:
            self.cancelled.append(owner)
            if self.owner == owner and self.process and self.process.poll() is None:
                self.process.terminate()
                active = True
        if active and self.lock.acquire(timeout=3):
            self.lock.release()

    def _frame(self, process):
        deadline = time.monotonic() + 120

        def read_exact(size):
            result = bytearray()
            while len(result) < size:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
                    raise OSError("Speech timed out.")
                block = process.stdout.read(min(size - len(result), 65536))
                if not block:
                    raise OSError("Speech stopped.")
                result.extend(block)
            return bytes(result)

        size = struct.unpack(">I", read_exact(4))[0]
        if not 0 < size <= 24_000_044:
            raise OSError("Invalid speech frame.")
        return read_exact(size)

    def speak(self, text, speed, owner):
        if not self.available():
            raise ValueError("Set up the free local voice first. See the README's voice setup instructions.")
        if not self.lock.acquire(blocking=False):
            raise ValueError("The local voice is finishing another request. Please retry in a moment.")
        try:
            config = voice_config()
            with self.state:
                if owner in self.cancelled:
                    raise ValueError("This voice request was cancelled.")
                self.owner = owner
                if self.process is None or self.process.poll() is not None:
                    self.process = subprocess.Popen(
                        [config["voice_python"], str(ROOT / "speech_worker.py"), config["voice_models"]],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0, cwd=ROOT / '.runtime',
                    )
                    fresh = True
                else:
                    fresh = False
                process = self.process
            if fresh and self._frame(process) != b"READY":
                raise OSError("The local voice could not start.")
            process.stdin.write((json.dumps({"text": text, "speed": speed}) + "\n").encode())
            process.stdin.flush()
            audio = self._frame(process)
            with wave.open(io.BytesIO(audio), "rb") as recording:
                if (recording.getnchannels(), recording.getsampwidth(), recording.getframerate()) != (1, 2, 24000):
                    raise OSError("Invalid speech audio.")
                if len(recording.readframes(recording.getnframes())) != recording.getnframes() * 2:
                    raise OSError("Incomplete speech audio.")
            return audio
        except (OSError, ValueError, wave.Error, struct.error):
            self.close()
            raise ValueError("Local speech stopped or is unavailable. Please retry.")
        finally:
            with self.state:
                self.owner = None
            self.lock.release()


def transcribe(pcm):
    config = voice_config()
    if not config.get("transcribe_python") or not config.get("transcribe_model"):
        raise ValueError("Set up local microphone transcription first. See the README.")
    if not pcm or len(pcm) % 2 or len(pcm) > 960000:
        raise ValueError("Invalid recording; use at most 30 seconds.")
    result = subprocess.run(
        [config["transcribe_python"], str(ROOT / "transcribe_worker.py"), config["transcribe_model"]],
        input=pcm, capture_output=True, timeout=40,
    )
    if result.returncode:
        raise ValueError("The local microphone engine could not transcribe this recording.")
    return json.loads(result.stdout)["text"]
