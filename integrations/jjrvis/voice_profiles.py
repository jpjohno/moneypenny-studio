"""Shared assistant voice preference; never contains credentials."""
import json
import os
import tempfile
from pathlib import Path
PATH=Path(__file__).parent/'.runtime/voice-preference.json'
PROFILES={
 'english':{'name':'Jarvis','label':'Jarvis · London English male','voice':'cedar','style':'Use a distinctly natural London English male accent, with contemporary London vowels and relaxed conversational rhythm. Sound like Jarvis: calm, assured, highly capable, quick-witted and understated. Do not use an American accent, formal received pronunciation, or an exaggerated Cockney caricature.'},
 'moneypenny':{'name':'Moneypenny','label':'Moneypenny · natural English female','voice':'marin','style':'ACCENT FIRST: Speak as an adult English woman born and raised in London, England, using contemporary educated Southern British English throughout. Maintain a clearly English, non-rhotic London accent in every sentence. Use the Southern English long AH vowel in bath, ask, chance and afternoon; British rounded short O in lot; do not pronounce a final R in car, here or better unless followed by a vowel. Keep T crisp rather than an American D flap. Use English vowel shapes and falling British intonation, with no American twang, rhotic R, transatlantic blend or American vocal fry. Character: a confident, cheeky, jovial London woman with a noticeably sultry, flirtatious delivery. Use a warm lower register, a smiling voice, playful teasing emphasis and occasional little amused lifts, as though sharing a witty private joke. Let light double meanings land with a brief knowing pause. Sound like spontaneous conversation rather than a scripted voice-over. Use natural, varied pitch contours, small shifts in warmth and energy, relaxed sentence endings and brief pauses at thought boundaries. Let important words carry the emphasis; let connecting words flow lightly. Vary phrase lengths and rhythm instead of giving every sentence the same melody. Sound warmly playful, confident and quick-witted, with expressive conversational intonation. Keep flirtation non-explicit and responsive. Prioritise clear London English vowels over breathiness or exaggerated character acting. Avoid a presenter cadence, sing-song delivery, exaggerated theatricality, artificial laughs, added filler words, whispering or breathlessness. Preserve the English accent above all. For financial figures, client correspondence, distress or urgent matters, drop the flirtation and speak clearly and professionally. Do not imitate any particular actress.'},
 'american':{'name':'Moneypenny','label':'Coral · American alternative (cloud)','voice':'coral','style':'Use a natural American female voice. Sound bright, friendly, energetic and quick-witted with crisp diction.'},
}
# Keep speech direction short and consistent across greetings and factual replies.
PROFILES['moneypenny']['speech_instructions'] = (
    'Read the supplied words exactly, in one continuous performance. '
    'You are Moneypenny, an adult woman from London, England. '
    'Speak only in a natural contemporary Southern English British accent, non-rhotic, '
    'with British vowels throughout. Your voice is warm, low, lightly husky, '
    'playful and subtly flirtatious, with a knowing smile. '
    'Keep this same English voice when reading appointments, business messages, news and numbers. '
    'Be conversational and clear. Do not change accent or character during the reply.'
)
MODELS={'local-moneypenny':{'label':'MoneyPenny legacy answer model · on this Mac','input':0,'output':0},'gpt-4.1-mini':{'label':'GPT-4.1 mini · economical','input':.4,'output':1.6},'gpt-4.1':{'label':'GPT-4.1 · higher capability · 5× token cost','input':2,'output':8}}
# Explicit local models already verified in the host's Ollama catalogue.
for model in ('uncensored-3b:latest','sadiq-bd/llama3.2-3b-uncensored:latest','llama3.2:3b','dolphin-llama3:latest','llama3.2:latest'):
 MODELS['ollama:'+model]={'label':model+' · on this Mac','input':0,'output':0,'ollama_model':model}
# The fixed local voice was explicitly selected after the greeting preview.
# Existing Moneypenny preferences therefore follow the same approved voice.
PROFILES['moneypenny'].update({'provider':'local-kokoro','voice':'bf_emma','language':'en-GB','label':'Moneypenny · British voice on this Mac'})
PROFILES['english'].update({'provider':'local-kokoro','voice':'bm_george','language':'en-GB','label':'Jarvis · British male voice on this Mac'})
PROFILES['american'].update({'provider':'openai','language':'en-US'})

def selected():
 try:
  data=json.loads(PATH.read_text()); profile=data['profile']; speed=float(data.get('speed',1.3))
  if profile in PROFILES and .8<=speed<=1.5:return {'profile':profile,'speed':speed,'model':data.get('model') if data.get('model') in MODELS else 'gpt-4.1-mini'}
 except (OSError,ValueError,KeyError,TypeError):pass
 return {'profile':'moneypenny','speed':1.0,'model':'gpt-4.1-mini'}
def resolved_model(model=None):
 model=model or selected()['model']
 if model=='local-moneypenny':return 'MoneyPenny:latest'
 return MODELS.get(model,{}).get('ollama_model') or model
def public():
 preference=selected()
 return {**preference,'voice':{key:PROFILES[preference['profile']][key] for key in ('provider','voice','language')},'resolved_model':resolved_model(preference['model']),'models':[{'id':k,**v} for k,v in MODELS.items()],'choices':[{'id':k,'name':v['name'],'label':v['label']} for k,v in PROFILES.items()]}
def current():
 preference=selected()
 return {**PROFILES[preference['profile']],**preference}
def save(profile,speed,model=None):
 model=model or selected()["model"]
 if model not in MODELS:raise ValueError("Invalid answer model")
 if profile not in PROFILES or not .8<=speed<=1.5:raise ValueError('Invalid voice preference')
 PATH.parent.mkdir(parents=True,exist_ok=True)
 fd,name=tempfile.mkstemp(dir=PATH.parent,prefix='voice-')
 try:
  with os.fdopen(fd,'w') as f:json.dump({'profile':profile,'speed':speed,'model':model},f)
  os.replace(name,PATH)
 finally:
  if os.path.exists(name):os.unlink(name)
 return public()


def for_speech(profile=None, speed=None):
    """Resolve one explicit identity; never silently replace a missing voice."""
    preference = selected()
    profile = profile if profile is not None else preference['profile']
    speed = speed if speed is not None else preference['speed']
    if profile not in PROFILES or isinstance(speed, bool) or not isinstance(speed, (int, float)) or not .8 <= speed <= 1.5:
        raise ValueError('Invalid voice preference')
    return {**PROFILES[profile], 'profile': profile, 'speed': float(speed)}
