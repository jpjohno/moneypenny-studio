"""Kokoro bf_emma, the same approved British voice used by JJRVIS."""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import shutil
import tempfile
import espeakng_loader
import numpy as np
import onnxruntime as ort
from kokoro_onnx import Kokoro
from kokoro_onnx.config import EspeakConfig
import soundfile as sf


def frame(value):
    sys.stdout.buffer.write(struct.pack(">I", len(value)) + value)
    sys.stdout.buffer.flush()


def main():
    models = Path(sys.argv[1])
    for name, digest in (
        ("kokoro-v1.0.onnx", "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a"),
        ("voices-v1.0.bin", "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"),
    ):
        if hashlib.sha256((models / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Voice model checksum mismatch")
    cached = Path.home() / ".cache/jjrvis-kokoro/espeak-ng-data"
    data = cached if (cached / "phontab").is_file() else Path(espeakng_loader.get_data_path())
    temporary = None
    if len(str(data).encode()) > 140:
        temporary = tempfile.TemporaryDirectory(prefix='mp-espeak-')
        short = Path(temporary.name) / 'data'
        shutil.copytree(data, short)
        data = short
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(models / "kokoro-v1.0.onnx"), sess_options=options, providers=["CPUExecutionProvider"])
    engine = Kokoro.from_session(session, str(models / "voices-v1.0.bin"), espeak_config=EspeakConfig(data_path=str(data)))
    frame(b"READY")
    while value := sys.stdin.buffer.readline(16001):
        if len(value) > 16000 or not value.endswith(b"\n"):
            raise ValueError("Invalid voice request")
        payload = json.loads(value)
        text, speed = payload["text"], payload["speed"]
        if not isinstance(text, str) or not 0 < len(text) <= 2400 or not .8 <= speed <= 1.5:
            raise ValueError("Invalid voice request")
        samples, rate = engine.create(text, voice="bf_emma", lang="en-gb", speed=speed)
        if rate != 24000 or not np.isfinite(samples).all():
            raise ValueError("Invalid speech")
        output = io.BytesIO()
        sf.write(output, samples, rate, format="WAV", subtype="PCM_16")
        frame(output.getvalue())


if __name__ == "__main__":
    main()
