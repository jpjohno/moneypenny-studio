"""Private resident British voice; invoked only by local_voice.py's venv.

Requests are bounded JSON lines on stdin. Responses are length-prefixed bytes;
no listening socket, credentials, text logs or remote speech service is used.
"""
import hashlib
import io
import json
from pathlib import Path
import shutil
import struct
import sys


def validate_voice(payload):
    if payload["voice"] not in {"bf_emma", "bm_george"} or payload["language"] != "en-gb":
        raise ValueError("Unsupported local voice")


def load_engine(payload):
    validate_voice(payload)
    import espeakng_loader
    import onnxruntime as ort
    from kokoro_onnx import Kokoro
    from kokoro_onnx.config import EspeakConfig

    runtime = Path(__file__).resolve().parent / ".runtime"
    model = runtime / "kokoro-models/kokoro-v1.0.onnx"
    voices = runtime / "kokoro-models/voices-v1.0.bin"
    for path, checksum in ((model, payload["model_sha256"]), (voices, payload["voices_sha256"])):
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != checksum:
            raise ValueError("Local speech model checksum mismatch")
    # This short cache path avoids eSpeak NG's 160-byte POSIX data-path limit.
    espeak_data = Path.home() / ".cache/jjrvis-kokoro/espeak-ng-data"
    espeak_data.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not (espeak_data / "phontab").is_file():
        shutil.copytree(espeakng_loader.get_data_path(), espeak_data, dirs_exist_ok=True)
    options = ort.SessionOptions()
    threads = payload.get("threads", 4)
    if threads not in (2, 4):
        raise ValueError("Invalid local voice worker configuration")
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session = ort.InferenceSession(str(model), sess_options=options, providers=["CPUExecutionProvider"])
    return Kokoro.from_session(session, str(voices), espeak_config=EspeakConfig(data_path=str(espeak_data)))


def synthesize(engine, payload):
    validate_voice(payload)
    text, speed = payload["text"], payload["speed"]
    if (not isinstance(text, str) or not text.strip() or len(text) > 2400
            or isinstance(speed, bool) or not isinstance(speed, (int, float)) or not .8 <= speed <= 1.5):
        raise ValueError("Invalid local speech request")
    import numpy as np
    import soundfile as sf
    samples, sample_rate = engine.create(text, voice=payload["voice"], lang="en-gb", speed=speed)
    if sample_rate != 24000 or not samples.size or not np.isfinite(samples).all():
        raise ValueError("Invalid speech samples")
    output = io.BytesIO()
    sf.write(output, samples, sample_rate, format="WAV", subtype="PCM_16")
    value = output.getvalue()
    if not 44 < len(value) <= 24_000_044:
        raise ValueError("Invalid speech length")
    return value


def read_request():
    value = sys.stdin.buffer.readline(16001)
    if not value:
        return None
    if len(value) > 16000 or not value.endswith(b"\n"):
        raise ValueError("Invalid speech request length")
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("Invalid speech request")
    return payload


def write_frame(value):
    sys.stdout.buffer.write(struct.pack(">I", len(value)))
    sys.stdout.buffer.write(value)
    sys.stdout.buffer.flush()


def main():
    if sys.argv[1:] == ["--persistent"]:
        payload = read_request()
        if payload is None:
            return
        engine = load_engine(payload)
        # Exercise phonemisation and inference once during silent startup, so
        # the first real reply does not pay their one-off initialisation cost.
        synthesize(engine, {**payload, "text": "Ready.", "speed": 1.0})
        write_frame(b"READY")
        while (payload := read_request()) is not None:
            write_frame(synthesize(engine, payload))
    else:
        payload = json.loads(sys.stdin.buffer.read(16000))
        sys.stdout.buffer.write(synthesize(load_engine(payload), payload))


if __name__ == "__main__":
    main()
