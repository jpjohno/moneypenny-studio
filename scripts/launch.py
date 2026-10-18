"""Open an existing instance or run our own local studio without stopping services."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get('MONEYPENNY_PORT', '8090'))
URL = f'http://127.0.0.1:{PORT}'


def ready():
    try:
        with urllib.request.urlopen(URL + '/api/status', timeout=4) as response:
            return json.load(response).get('app') == 'moneypenny-studio'
    except Exception:
        return False


def open_browser():
    if sys.platform == 'darwin':
        subprocess.Popen(['/usr/bin/open', URL])
    else:
        import webbrowser
        webbrowser.open(URL)


def main():
    if ready():
        open_browser()
        print(f'Moneypenny Studio is already running: {URL}')
        return
    with socket.socket() as check:
        if check.connect_ex(('127.0.0.1', PORT)) == 0:
            raise SystemExit(f'Port {PORT} is occupied by another program. Nothing was stopped. Set MONEYPENNY_PORT to another free port.')
    process = subprocess.Popen([sys.executable, str(ROOT / 'app.py')], cwd=ROOT)

    def open_when_ready():
        for _ in range(25):
            if ready():
                open_browser()
                return
            if process.poll() is not None:
                return
            time.sleep(.3)

    threading.Thread(target=open_when_ready, daemon=True).start()
    print(f'Opening {URL}. Keep this Terminal window open; press Control-C to stop the studio.', flush=True)
    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait(timeout=5)


if __name__ == '__main__':
    main()
