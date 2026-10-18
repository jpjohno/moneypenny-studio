"""Fetch checksum-pinned, free character data from its attributed source."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request


def main():
    folder=Path(__file__).resolve().parent
    root=folder.parents[1]
    manifest=json.loads((folder/'free-surface-assets.json').read_text())
    destination=root/'.runtime/free-character-research/vitruvian'
    destination.mkdir(parents=True,exist_ok=True)
    repository=manifest['repository'].removeprefix('https://github.com/')
    def fetch(record):
        target=destination/record['local_file']
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=record['sha256']:
                raise ValueError('Existing source differs; preserved: '+target.name)
            return
        url=f"https://raw.githubusercontent.com/{repository}/{manifest['commit']}/{record['path']}"
        with urllib.request.urlopen(url,timeout=60) as response:
            data=response.read(record['bytes']+1)
        if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:
            raise ValueError('Downloaded source checksum mismatch: '+record['local_file'])
        target.write_bytes(data)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(fetch,manifest['files']))
    (destination/'source-manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Verified free source data:',len(manifest['files']),'files at',manifest['commit'])


if __name__=='__main__': main()
