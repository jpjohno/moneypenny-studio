"""Private loopback deployment contracts; never changes the host LaunchAgent."""
import importlib.util
from pathlib import Path
import plistlib

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_login_service_has_no_network_listener_override_or_credentials(tmp_path):
    service = module('service')
    definition = service.definition(tmp_path)
    assert definition['ProgramArguments'] == [str(tmp_path / '.venv/bin/python'), str(tmp_path / 'scripts/serve.py')]
    assert definition['RunAtLoad'] and definition['KeepAlive']
    assert definition['Umask'] == 0o077
    assert definition['ProcessType'] == 'Interactive'
    assert definition['EnvironmentVariables'] == {'PYTHONUNBUFFERED': '1', 'MONEYPENNY_PORT': '8090',
                                                 'MONEYPENNY_OLLAMA_URL': 'http://127.0.0.1:11434',
                                                 'MONEYPENNY_LOG_DIR': str(service.LOGS)}
    encoded = plistlib.dumps(definition)
    assert plistlib.loads(encoded) == definition


def test_private_config_write_is_atomic_and_preserves_private_mode(tmp_path):
    service = module('service')
    path = tmp_path / 'agents/service.plist'
    service.private_write(path, b'first')
    assert path.read_bytes() == b'first'
    assert path.stat().st_mode & 0o777 == 0o600
    service.private_write(path, b'second')
    assert path.read_bytes() == b'second'
    assert list(path.parent.iterdir()) == [path]


def test_log_rotation_keeps_the_open_descriptor_and_private_archive(tmp_path):
    server = module('serve')
    path = tmp_path / 'stdout.log'
    path.write_bytes(b'1234567890')
    inode = path.stat().st_ino
    server.rotate_logs(tmp_path, limit=5)
    assert path.stat().st_ino == inode
    assert path.read_bytes() == b''
    assert (tmp_path / 'stdout.previous.log').read_bytes() == b'67890'
    assert (tmp_path / 'stdout.previous.log').stat().st_mode & 0o777 == 0o600
    assert tmp_path.stat().st_mode & 0o777 == 0o700


def test_wsgi_server_cannot_bind_external_address():
    source = (ROOT / 'scripts/serve.py').read_text()
    assert "host='127.0.0.1'" in source
    assert 'expose_tracebacks=False' in source
    assert 'app.run(' not in source


def test_explicit_restart_reloads_scheduling_definition(monkeypatch):
    service = module('service')
    actions = []
    monkeypatch.setattr(service.sys, 'platform', 'darwin')
    monkeypatch.setattr(service.sys, 'argv', ['service.py', 'restart'])
    monkeypatch.setattr(service, 'loaded', lambda: True)
    monkeypatch.setattr(service, 'prepare', lambda: actions.append('prepare'))
    monkeypatch.setattr(service, 'wait_ready', lambda: actions.append('ready'))
    monkeypatch.setattr(service, 'status', lambda: {'ready': True})
    monkeypatch.setattr(service.subprocess, 'run', lambda argv, **kwargs: actions.append(argv[1]))
    service.main()
    assert actions == ['prepare', 'bootout', 'bootstrap', 'ready'], 'A stale Background job must not survive a scheduling fix'


def test_bootstrap_retries_only_transient_launchd_reload_race(monkeypatch):
    service = module('service')
    calls, pauses = [], []
    def run(argv, **kwargs):
        calls.append(argv)
        if len(calls) < 3:
            raise service.subprocess.CalledProcessError(5, argv)
    monkeypatch.setattr(service.subprocess, 'run', run)
    monkeypatch.setattr(service.time, 'sleep', pauses.append)
    service.bootstrap()
    assert len(calls) == 3 and pauses == [.25, .5]
    assert all(call[1] == 'bootstrap' for call in calls)


def test_bootstrap_does_not_retry_unrelated_failure_or_loop_forever(monkeypatch):
    import pytest
    service = module('service')
    calls = []
    def rejected(argv, **kwargs):
        calls.append(argv)
        raise service.subprocess.CalledProcessError(37, argv)
    monkeypatch.setattr(service.subprocess, 'run', rejected)
    monkeypatch.setattr(service.time, 'sleep', lambda value: None)
    with pytest.raises(service.subprocess.CalledProcessError):
        service.bootstrap()
    assert len(calls) == 1
    calls.clear()
    def transient(argv, **kwargs):
        calls.append(argv)
        raise service.subprocess.CalledProcessError(5, argv)
    monkeypatch.setattr(service.subprocess, 'run', transient)
    with pytest.raises(service.subprocess.CalledProcessError):
        service.bootstrap()
    assert len(calls) == 4
