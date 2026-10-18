"""Download pinned local authoring data; never install the legacy MHX addon."""
import hashlib
import json
from pathlib import Path
import stat
import subprocess
import urllib.request
import zipfile


def verified(path, expected):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest() == expected


def main():
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads(Path(__file__).with_name('body-assets.json').read_text())
    tools = root / '.runtime/character-tools'
    assets = tools / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    for pack in manifest['packs']:
        archive = assets / (pack['name'] + '.zip')
        if not archive.exists():
            partial = archive.with_suffix('.download')
            with urllib.request.urlopen(pack['url'], timeout=60) as source, partial.open('wb') as destination:
                while chunk := source.read(1024 * 1024):
                    destination.write(chunk)
            if not verified(partial, pack['sha256']):
                raise ValueError('Downloaded pack checksum mismatch: ' + pack['name'])
            partial.rename(archive)
        if not verified(archive, pack['sha256']):
            raise ValueError('Existing pack checksum mismatch; preserved: ' + str(archive))
        destination = assets / pack['name']
        if not destination.exists():
            with zipfile.ZipFile(archive) as zipped:
                for item in zipped.infolist():
                    target = (destination / item.filename).resolve()
                    if not target.is_relative_to(destination.resolve()) or stat.S_ISLNK(item.external_attr >> 16):
                        raise ValueError('Unsafe archive entry')
                zipped.extractall(destination)
        print('Verified authoring pack:', pack['name'])
    source = manifest['anatomy_source']
    checkout = tools / 'mhx2-source'
    if not checkout.exists():
        subprocess.run(['git', 'clone', '--no-checkout', source['repository'], str(checkout)], check=True)
        subprocess.run(['git', '-C', str(checkout), 'checkout', '--detach', source['commit']], check=True)
    revision = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != source['commit'] or not verified(checkout / source['path'], source['sha256']):
        raise ValueError('Existing anatomy data differs from the pinned source; preserved for review.')
    print('Verified local anatomy data. Redistribution licence remains unresolved; see body-assets.json.')


if __name__ == '__main__':
    main()
