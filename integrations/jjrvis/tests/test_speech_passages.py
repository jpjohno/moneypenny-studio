import asyncio
import cloud_ai
import voice_profiles
import local_voice


def test_explicit_cloud_reply_is_one_recording_with_full_text(monkeypatch):
    calls = []
    monkeypatch.setattr(cloud_ai.usage_meter, 'record', lambda *args, **kwargs: None)
    class Response:
        content = b'\x01\x00' * 24
        def raise_for_status(self): pass
    class Client:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers, json):
            calls.append(json)
            return Response()
    monkeypatch.setattr(cloud_ai.httpx, 'AsyncClient', Client)
    monkeypatch.setattr(cloud_ai, 'headers', lambda: {})
    async def forbid_local(*args, **kwargs):
        raise AssertionError('An explicit cloud speech fixture must never launch the real local voice worker')
    monkeypatch.setattr(local_voice, 'speech', forbid_local)
    text = 'James, your afternoon appointment is at 14:30. ' * 40
    # Jarvis/English is now deliberately local. Exercise the retained explicit
    # cloud alternative, without relying on or changing the saved preference.
    profile = dict(voice_profiles.PROFILES['american'])
    result = asyncio.run(cloud_ai.speech(text, profile))
    assert result.startswith(b'RIFF')
    assert result.endswith(Response.content)
    assert len(calls) == 1
    assert calls[0]['input'] == text
    assert calls[0]['voice'] == profile['voice']
    assert calls[0]['instructions'] == profile.get('speech_instructions', profile['style'])
    assert calls[0]['response_format'] == 'pcm'
