"""Reproducible free assets; optionally set up an independent local voice."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / '.runtime'


def download(url, target, digest=None):
    if target.is_file() and (not digest or hashlib.sha256(target.read_bytes()).hexdigest() == digest):
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.partial')
    print(f'Downloading {target.name}…', flush=True)
    with urllib.request.urlopen(url, timeout=180) as source, temporary.open('wb') as output:
        while block := source.read(1024 * 1024):
            output.write(block)
    if digest and hashlib.sha256(temporary.read_bytes()).hexdigest() != digest:
        raise ValueError(f'Checksum mismatch for {target.name}. Remove its .partial download and retry.')
    temporary.replace(target)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--voice', action='store_true', help='Install free Kokoro and Vosk in this checkout (several hundred MB).')
    parser.add_argument('--link-jjrvis', type=Path, help='Reuse an existing JJRVIS communication_broker runtime, read-only.')
    args = parser.parse_args()
    RUNTIME.mkdir(exist_ok=True)
    for item in json.loads((ROOT / 'assets-manifest.json').read_text()):
        download(item['url'], ROOT / item['path'], item['sha256'])
    config_path = RUNTIME / 'machine.json'
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    broker = args.link_jjrvis or (Path.home() / '.codex/.chatgpt-projects/g-p-695eea173370819196be0c9be135bb6e/outputs/communication_broker')
    if (broker / '.runtime/kokoro-env/bin/python').is_file() and not args.voice and (args.link_jjrvis or not config.get('voice_python')):
        config.update(voice_python=str(broker / '.runtime/kokoro-env/bin/python'), voice_models=str(broker / '.runtime/kokoro-models'))
        if (broker / '.venv/bin/python').is_file() and (Path.home() / '.cache/jjrvis-speech/vosk-model-small-en-us-0.15').is_dir():
            config.update(transcribe_python=str(broker / '.venv/bin/python'), transcribe_model=str(Path.home() / '.cache/jjrvis-speech/vosk-model-small-en-us-0.15'))
        print('Existing JJRVIS model files reused. Existing services and preferences are unchanged.')
    if args.voice:
        environment = ROOT / '.voice-venv'
        subprocess.run([sys.executable, '-m', 'venv', str(environment)], check=True)
        python = environment / 'bin/python'
        subprocess.run([str(python), '-m', 'pip', 'install', 'kokoro-onnx==0.6.1', 'vosk==0.3.45'], check=True)
        models = RUNTIME / 'kokoro-models'
        prefix = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
        for name, digest in (
            ('kokoro-v1.0.onnx', 'beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a'),
            ('voices-v1.0.bin', 'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d'),
        ):
            download(prefix + name, models / name, digest)
        archive = RUNTIME / 'vosk-model-small-en-us-0.15.zip'
        download('https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip', archive)
        with zipfile.ZipFile(archive) as bundle:
            if any(not (RUNTIME / name).resolve().is_relative_to(RUNTIME.resolve()) for name in bundle.namelist()):
                raise ValueError('Invalid Vosk archive paths.')
            bundle.extractall(RUNTIME)
        config.update(voice_python=str(python), voice_models=str(models), transcribe_python=str(python), transcribe_model=str(RUNTIME / 'vosk-model-small-en-us-0.15'))
    config_path.write_text(json.dumps(config, indent=2) + '\n')
    config_path.chmod(0o600)
    print('Studio assets ready. Start with ./Start-Moneypenny.command')
    if not config.get('voice_python'):
        print('Voice setup: .venv/bin/python scripts/setup.py --voice')


if __name__ == '__main__':
    main()
