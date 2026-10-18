"""Local Moneypenny Studio. Inference, speech, and dictation stay on this Mac."""
import io
import json
import math
import os
from pathlib import Path
import re
import time
import wave

from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context
import requests
from werkzeug.exceptions import HTTPException
from speech import Voice, transcribe, voice_config

ROOT = Path(__file__).resolve().parent
OLLAMA = os.environ.get("MONEYPENNY_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True
voice = Voice()


@app.before_request
def local_only():
    # Loopback binding alone does not prevent malicious sites posting to localhost.
    if request.host.split(":")[0] not in {"127.0.0.1", "localhost"}:
        return jsonify(error="Open the studio using localhost or 127.0.0.1."), 403
    if request.method == "POST":
        origin = request.headers.get("Origin")
        if (origin and origin != request.host_url.rstrip("/")) or request.headers.get("Sec-Fetch-Site") == "cross-site":
            return jsonify(error="Cross-site requests are not allowed."), 403
        if request.headers.get("X-Studio-Client") != "moneypenny":
            return jsonify(error="Use the studio to make this request."), 403


@app.after_request
def private_response(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' blob: data:; connect-src 'self' blob:; worker-src 'self' blob:; "
        "media-src 'self' blob:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
    )
    if request.path.startswith(("/api/", "/chat")):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(Exception)
def errors(error):
    if isinstance(error, HTTPException):
        return jsonify(error=error.description), error.code
    if isinstance(error, ValueError):
        return jsonify(error=str(error)), 400
    app.logger.error("Studio request failed: %s", type(error).__name__)
    return jsonify(error="The local service could not complete this request. Please retry."), 503


def body():
    value = request.get_json()
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object.")
    return value


def text(value, label, limit, empty=False):
    if not isinstance(value, str) or len(value) > limit or (not empty and not value.strip()):
        raise ValueError(f"{label} must contain {'0' if empty else '1'}–{limit} characters.")
    return value.strip()


def number(value, label, lower, upper, integer=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{label} must be between {lower} and {upper}.")
    if integer and int(value) != value:
        raise ValueError(f"{label} must be a whole number.")
    return int(value) if integer else float(value)


def chat_payload(data):
    prompt = text(data.get("prompt"), "Message", 4000)
    model = text(data.get("model", "MoneyPenny:latest"), "Model", 150)
    system = text(data.get("system", "You are Moneypenny, a warm, witty British assistant."), "Personality", 6000, empty=True)
    history = data.get("history", [])
    if not isinstance(history, list) or len(history) > 40:
        raise ValueError("Conversation history is limited to 40 messages.")
    messages = [{"role": "system", "content": system + "\n\n" + (
        "Reply in conversational English. Keep replies concise unless detail is requested. "
        "Optionally begin with one short physical expression between asterisks, e.g. *smiles and nods*. "
        "Then speak naturally, without quotation marks, markdown, or role labels. "
        "Never claim to have used tools, sent a message, accessed files or completed an action: this studio only chats."
    )}]
    total = 0
    for item in history:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            raise ValueError("Invalid conversation history.")
        content = text(item.get("content"), "Previous message", 8000)
        total += len(content)
        if total > 32000:
            raise ValueError("Conversation history is too long. Start a new conversation.")
        messages.append({"role": item["role"], "content": content})
    messages.append({"role": "user", "content": prompt})
    return {"model": model, "messages": messages, "stream": True, "keep_alive": "10m", "options": {
        "temperature": number(data.get("temperature", .7), "Creativity", .1, 1.5),
        "num_predict": number(data.get("max_tokens", 256), "Reply length", 64, 1024, integer=True),
        "num_ctx": 8192,
    }}


def parse_reply(raw):
    actions = " ".join(re.findall(r"\*([^*\n]+)\*", raw))[:300]
    dialogue = re.sub(r"\*[^*]*\*", "", raw).strip().strip('"“”')
    if not dialogue:
        raise ValueError("The model returned no spoken reply. Try a shorter message or another model.")
    lower = actions.lower()
    mood = "happy" if re.search(r"smil|laugh|grin|wink|chuckl", lower) else "neutral"
    if any(word in lower for word in ("sad", "frown", "concern")):
        mood = "sad"
    gesture = next((name for pattern, name in (
        (r"shrug", "shrug"), (r"wave|greet", "handup"), (r"thumb", "thumbup"),
        (r"point|index", "index"), (r"explain|palm|gesture", "side"), (r"\bok\b", "ok")
    ) if re.search(pattern, lower)), None)
    return dict(dialogue=dialogue, actions=actions, mood=mood, gesture=gesture)


def reply_events(payload):
    started = time.monotonic()
    try:
        with requests.post(f"{OLLAMA}/api/chat", json=payload, stream=True, timeout=(5, 120)) as upstream:
            upstream.raise_for_status()
            raw = ""
            completed = False
            for line in upstream.iter_lines(chunk_size=1):
                if not line:
                    continue
                item = json.loads(line)
                if item.get("error"):
                    raise ValueError("Ollama could not generate this reply. Check the selected model.")
                token = item.get("message", {}).get("content", "")
                raw += token
                if len(raw) > 16000:
                    raise ValueError("The model reply exceeded the studio's limit.")
                if token:
                    yield {"type": "delta", "text": token}
                if item.get("done"):
                    completed = True
                    yield {"type": "done", **parse_reply(raw), "elapsed": round(time.monotonic() - started, 2)}
                    break
            if not completed:
                raise ValueError("Ollama disconnected before completing the reply. Please retry.")
    except requests.RequestException:
        yield {"type": "error", "error": "Cannot reach the selected Ollama model. Make sure Ollama is running and the model is installed."}
    except (ValueError, KeyError, TypeError) as error:
        yield {"type": "error", "error": str(error) if isinstance(error, ValueError) and not isinstance(error, json.JSONDecodeError) else "Ollama returned an invalid response."}


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/vendor/three/<path:filename>")
def three(filename):
    return send_from_directory(ROOT / "node_modules/three", filename)


@app.get("/api/status")
def status():
    models, error = [], None
    try:
        response = requests.get(f"{OLLAMA}/api/tags", timeout=3)
        response.raise_for_status()
        models = [item["name"] for item in response.json().get("models", [])]
    except (requests.RequestException, ValueError, KeyError):
        error = "Ollama is unavailable. Start Ollama to chat."
    config = voice_config()
    return jsonify(app="moneypenny-studio", version="2.0.0", models=models, ollama_error=error, voice_ready=voice.available(),
                   voice="Moneypenny · British English · bf_emma", voice_engine="Kokoro ONNX",
                   microphone_ready=bool(config.get("transcribe_python") and Path(config.get("transcribe_model", "__missing__")).is_dir()),
                   avatar_ready=(ROOT / "static/avatars/mpfb.glb").is_file())


@app.post("/api/chat/stream")
def chat_stream():
    payload = chat_payload(body())
    return Response(stream_with_context((json.dumps(event) + "\n" for event in reply_events(payload))), mimetype="application/x-ndjson")


@app.post("/chat")
def chat():
    for event in reply_events(chat_payload(body())):
        if event["type"] == "done":
            return jsonify(event)
        if event["type"] == "error":
            return jsonify(error=event["error"]), 503
    return jsonify(error="No reply was received."), 503


@app.post("/api/speech")
def speech():
    data = body()
    spoken = text(data.get("text"), "Speech", 2400)
    speed = number(data.get("speed", 1), "Voice speed", .8, 1.5)
    owner = text(data.get("owner"), "Session", 100)
    return Response(voice.speak(spoken, speed, owner), mimetype="audio/wav", headers={"X-Studio-Voice": "bf_emma"})


@app.post("/api/speech/stop")
def stop_speech():
    voice.cancel(text(body().get("owner"), "Session", 100))
    return "", 204


@app.post("/api/transcribe")
def microphone():
    value = request.get_data()
    if not 44 < len(value) <= 960044:
        raise ValueError("Recording must be no longer than 30 seconds.")
    try:
        with wave.open(io.BytesIO(value), "rb") as recording:
            if (recording.getnchannels(), recording.getsampwidth(), recording.getframerate()) != (1, 2, 16000):
                raise ValueError("Expected 16 kHz mono WAV audio.")
            pcm = recording.readframes(recording.getnframes())
    except (wave.Error, EOFError):
        raise ValueError("Invalid microphone recording.")
    return jsonify(text=transcribe(pcm))


if __name__ == "__main__":
    print("Moneypenny Studio: http://127.0.0.1:8090", flush=True)
    app.run(host="127.0.0.1", port=int(os.environ.get("MONEYPENNY_PORT", "8090")), debug=False, threaded=True)
