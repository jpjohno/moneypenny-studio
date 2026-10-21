"""Voice-control help routing without microphone, model calls or owner data."""
import asyncio
import pytest

from jjrvis_core import voice_controls_request, literal_speech_request
from jarvis_comm_broker import Settings
from test_core import core, fake_model, cite_evidence, TOKEN


@pytest.mark.parametrize('question', [
    'For a voice check, say exactly: A calm afternoon at home.',
    'Please say exactly: How do I enable my microphone?',
    'Read the following: How do I stop voice?',
    'Say: How can I use the microphone?',
    'Please repeat "How do I enable the microphone?"',
    'Explain the line “Can you hear me?”',
    "Discuss the phrase 'How do I start voice?'",
    'Tell me about voice acting.',
    'You have a clear speaking voice.',
    'Write a conversation between two people.',
    'I heard a bird singing this morning.',
])
def test_voice_mentions_and_spoken_payloads_are_not_microphone_help(question):
    assert voice_controls_request(question) is False


@pytest.mark.parametrize('question', [
    'Can you hear me and speak the answer?',
    'How do I enable the microphone?',
    'Moneypenny, how can I use voice?',
    'How do I start conversation?',
    'How do I stop you speaking?',
    'How can I talk to you?',
    'Where are the microphone settings?',
    'Are you listening?',
    'Do you listen continuously?',
    'My microphone is not working.',
    'The audio is not working.',
    'No sound.',
])
def test_actual_microphone_controls_and_listening_help_are_preserved(question):
    assert voice_controls_request(question) is True


def test_native_voice_check_returns_exact_text_without_a_model_or_source_read(core, monkeypatch):
    question='For a voice check, say exactly: A calm afternoon at home.'
    requests=fake_model(monkeypatch,{'answer':'Must not be requested.'})
    def forbidden_plan():
        pytest.fail('A literal speech check must not read owner context')
    monkeypatch.setattr(core,'plan',forbidden_plan)
    result=asyncio.run(core.ask(question,Settings(token=TOKEN)))
    assert result['answer']=='A calm afternoon at home.'
    assert result['mode']=='literal_speech'
    assert result['model']=='local-speech-utility'
    assert result['actions_executed'] is False
    assert result['sources']==[] and result['web_results']==[]
    assert requests==[]


def test_genuine_microphone_help_stays_deterministic(core, monkeypatch):
    requests=fake_model(monkeypatch,{'answer':'Must not be requested.'})
    result=asyncio.run(core.ask('How do I enable the microphone?',Settings(token=TOKEN)))
    assert 'Speak your question' in result['answer']
    assert result['sources'][0]['title']=='JJRVIS phone voice controls'
    assert requests==[]


@pytest.mark.parametrize('question,expected', [
    ('say exactly: A calm afternoon at home.','A calm afternoon at home.'),
    ('For a voice check, say exactly: A calm afternoon at home.','A calm afternoon at home.'),
    (' Please say exactly: How do I enable the microphone? ','How do I enable the microphone?'),
    ('SAY EXACTLY: Keep This Case.','Keep This Case.'),
    ('say exactly: '+('x'*400),'x'*400),
])
def test_only_explicit_top_level_bounded_literal_forms_are_parsed(question, expected):
    assert literal_speech_request(question)==expected


@pytest.mark.parametrize('question', [
    'say exactly:',
    'say exactly:   ',
    'say exactly: '+('x'*401),
    'Explain why "say exactly: A calm afternoon at home." is useful.',
    '"For a voice check, say exactly: A calm afternoon at home."',
    'Here is an instruction: say exactly: A calm afternoon at home.',
    'What should I say exactly?',
    'How do I enable the microphone?',
])
def test_literal_text_embedded_in_analysis_or_invalid_payload_is_not_executed(question):
    assert literal_speech_request(question) is None


def test_literal_speech_does_not_dispatch_embedded_device_commands(core, monkeypatch):
    import bluos_control
    async def forbidden(*args, **kwargs):
        pytest.fail('A literal speech check must not dispatch a device command')
    monkeypatch.setattr(bluos_control,'assistant_request',forbidden)
    result=asyncio.run(core.ask('say exactly: Turn the speaker off.',Settings(token=TOKEN)))
    assert result['answer']=='Turn the speaker off.'
    assert result['actions_executed'] is False
