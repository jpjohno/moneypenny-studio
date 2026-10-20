"""Owner-maintained profiles. A saved profile never implies tracking access."""
import json
import os
import uuid
from pathlib import Path

KINDS = {'person', 'pet', 'vehicle', 'place', 'device'}
DEFAULTS = [
    {'id': 'kit-bmw', 'name': 'Kit · BMW', 'kind': 'vehicle', 'connection': 'bmw', 'note': 'Review the BMW connection for dated vehicle reports.'},
    {'id': 'enkidu', 'name': 'Enkidu', 'kind': 'pet', 'connection': '', 'note': 'Add a paired tracker or review Find My. No location source is attached.'},
]

class AssetProfiles:
    def __init__(self, path):
        self.path = Path(path)

    def read(self):
        if not self.path.exists():
            return [dict(item) for item in DEFAULTS]
        if self.path.is_symlink():
            raise ValueError('Profile storage must be a regular file')
        data = json.loads(self.path.read_text())
        if not isinstance(data, list):
            raise ValueError('Profile storage needs checking')
        return data

    def list(self):
        return {'state': 'saved_profiles', 'assets': [{**item, 'location_state': 'unavailable', 'tracking_enabled': False} for item in self.read()]}

    def add(self, value):
        name = str(value.get('name', '')).strip()
        kind = value.get('kind')
        if not name or len(name) > 80 or any(ord(c) < 32 for c in name) or kind not in KINDS:
            raise ValueError('Enter a name and choose a supported profile type')
        rows = self.read()
        if len(rows) >= 100:
            raise ValueError('Up to 100 profiles can be saved')
        if any(item['name'].casefold() == name.casefold() for item in rows):
            raise ValueError('That name is already saved')
        rows.append({'id': uuid.uuid4().hex, 'name': name, 'kind': kind, 'connection': '', 'note': 'Saved profile. Pair a device or connect a supported source to receive reports.'})
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(rows, stream)
        temporary.replace(self.path)
        return self.list()
