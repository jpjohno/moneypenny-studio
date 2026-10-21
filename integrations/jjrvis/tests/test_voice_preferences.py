import pytest
import voice_profiles as v

def test_choices_persist_independently(tmp_path,monkeypatch):
    monkeypatch.setattr(v,'PATH',tmp_path/'preferences.json')
    assert v.selected()['model']=='gpt-4.1-mini'
    v.save('moneypenny',1.15,'gpt-4.1')
    assert v.current()['voice']=='bf_emma'
    assert v.current()['provider']=='local-kokoro'
    assert v.public()['resolved_model']=='gpt-4.1'
    v.save('english',1.3)
    assert v.selected()['model']=='gpt-4.1'
    assert v.current()['name']=='Jarvis'
    assert v.current()['voice']=='bm_george'
    assert v.current()['provider']=='local-kokoro'
    assert v.PATH.stat().st_mode & 0o777==0o600
    with pytest.raises(ValueError):v.save('bad',1.3)
    with pytest.raises(ValueError):v.save('english',1.3,'unknown')

def test_answer_model_alias_reports_the_engine_that_runs():
    assert v.resolved_model('local-moneypenny')=='MoneyPenny:latest'
    assert v.resolved_model('ollama:uncensored-3b:latest')=='uncensored-3b:latest'


@pytest.mark.parametrize('model', list(v.MODELS))
def test_every_offered_model_accepted_by_request_schema(model):
    from jarvis_comm_broker import VoicePreference
    assert VoicePreference(profile='moneypenny', speed=1, model=model).model == model


def test_public_voice_identity_is_explicit_and_speech_pin_does_not_persist(tmp_path, monkeypatch):
    monkeypatch.setattr(v, 'PATH', tmp_path/'preferences.json')
    v.save('moneypenny', 1.15, 'gpt-4.1-mini')
    assert v.public()['voice'] == {'provider':'local-kokoro','voice':'bf_emma','language':'en-GB'}
    pinned = v.for_speech('english', 1.0)
    assert (pinned['profile'], pinned['voice'], pinned['language'], pinned['speed']) == ('english','bm_george','en-GB',1.0)
    assert v.selected()['profile'] == 'moneypenny'
    assert v.selected()['speed'] == 1.15
    for speed in (True, float('nan'), .4):
        with pytest.raises(ValueError): v.for_speech('english', speed)
