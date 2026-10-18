"""Bounded connection inventory. Never generates text or activates a device.

Only the two loopback services are probed. Home, phone and car summaries read
saved configuration; saved records are deliberately not called live devices.
"""
import asyncio
import json
import math
import time
from pathlib import Path

import httpx

import cloud_ai
import voice_profiles

OLLAMA_TIMEOUT_SECONDS = 4
STUDIO_TIMEOUT_SECONDS = 2


def read_json(path, default):
    try:
        if path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
            return default
        value = json.loads(path.read_text())
        return value if isinstance(value, type(default)) else default
    except (OSError, ValueError):
        return default


def age(value, now):
    try:
        result = now - float(value)
        return round(result, 1) if math.isfinite(result) and result >= 0 else None
    except (ValueError, TypeError):
        return None


async def snapshot(settings, infrastructure, *, runtime, private_config=None, transport=None):
    now = time.time()
    preference = voice_profiles.selected()['model']
    local_selected = preference == 'local-moneypenny' or preference.startswith('ollama:')
    cloud_enabled = cloud_ai.enabled()
    uses_local = local_selected or not cloud_enabled
    selected_model = voice_profiles.resolved_model(preference) if local_selected or cloud_enabled else settings.model
    try:
        credential_configured = bool(cloud_ai.key().strip())
    except (OSError, ValueError):
        credential_configured = False

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_SECONDS, trust_env=False, follow_redirects=False, transport=transport) as client:
        async def probe(url, timeout, *, models=False):
            started = time.monotonic()
            check = {'state': 'unavailable', 'reason': None, 'timeout_seconds': timeout}
            async def read():
                response = await client.get(url, timeout=timeout)
                response.raise_for_status()
                if len(response.content) > 512 * 1024:
                    return None, 'response_too_large'
                value = response.json()
                if not isinstance(value, dict) or (models and not isinstance(value.get('models'), list)):
                    return None, 'invalid_response'
                return value, None
            try:
                value, reason = await asyncio.wait_for(read(), timeout=timeout)
                check.update(state='ready' if value is not None else 'unavailable', reason=reason)
            except (httpx.TimeoutException, asyncio.TimeoutError):
                value = None
                check['reason'] = 'timeout'
            except httpx.HTTPStatusError as error:
                value = None
                check.update(reason='http_error', status_code=error.response.status_code)
            except httpx.HTTPError:
                value = None
                check['reason'] = 'connection_failed'
            except ValueError:
                value = None
                check['reason'] = 'invalid_response'
            check['duration_seconds'] = round(time.monotonic() - started, 3)
            return value, check
        (tags, tags_check), (running, running_check), (studio, studio_check) = await asyncio.gather(
            probe(settings.ollama_url.rstrip('/') + '/api/tags', OLLAMA_TIMEOUT_SECONDS, models=True),
            probe(settings.ollama_url.rstrip('/') + '/api/ps', OLLAMA_TIMEOUT_SECONDS, models=True),
            probe('http://127.0.0.1:8090/api/status?quick=1', STUDIO_TIMEOUT_SECONDS))

    def model_names(value):
        rows = (value or {}).get('models', [])
        rows = rows if isinstance(rows, list) else []
        return {row['name'] for row in rows
                if isinstance(row, dict) and isinstance(row.get('name'), str)}
    installed, loaded = model_names(tags), model_names(running)
    ai = {
        'provider': 'ollama' if uses_local else 'openai',
        'selected_model': selected_model,
        'state': ('ready' if selected_model in installed else 'model_missing' if tags is not None else 'unavailable')
                 if uses_local else ('configured_unverified' if credential_configured else 'credential_required'),
        'selected_model_installed': selected_model in installed if uses_local and tags is not None else None,
        'selected_model_loaded': selected_model in loaded if uses_local and running is not None else None,
        'inference_tested_by_this_check': False,
        'catalogue_check': tags_check,
        'loaded_models_check': running_check,
        'cloud': {'enabled': cloud_enabled, 'credential_configured': credential_configured,
                  'connection_verified': False, 'automatic_fallback': False},
        'detail': 'Local model availability checked without generating a reply.' if uses_local else
                  'Cloud credentials are configured locally; this check makes no paid API request.'
    }
    registry = infrastructure._registry()
    entities = registry.get('entities', [])
    cameras = [row for row in entities if row.get('id', '').startswith('camera.') and not row.get('disabled')]
    devices = read_json(Path(runtime) / 'device-registry.json', [])
    devices = [row for row in devices if isinstance(row, dict)] if isinstance(devices, list) else []
    online = [row for row in devices if (seen := age(row.get('last_seen'), now)) is not None and seen < 180]
    private_config = Path(private_config or Path.home() / '.config/jjrvis')
    vehicle = read_json(private_config / 'bmw-vehicle.json', {})
    tokens = read_json(private_config / 'bmw-tokens.json', {})
    telemetry = read_json(private_config / 'bmw-telemetry.json', {})
    stream = read_json(private_config / 'bmw-stream-status.json', {})
    stream_age = age(stream.get('heartbeat_at'), now)
    return {
        'checked_at': now, 'ai': ai,
        'moneypenny': {
            'state': 'ready' if studio and studio.get('avatar_ready') else 'unavailable',
            'check': studio_check,
            'embedded_answer_provider': ai['provider'],
            'embedded_answer_model': selected_model,
            'standalone_model_selection': 'persona_or_browser_preference',
            'voice_ready': bool(studio and studio.get('voice_ready')),
            'microphone_engine_ready': bool(studio and studio.get('microphone_ready')),
            'microphone_permission': 'check_on_device',
            'character_revision': studio.get('character_revision') if studio else None,
            'photographic_realism_verified': False,
        },
        'home': {'state': 'saved_registry' if entities else 'not_configured',
                 'registered_entities': len(entities), 'device_states_connected': False,
                 'commands_enabled': False},
        'cameras': {'state': 'registered_only' if cameras else 'not_connected',
                    'registered_count': len(cameras), 'live_video_connected': False,
                    'camera_activated_by_this_check': False},
        'phones': {'state': 'pairing_available' if settings.origins else 'private_access_required',
                   'registered_devices': len(devices), 'recent_device_heartbeats': len(online),
                   'remote_origin_configured': bool(settings.origins), 'native_iphone_control': False},
        'vehicle': {'provider': 'BMW CarData',
                    'state': 'configured_unverified' if tokens.get('refresh_token') and vehicle.get('container_id') else 'authorisation_required',
                    'vehicle_registered': bool(vehicle.get('vin')),
                    'cached_observation_age_seconds': age(telemetry.get('retrieved_at'), now),
                    'stream_state': str(stream.get('state', 'unverified'))[:40] if stream_age is not None and stream_age < 180 else 'unverified',
                    'vehicle_control_enabled': False, 'other_brand_connections': 0,
                    'network_request_by_this_check': False},
    }
