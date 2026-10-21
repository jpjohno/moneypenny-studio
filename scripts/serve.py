"""Run the studio with a production WSGI server, restricted to this Mac."""
import os
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def rotate_logs(directory, limit=5 * 1024 * 1024):
    """Retain one previous private log when the service starts again."""
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    for name in ('stdout.log', 'stderr.log'):
        path = directory / name
        if path.is_symlink():
            raise SystemExit('Service log must be an ordinary private file.')
        if path.exists() and path.stat().st_size > limit:
            with path.open('rb') as source:
                source.seek(-limit, os.SEEK_END)
                previous = path.with_suffix('.previous.log')
                previous.write_bytes(source.read(limit))
                previous.chmod(0o600)
            # launchd has already opened this file. Keep its inode so the
            # current process still writes to the visible stdout/stderr log.
            path.write_bytes(b'')
        if not path.exists():
            path.touch(mode=0o600)
        path.chmod(0o600)


def main():
    os.umask(0o077)
    rotate_logs(Path(os.environ.get('MONEYPENNY_LOG_DIR', str(ROOT / '.runtime/service'))))
    port = int(os.environ.get('MONEYPENNY_PORT', '8090'))
    if not 1024 <= port <= 65535:
        raise SystemExit('Choose a non-privileged studio port.')
    from waitress import create_server
    from app import app, listening, voice

    server = create_server(app, host='127.0.0.1', port=port, threads=4,
                           connection_limit=32, channel_timeout=60,
                           max_request_body_size=26 * 1024 * 1024,
                           expose_tracebacks=False, clear_untrusted_proxy_headers=True)

    def shutdown(signum, frame):
        server.close()
        listening.close()
        voice.close()
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    print(f'Moneypenny service ready at http://127.0.0.1:{port}', flush=True)
    try:
        server.run()
    finally:
        server.close()
        listening.close()
        voice.close()


if __name__ == '__main__':
    main()
