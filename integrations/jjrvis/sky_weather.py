"""Bounded weather reads for an explicitly chosen location. No device activation."""
import asyncio
import math
import time
from collections import OrderedDict

import httpx
from fastapi import HTTPException, Query

TTL = 600
CONDITIONS = {0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
              45: 'Fog', 48: 'Freezing fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
              56: 'Freezing drizzle', 57: 'Freezing drizzle', 61: 'Light rain', 63: 'Rain',
              65: 'Heavy rain', 66: 'Freezing rain', 67: 'Freezing rain', 71: 'Light snow',
              73: 'Snow', 75: 'Heavy snow', 77: 'Snow grains', 80: 'Rain showers',
              81: 'Rain showers', 82: 'Heavy showers', 85: 'Snow showers', 86: 'Heavy snow showers',
              95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Thunderstorm with hail'}


def register_routes(app, secure, *, transport=None):
    cache = OrderedDict()
    lock = asyncio.Lock()

    @app.get('/v1/workspace/weather', dependencies=secure)
    async def weather(latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180)):
        if not all(math.isfinite(v) for v in (latitude, longitude)):
            raise HTTPException(422, 'Choose a valid place')
        # Town-level accuracy is sufficient. Never forward exact device coordinates.
        key = (round(latitude, 2), round(longitude, 2))
        async with lock:
            cached = cache.get(key)
            if cached and time.time() - cached['fetched_at'] < TTL:
                return {**cached, 'cached': True}
            params = {'latitude': key[0], 'longitude': key[1], 'timezone': 'auto', 'timeformat': 'unixtime',
                      'forecast_days': 3,
                      'current': 'temperature_2m,apparent_temperature,weather_code,is_day,cloud_cover,wind_speed_10m',
                      'daily': 'temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset,weather_code'}
            try:
                async with httpx.AsyncClient(timeout=8, trust_env=False, transport=transport) as client:
                    response = await client.get('https://api.open-meteo.com/v1/forecast', params=params)
                    response.raise_for_status()
                data = response.json()
                current, daily = data['current'], data['daily']
                if not isinstance(current, dict) or not isinstance(daily, dict):
                    raise ValueError('Invalid weather data')
                def number(value, lo, hi):
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
                        raise ValueError('Invalid weather value')
                    return value
                rows = []
                for i, stamp in enumerate(daily['time'][:3]):
                    rows.append({'time': number(stamp, 1e9, 1e10),
                                 'high_c': number(daily['temperature_2m_max'][i], -100, 70),
                                 'low_c': number(daily['temperature_2m_min'][i], -100, 70),
                                 'rain_chance': number(daily['precipitation_probability_max'][i], 0, 100),
                                 # Polar day/night can legitimately have null sunrise or sunset.
                                 'sunrise': number(daily['sunrise'][i], 1e9, 1e10) if daily['sunrise'][i] is not None else None,
                                 'sunset': number(daily['sunset'][i], 1e9, 1e10) if daily['sunset'][i] is not None else None,
                                 'condition': CONDITIONS.get(daily['weather_code'][i], 'Conditions unavailable')})
                if not rows:
                    raise ValueError('Daily weather absent')
                result = {'source': 'Open-Meteo', 'source_url': 'https://open-meteo.com/',
                          'data_kind': 'weather_model', 'fetched_at': time.time(),
                          'valid_at': number(current['time'], 1e9, 1e10),
                          'timezone': str(data['timezone'])[:80],
                          'temperature_c': number(current['temperature_2m'], -100, 70),
                          'feels_like_c': number(current['apparent_temperature'], -120, 90),
                          'wind_kmh': number(current['wind_speed_10m'], 0, 500),
                          'cloud_percent': number(current['cloud_cover'], 0, 100),
                          'is_day': number(current['is_day'], 0, 1) == 1,
                          'condition': CONDITIONS.get(current['weather_code'], 'Conditions unavailable'),
                          'days': rows, 'cached': False, 'refresh_seconds': TTL}
                # Verify the timezone before it can reach a browser Intl formatter.
                from zoneinfo import ZoneInfo
                ZoneInfo(result['timezone'])
            except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
                raise HTTPException(503, 'Weather is unavailable. Your last view is not a live reading.')
            cache[key] = result
            cache.move_to_end(key)
            while len(cache) > 64:
                cache.popitem(last=False)
            return result
