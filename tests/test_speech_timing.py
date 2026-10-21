import io
import json
import math
import struct
from types import SimpleNamespace as Timing
import wave

from speech_timing import append_viseme_chunk, create_speech, viseme_timing


def wav():
    stream=io.BytesIO()
    with wave.open(stream,'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(24000)
        audio.writeframes(b'\x01\x00'*24000)
    return stream.getvalue()


def test_wav_stays_sample_identical_with_optional_text_free_timing():
    original=wav()
    cues=[Timing(phoneme='p',start=.02,end=.10),Timing(phoneme='ɑ',start=.10,end=.30),Timing(phoneme='m',start=.30,end=.40)]
    result=append_viseme_chunk(original,cues,1)
    assert len(result)>len(original)
    assert struct.unpack_from('<I',result,4)[0]+8==len(result)
    with wave.open(io.BytesIO(original)) as before,wave.open(io.BytesIO(result)) as after:
        assert before.getparams()==after.getparams()
        assert before.readframes(24000)==after.readframes(24000)
    at=len(original)
    assert result[at:at+4]==b'MPVS'
    size=struct.unpack_from('<I',result,at+4)[0]
    data=json.loads(result[at+8:at+8+size])
    assert data=={'version':1,'duration':1,'cues':[[.02,.10,'viseme_PP'],[.10,.30,'viseme_aa'],[.30,.40,'viseme_PP']]}


def test_stress_and_length_continue_the_vowel_and_adjacent_equal_shapes_merge():
    data=viseme_timing([Timing(phoneme=p,start=i*.1,end=(i+1)*.1) for i,p in enumerate(['ɑ','ː','ɑ',' ','m'])],.5)
    assert data['cues']==[[0,.3,'viseme_aa'],[.3,.4,'viseme_sil'],[.4,.5,'viseme_PP']]


def test_invalid_or_unusable_timing_preserves_ordinary_wav_fallback():
    original=wav()
    cases=[[],[Timing(phoneme='🙂',start=0,end=.1)],
           [Timing(phoneme='p',start=math.nan,end=.1)],
           [Timing(phoneme='p',start=.2,end=.1)],
           [Timing(phoneme='p',start=True,end=.1)],
           [Timing(phoneme='p',start=0,end=2)],
           [Timing(phoneme='p',start=.3,end=.4),Timing(phoneme='ɑ',start=.1,end=.2)]]
    for timings in cases:assert append_viseme_chunk(original,timings,1)==original


def test_duration_is_already_computed_in_one_synthesis_call():
    calls=[]
    class Engine:
        has_timings=True
        def create_timed(self,*args,**kwargs):
            calls.append((args,kwargs));return b'samples',24000,['timing']
        def create(self,*args,**kwargs):raise AssertionError('must not synthesize twice')
    assert create_speech(Engine(),'A sample.','bf_emma','en-gb',1.2)==(b'samples',24000,['timing'])
    assert calls==[(('A sample.',),{'voice':'bf_emma','lang':'en-gb','speed':1.2})]


def test_older_voice_engine_can_still_return_plain_audio():
    class Engine:
        def create(self,*args,**kwargs):return b'samples',24000
    assert create_speech(Engine(),'A sample.','bf_emma','en-gb',1)==(b'samples',24000,[])
