"""Bounded, text-free viseme timing carried beside the original PCM in WAV.

Kokoro already predicts these phoneme durations during normal synthesis. This
module adds no inference, socket or dependency. Standard WAV readers ignore the
optional MPVS chunk and continue to receive exactly the same audio samples.
"""
import json
import math
import struct
import unicodedata

GROUPS = {
    'viseme_PP': 'pbm', 'viseme_FF': 'fv', 'viseme_TH': 'θð',
    'viseme_DD': 'td', 'viseme_kk': 'kɡgŋxɣ', 'viseme_CH': 'ʃʒʧʤcç',
    'viseme_SS': 'sz', 'viseme_nn': 'nlɫɲ', 'viseme_RR': 'rɹɾɻʁ',
    'viseme_aa': 'aɑɐɒæʌəɚhɦ', 'viseme_E': 'eɛɜɝɞ',
    'viseme_I': 'iɪɨɘjy', 'viseme_O': 'oɔøœɶɤ', 'viseme_U': 'uʊɯʉw',
    'viseme_sil': ' .,!?;:—–-\n\t',
}
PHONEMES = {character:viseme for viseme,characters in GROUPS.items() for character in characters}
MAX_CUES = 8192
MAX_BYTES = 512 * 1024


def viseme_timing(timings, duration):
    """Translate English IPA token spans, preserving predicted sample timing."""
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or not 0 < duration <= 600:
        return None
    cues=[]
    for item in timings or ():
        phoneme=getattr(item,'phoneme',None)
        start,end=getattr(item,'start',None),getattr(item,'end',None)
        if (not isinstance(phoneme,str) or len(phoneme)!=1
                or isinstance(start,bool) or isinstance(end,bool)
                or not isinstance(start,(int,float)) or not isinstance(end,(int,float))
                or not math.isfinite(start) or not math.isfinite(end)
                or start < -0.001 or end < start or end > duration+0.05):
            return None
        start,end=max(0,start),min(duration,end)
        if end<=start:
            continue
        viseme=PHONEMES.get(phoneme)
        # Stress/length/combining markers continue the preceding articulation,
        # rather than forcing an artificial closed mouth inside a vowel.
        if viseme is None and (phoneme in 'ˈˌːˑ' or unicodedata.combining(phoneme)):
            if cues:cues[-1][1]=round(max(cues[-1][1],end),5)
            continue
        if viseme is None:
            continue
        if cues and start<cues[-1][0]-0.001:
            return None
        if cues and cues[-1][2]==viseme and start<=cues[-1][1]+0.001:
            cues[-1][1]=round(max(cues[-1][1],end),5)
        else:
            cues.append([round(start,5),round(end,5),viseme])
        if len(cues)>MAX_CUES:return None
    if not any(cue[2]!='viseme_sil' for cue in cues):return None
    return {'version':1,'duration':round(duration,5),'cues':cues}


def append_viseme_chunk(wav, timings, duration):
    """Append optional metadata; malformed/unsupported timing leaves WAV intact."""
    timing=viseme_timing(timings,duration)
    if not timing:return wav
    if (not isinstance(wav,bytes) or len(wav)<44 or wav[:4]!=b'RIFF'
            or wav[8:12]!=b'WAVE' or struct.unpack_from('<I',wav,4)[0]+8!=len(wav)):
        raise ValueError('Use a complete PCM WAV for speech timing')
    payload=json.dumps(timing,separators=(',',':'),allow_nan=False).encode('utf8')
    if len(payload)>MAX_BYTES:return wav
    chunk=b'MPVS'+struct.pack('<I',len(payload))+payload+(b'\0' if len(payload)%2 else b'')
    result=wav[:4]+struct.pack('<I',len(wav)+len(chunk)-8)+wav[8:]+chunk
    return result


def create_speech(engine, text, voice, language, speed):
    """Use durations already computed by installed Kokoro, with legacy fallback."""
    if getattr(engine,'has_timings',False) and callable(getattr(engine,'create_timed',None)):
        return engine.create_timed(text,voice=voice,lang=language,speed=speed)
    samples,rate=engine.create(text,voice=voice,lang=language,speed=speed)
    return samples,rate,[]
