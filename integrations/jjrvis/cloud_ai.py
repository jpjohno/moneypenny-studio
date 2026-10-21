"""Explicitly configured OpenAI transport. Credentials never enter browser responses."""
import io
import json as json_module
import os
import wave
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pathlib import Path
import httpx
import voice_profiles
import usage_meter

KEY_PATH = Path.home()/'.config/jjrvis/openai.key'
# Ollama reloads a runner when its context allocation changes. Keep ordinary
# chat, planning, grounded answers and startup on one allocation; retain larger
# contexts explicitly requested by long correspondence reviews.
LOCAL_CONTEXT = 4096
_answer_selection = ContextVar('jjrvis_answer_selection', default=None)

def local_payload(payload, model):
    options = payload.get('options', {})
    return {**payload, 'model': model, 'keep_alive': '2h',
            'options': {**options, 'num_ctx': max(LOCAL_CONTEXT, options.get('num_ctx', LOCAL_CONTEXT))}}

def answer_preference():
    """One request keeps its chosen engine even if settings change mid-answer."""
    return _answer_selection.get() or voice_profiles.selected()

@asynccontextmanager
async def answer_selection():
    token = _answer_selection.set(dict(answer_preference()))
    try:
        yield
    finally:
        _answer_selection.reset(token)
def key():
    return os.environ.get('OPENAI_API_KEY') or KEY_PATH.read_text().strip()
def enabled():
    override = os.environ.get('JJRVIS_CLOUD_AI')
    if override is not None:
        return override == '1'
    return (KEY_PATH.parent/'cloud-enabled').is_file()
def headers():
    return {'Authorization': 'Bearer '+key()}
def selected_answer_model():
    """Return the engine the transport will actually call, not its UI alias."""
    return voice_profiles.resolved_model(answer_preference()['model'])
async def chat(client, url, *, json):
    chosen=answer_preference()['model']
    local_model=selected_answer_model() if chosen=='local-moneypenny' or chosen.startswith('ollama:') else None
    if local_model:
        response = await client.post(url, json=local_payload(json, local_model))
        if response.is_success:
            usage_meter.record('local answers', local_model)
        return response
    if not enabled():
        return await client.post(url, json=local_payload(json, json['model']))
    payload={'model':chosen,'messages':json['messages'],'max_tokens':json.get('options',{}).get('num_predict',1600),'temperature':0,'store':False}
    if isinstance(json.get('format'),dict):
        payload['response_format']={'type':'json_schema','json_schema':{'name':'jjrvis_result','schema':json['format'],'strict':True}}
    r=await client.post('https://api.openai.com/v1/chat/completions',headers=headers(),json=payload)
    r.raise_for_status()
    usage_meter.record('cloud answers', payload['model'], r.json().get('usage'))
    choice=r.json()['choices'][0]
    return httpx.Response(200,request=r.request,json={'done':True,'done_reason':choice['finish_reason'],'message':{'content':choice['message']['content']}})

async def chat_stream(client, url, *, json):
    """Stream Ollama content once; cloud transport retains final-only compatibility.

    This is a private transport stream. The caller extracts the answer field and
    validates the final schema before sending authoritative output to a browser.
    Closing/cancelling the iterator closes the upstream HTTP response as well.
    """
    chosen = answer_preference()['model']
    local = chosen == 'local-moneypenny' or chosen.startswith('ollama:') or not enabled()
    if not local:
        response = await chat(client, url, json=json)
        response.raise_for_status()
        payload = response.json()
        yield {'text': payload['message']['content'], 'done': payload.get('done', False),
               'done_reason': payload.get('done_reason')}
        return
    model = selected_answer_model() if chosen == 'local-moneypenny' or chosen.startswith('ollama:') else json['model']
    payload = {**local_payload(json, model), 'stream': True}
    size, completed = 0, False
    async with client.stream('POST', url, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.strip():
                continue
            if len(line) > 25000:
                raise ValueError('response_size')
            part = json_module.loads(line)
            if part.get('error'):
                # Provider diagnostics may contain paths or configuration.
                raise ValueError('Model streaming failed')
            text = part.get('message', {}).get('content', '')
            if not isinstance(text, str):
                raise ValueError('Invalid streamed content')
            size += len(text)
            if size > 20000:
                raise ValueError('response_size')
            completed = part.get('done') is True
            yield {'text': text, 'done': completed, 'done_reason': part.get('done_reason')}
            if completed:
                usage_meter.record('local answers', model)
                break
    if not completed:
        raise ValueError('Incomplete model answer')
async def transcribe(pcm):
    output=io.BytesIO()
    with wave.open(output,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(pcm)
    async with httpx.AsyncClient(timeout=25,trust_env=False) as client:
        r=await client.post('https://api.openai.com/v1/audio/transcriptions',headers=headers(),data={'model':'gpt-4o-mini-transcribe','language':'en'},files={'file':('speech.wav',output.getvalue(),'audio/wav')})
        r.raise_for_status()
        usage_meter.record('listening', 'gpt-4o-mini-transcribe', audio_seconds=len(pcm)/32000)
        return r.json()['text']
async def speech(text, profile=None):
    profile = dict(profile or voice_profiles.current())
    if profile.get('provider') == 'local-kokoro':
        import local_voice
        selected_voice = profile.get('voice', 'bf_emma')
        audio = await local_voice.speech(text, speed=profile.get('speed', 1.0), voice=selected_voice)
        with wave.open(io.BytesIO(audio), 'rb') as local_audio:
            duration = local_audio.getnframes() / local_audio.getframerate()
        usage_meter.record('local speech', 'Kokoro ' + selected_voice, audio_seconds=duration)
        return audio
    # Explicit cloud profiles retain one complete synthesis. There is never
    # an automatic provider or voice fallback after a local speech failure.
    instructions = profile.get('speech_instructions', profile['style'])
    async with httpx.AsyncClient(timeout=35, trust_env=False) as client:
        response = await client.post('https://api.openai.com/v1/audio/speech', headers=headers(), json={
            'model':'gpt-4o-mini-tts', 'voice':profile['voice'],
            'input':text, 'instructions':instructions,
            'speed':profile.get('speed',1.15), 'response_format':'pcm'})
        response.raise_for_status()
        pcm = response.content
        if not pcm or len(pcm) % 2:
            raise OSError('Invalid speech audio')
        output = io.BytesIO()
        with wave.open(output, 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(24000)
            audio.writeframes(pcm)
        usage_meter.record('speech', 'gpt-4o-mini-tts / '+profile['voice'], audio_seconds=len(pcm)/48000)
        return output.getvalue()
