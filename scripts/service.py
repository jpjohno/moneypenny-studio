"""Install and manage this owner's local macOS Moneypenny service."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
LABEL = 'com.jamesjohnston.moneypenny-studio'
DOMAIN = f'gui/{os.getuid()}'
TARGET = DOMAIN + '/' + LABEL
AGENT = Path.home() / 'Library/LaunchAgents' / (LABEL + '.plist')
RUNTIME = ROOT / '.runtime/service'
LOGS = Path.home() / 'Library/Logs/Moneypenny-Studio'
URL = 'http://127.0.0.1:8090'


def definition(root=ROOT):
    root = Path(root)
    return {
        'Label': LABEL,
        'ProgramArguments': [str(root / '.venv/bin/python'), str(root / 'scripts/serve.py')],
        'WorkingDirectory': str(root),
        'EnvironmentVariables': {'PYTHONUNBUFFERED': '1', 'MONEYPENNY_PORT': '8090',
                                 'MONEYPENNY_OLLAMA_URL': 'http://127.0.0.1:11434',
                                 'MONEYPENNY_LOG_DIR': str(LOGS)},
        'RunAtLoad': True, 'KeepAlive': True, 'ThrottleInterval': 10,
        # Speech is an interactive request. Background classification throttles
        # its child inference worker and delays the first audible phrase.
        'Umask': 0o077, 'ProcessType': 'Interactive',
        'StandardOutPath': str(LOGS / 'stdout.log'),
        'StandardErrorPath': str(LOGS / 'stderr.log'),
    }


def ready(timeout=1):
    try:
        with urllib.request.urlopen(URL + '/api/status?quick=1', timeout=timeout) as response:
            return json.load(response).get('app') == 'moneypenny-studio'
    except (OSError, ValueError):
        return False


def loaded():
    return subprocess.run(['/bin/launchctl', 'print', TARGET], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, check=False).returncode == 0


def private_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def prepare():
    if not (ROOT / '.venv/bin/python').is_file() or importlib.util.find_spec('waitress') is None:
        raise SystemExit('Run Start-Moneypenny.command once to install the studio dependencies.')
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    RUNTIME.chmod(0o700)
    LOGS.mkdir(parents=True, exist_ok=True, mode=0o700)
    LOGS.chmod(0o700)
    for name in ('stdout.log', 'stderr.log'):
        path = LOGS / name
        if path.is_symlink():
            raise SystemExit('Service log must be an ordinary private file.')
        path.touch(mode=0o600, exist_ok=True)
        path.chmod(0o600)
    expected = plistlib.dumps(definition(), sort_keys=True)
    if AGENT.exists() and AGENT.read_bytes() != expected:
        backup = RUNTIME / f'launchagent-before-{time.time_ns()}.plist'
        private_write(backup, AGENT.read_bytes())
    private_write(AGENT, expected)


def wait_ready():
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if ready():
            return
        time.sleep(.25)
    raise SystemExit('The service did not become ready. Private diagnostics are in ' + str(LOGS))


def bootstrap():
    # launchd can acknowledge bootout before releasing the old job. Retry only
    # its transient I/O result, with a short fixed deadline and no other changes.
    for attempt in range(4):
        try:
            subprocess.run(['/bin/launchctl', 'bootstrap', DOMAIN, str(AGENT)], check=True)
            return
        except subprocess.CalledProcessError as error:
            if error.returncode != 5 or attempt == 3:
                raise
            time.sleep(.25 * (attempt + 1))


def start():
    if loaded():
        if not ready():
            subprocess.run(['/bin/launchctl', 'kickstart', TARGET], check=True)
    else:
        with socket.socket() as probe:
            occupied = probe.connect_ex(('127.0.0.1', 8090)) == 0
        if occupied:
            if ready():
                raise SystemExit('The studio is running outside its login service. Close its original Terminal instance, then start again; nothing was stopped.')
            raise SystemExit('Port 8090 belongs to another program. Nothing was stopped.')
        prepare()
        bootstrap()
    wait_ready()


def status():
    return {'installed': AGENT.is_file(), 'loaded': loaded(), 'ready': ready(),
            'url': URL, 'logs': str(LOGS)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'start', 'restart', 'stop', 'remove', 'status'))
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise SystemExit('This login service is for macOS. Use scripts/launch.py on other platforms.')
    os.umask(0o077)
    if args.action in {'install', 'start'}:
        start()
    elif args.action == 'restart':
        if loaded():
            # Reload the definition too: kickstart alone retains old scheduling
            # and environment settings even when the plist has been updated.
            prepare()
            subprocess.run(['/bin/launchctl', 'bootout', TARGET], check=True)
            bootstrap()
            wait_ready()
        else:
            start()
    elif args.action in {'stop', 'remove'}:
        if loaded():
            subprocess.run(['/bin/launchctl', 'bootout', TARGET], check=True)
        if args.action == 'remove' and AGENT.exists():
            RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
            AGENT.replace(RUNTIME / f'removed-launchagent-{time.time_ns()}.plist')
    print(json.dumps(status(), indent=2))


if __name__ == '__main__':
    main()
