"""Local Moneypenny Studio. Inference, speech, and dictation stay on this Mac."""
import io
import json
import math
import os
from pathlib import Path
import re
import time
import wave

from flask import Flask, Response, jsonify, render_template, request, send_file, send_from_directory, stream_with_context
import requests
from werkzeug.exceptions import HTTPException
from speech import Voice, voice_config
from listening import Listening
from motion import generate_plan, validate_plan, SKILLS
import reminders
import appearance_settings
import personas
import motion_assets
import threading

ROOT = Path(__file__).resolve().parent
OLLAMA = os.environ.get("MONEYPENNY_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
LOCAL_CHARACTER = ROOT / ".runtime/character-workshop/Moneypenny-Performance-Candidate-v6.glb"
SURFACE_CHARACTER = ROOT / ".runtime/character-workshop/Moneypenny-Performance-Candidate-v9.glb"
STYLED_CHARACTER = ROOT / ".runtime/character-workshop/Moneypenny-Style-v26.glb"
NATURAL_CHARACTER = ROOT / ".runtime/character-workshop/Moneypenny-Style-v36.glb"
REFRESHED_CHARACTER = ROOT / ".runtime/character-workshop/Moneypenny-Style-v30.glb"
FITTED_CHARACTER = ROOT / ".runtime/character-workshop/Moneypenny-Style-v27.glb"
FREE_SURFACE_CHARACTER = ROOT / ".runtime/character-workshop/Moneypenny-Free-Surface-Reviewed.glb"
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 26 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True
voice = Voice()
listening = Listening()


def valid_local_character(path):
    """Check a fixed local candidate's container header and browser size limit."""
    try:
        size = path.stat().st_size
        if not 24 <= size <= 80 * 1024 * 1024:
            return False
        with path.open("rb") as source:
            header = source.read(12)
        return (header[:4] == b"glTF" and int.from_bytes(header[4:8], "little") == 2
                and int.from_bytes(header[8:12], "little") == size)
    except OSError:
        return False


def local_character_path():
    """Prefer the reviewed surface revision, retaining the previous working rig."""
    return next((path for path in (NATURAL_CHARACTER, REFRESHED_CHARACTER, FITTED_CHARACTER, STYLED_CHARACTER, FREE_SURFACE_CHARACTER, SURFACE_CHARACTER, LOCAL_CHARACTER)
                 if valid_local_character(path)), None)


def local_character_ready():
    return local_character_path() is not None


@app.before_request
def local_only():
    # Loopback binding alone does not prevent malicious sites posting to localhost.
    if request.host.split(":")[0] not in {"127.0.0.1", "localhost"}:
        return jsonify(error="Open the studio using localhost or 127.0.0.1."), 403
    if request.method == "POST" or request.path.startswith('/api/'):
        origin = request.headers.get("Origin")
        if (origin and origin != request.host_url.rstrip("/")) or request.headers.get("Sec-Fetch-Site") == "cross-site":
            return jsonify(error="Cross-site requests are not allowed."), 403
    if request.method == "POST":
        if request.headers.get("X-Studio-Client") != "moneypenny":
            return jsonify(error="Use the studio to make this request."), 403


@app.after_request
def private_response(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' blob: data:; connect-src 'self' blob:; worker-src 'self' blob:; "
        "media-src 'self' blob:; object-src 'none'; "
        "frame-ancestors 'self' http://127.0.0.1:8766 http://localhost:8766; base-uri 'self'; form-action 'self'"
    )
    if request.path.startswith(("/api/", "/chat")):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
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
    if data.get('persona_id'):
        record=personas.resolve(text(data['persona_id'],'Persona identity',200))
        data={**data,'model':record['model'],'system':record['system']}
    model = text(data.get("model", "MoneyPenny:latest"), "Model", 150)
    system = text(data.get("system", "You are Moneypenny, a warm, witty British assistant."), "Personality", 6000, empty=True)
    history = data.get("history", [])
    if not isinstance(history, list) or len(history) > 40:
        raise ValueError("Conversation history is limited to 40 messages.")
    movement=data.get('avatar_motion',[])
    if not isinstance(movement,list) or len(movement)>8 or any(not isinstance(x,str) or x not in SKILLS for x in movement):raise ValueError('Invalid avatar movement status.')
    movement_note=(' The local avatar controller has queued: '+', '.join(movement)+'. You may acknowledge that queued avatar performance; do not claim it has finished.') if movement else ' No avatar movement was queued for this turn.'
    messages = [{"role": "system", "content": system + "\n\n" + (
        "Reply in conversational English. Keep replies concise unless detail is requested. "
        "Optionally begin with one short physical expression between asterisks, e.g. *smiles and nods*. "
        "Then speak naturally, without quotation marks, markdown, or role labels. "
        "You speak for a visible 3D avatar. Its body is animated by a separate local controller. "
        "Never claim to have sent messages, accessed files or performed real-world actions." + movement_note
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
        "num_ctx": 4096,
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


@app.get('/vendor/vad/<path:filename>')
def vad_assets(filename):
    return send_from_directory(ROOT/'node_modules/@ricky0123/vad-web/dist',filename)


@app.get('/vendor/onnx/<path:filename>')
def onnx_assets(filename):
    return send_from_directory(ROOT/'node_modules/onnxruntime-web/dist',filename)


@app.get('/api/appearance')
def appearance_read():
    return jsonify(appearance_settings.read())


@app.post('/api/appearance')
def appearance_save():
    return jsonify(appearance_settings.save(body()))


@app.get('/api/character/default')
def default_character():
    look=request.args.get('look','latest')
    if look not in {'latest','previous'}:return jsonify(error='Choose latest or previous'),400
    candidate = local_character_path() if look=='latest' else next((p for p in (REFRESHED_CHARACTER,FITTED_CHARACTER,STYLED_CHARACTER) if valid_local_character(p)),None)
    if candidate is None:
        return jsonify(error="The local performance character is unavailable."), 404
    return send_file(candidate, mimetype="model/gltf-binary", conditional=True)


@app.get("/api/status")
def status():
    models, error = [], None
    quick = request.args.get('quick') == '1'
    if not quick:
        try:
            response = requests.get(f"{OLLAMA}/api/tags", timeout=3)
            response.raise_for_status()
            models = [item["name"] for item in response.json().get("models", [])]
        except (requests.RequestException, ValueError, KeyError):
            error = "Ollama is unavailable. Start Ollama to chat."
    config = voice_config()
    character_path = local_character_path()
    candidate = character_path is not None
    return jsonify(app="moneypenny-studio", version="2.2.0", models=models, models_checked=not quick, ollama_error=error, voice_ready=voice.available(),
                   voice="Moneypenny · British English · bf_emma", voice_engine="Kokoro ONNX",
                   microphone_ready=listening.available() or bool(config.get("transcribe_python") and Path(config.get("transcribe_model", "__missing__")).is_dir()),
                   listening_engine='Whisper base.en' if listening.available() else 'Vosk',
                   avatar_ready=candidate or (ROOT / "static/avatars/mpfb.glb").is_file(),
                   character_candidate_ready=candidate,
                   character_revision="style-v36" if character_path == NATURAL_CHARACTER else "style-v30" if character_path == REFRESHED_CHARACTER else "style-v27" if character_path == FITTED_CHARACTER else "style-v26" if character_path == STYLED_CHARACTER else "free-surface-reviewed" if character_path == FREE_SURFACE_CHARACTER else "surface-v9" if character_path == SURFACE_CHARACTER else "performance-v6" if candidate else None,
                   character_source="local-performance-candidate" if candidate else "bundled-cc0-sample")


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


@app.get('/api/motion/library')
def list_motion_library():
    return jsonify(motions=motion_assets.library())


@app.post('/api/motion/library')
def add_motion_asset():
    uploaded=request.files.get('file')
    if not uploaded:raise ValueError('Choose an animation file.')
    return jsonify(motion_assets.add(request.form.get('name',''),uploaded.filename,uploaded.read(24*1024*1024+1)))


@app.get('/api/motion/assets/<identity>')
def motion_asset(identity):
    return send_from_directory(motion_assets.DIRECTORY,motion_assets.asset(identity))


@app.get('/api/personas')
def list_personas():
    return jsonify(personas.catalogue())


@app.post('/api/personas')
def save_persona():
    return jsonify(personas.save(body()))


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
    return jsonify(text=listening.transcribe(pcm))


@app.post('/api/listening/warm')
def warm_listening():
    threading.Thread(target=listening.warm,daemon=True).start()
    return jsonify(state='warming',engine='Whisper' if listening.available() else 'Vosk')


@app.post('/api/motion/plan')
def motion_plan():
    data=body()
    if 'plan' in data:return jsonify(validate_plan(data['plan']))
    return jsonify(generate_plan(text(data.get('prompt'),'Movement instruction',2000),
        text(data.get('persona',''),'Movement persona',3000,empty=True),text(data.get('model','MoneyPenny:latest'),'Model',150),OLLAMA))


@app.get('/api/reminders')
def list_reminders():
    return jsonify(reminders=reminders.pending(),now=time.time())


@app.post('/api/reminders')
def add_reminder():
    data=body()
    return jsonify(reminders.add(text(data.get('text'),'Follow-up',1000),number(data.get('delay'),'Delay',1,604800)))


@app.post('/api/reminders/<identity>/claim')
def claim_reminder(identity):
    return jsonify(claimed=reminders.claim(identity))


if __name__ == "__main__":
    import signal

    def shutdown(signum, frame):
        listening.close()
        voice.close()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print("Moneypenny Studio: http://127.0.0.1:8090", flush=True)
    app.run(host="127.0.0.1", port=int(os.environ.get("MONEYPENNY_PORT", "8090")), debug=False, threaded=True)
