import time

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import sky_weather


def payload():
    now = int(time.time())
    return {'timezone': 'Europe/London',
            'current': {'time': now, 'temperature_2m': 13, 'apparent_temperature': 12,
                        'wind_speed_10m': 8, 'cloud_cover': 15, 'is_day': 0, 'weather_code': 1},
            'daily': {'time': [now], 'temperature_2m_max': [16], 'temperature_2m_min': [8],
                      'precipitation_probability_max': [20], 'sunrise': [now-36000],
                      'sunset': [now-3000], 'weather_code': [1]}}


def client(handler, secured=False):
    from fastapi import Depends
    app = FastAPI()
    async def reject():
        raise HTTPException(401)
    sky_weather.register_routes(app, [Depends(reject)] if secured else [], transport=httpx.MockTransport(handler))
    return TestClient(app)


def test_auth_does_not_contact_provider():
    def provider(request):
        pytest.fail('Unauthenticated requests cannot contact provider')
    with client(provider, True) as c:
        assert c.get('/v1/workspace/weather?latitude=52&longitude=0').status_code == 401


def test_fixed_provider_rounded_location_cache_and_real_timestamps():
    calls = []
    def provider(request):
        calls.append(request)
        assert str(request.url).startswith('https://api.open-meteo.com/v1/forecast?')
        assert request.url.params['latitude'] == '52.12'
        assert request.url.params['longitude'] == '-0.56'
        return httpx.Response(200, json=payload())
    with client(provider) as c:
        first = c.get('/v1/workspace/weather?latitude=52.123456&longitude=-0.555555').json()
        second = c.get('/v1/workspace/weather?latitude=52.123456&longitude=-0.555555').json()
    assert len(calls) == 1 and first['cached'] is False and second['cached'] is True
    assert first['data_kind'] == 'weather_model' and first['is_day'] is False
    assert first['valid_at'] > 1e9 and first['fetched_at'] > 1e9
    assert 'latitude' not in first


@pytest.mark.parametrize('query', ['latitude=91&longitude=0', 'latitude=nan&longitude=0', 'latitude=0&longitude=181'])
def test_invalid_coordinates_do_not_contact_provider(query):
    with client(lambda req: pytest.fail('Invalid coordinates reached provider')) as c:
        assert c.get('/v1/workspace/weather?'+query).status_code == 422


@pytest.mark.parametrize('change', ['missing', 'bad_temperature', 'bad_timezone', 'wrong_current'])
def test_invalid_weather_never_becomes_live_data(change):
    data = payload()
    if change == 'missing': del data['daily']
    if change == 'bad_temperature': data['current']['temperature_2m'] = 999
    if change == 'bad_timezone': data['timezone'] = 'Not/A_Timezone'
    if change == 'wrong_current': data['current'] = []
    with client(lambda req: httpx.Response(200, json=data)) as c:
        result = c.get('/v1/workspace/weather?latitude=52&longitude=0')
    assert result.status_code == 503 and 'not a live reading' in result.json()['detail']


def test_polar_night_can_have_no_sunrise_or_sunset():
    data = payload(); data['daily']['sunrise'] = [None]; data['daily']['sunset'] = [None]
    with client(lambda req: httpx.Response(200, json=data)) as c:
        result = c.get('/v1/workspace/weather?latitude=85&longitude=0')
    assert result.status_code == 200 and result.json()['days'][0]['sunrise'] is None
