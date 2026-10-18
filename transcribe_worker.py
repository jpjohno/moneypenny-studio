"""One bounded, local Vosk dictation. No recording is stored."""
import json
import sys
from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)
pcm = sys.stdin.buffer.read(960001)
if not pcm or len(pcm) > 960000 or len(pcm) % 2:
    raise ValueError("Invalid recording")
recognizer = KaldiRecognizer(Model(sys.argv[1]), 16000)
recognizer.AcceptWaveform(pcm)
print(json.dumps({"text": json.loads(recognizer.FinalResult()).get("text", "")}))
