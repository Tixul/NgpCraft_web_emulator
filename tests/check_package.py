"""Validate tracked artifacts and the optional release archive."""
from pathlib import Path
import hashlib
import json
import zipfile
root = Path(__file__).resolve().parents[1]
public = root / 'public'
manifest = json.loads((public / 'build-info.json').read_text(encoding='utf-8'))
files = {p.name for p in public.iterdir() if p.is_file()}
assert files == set(manifest['files']) | {'build-info.json'}
assert not any(Path(n).suffix.lower() in {'.ngc', '.ngp', '.npc', '.bin', '.rom'} for n in files)
for name, meta in manifest['files'].items():
    data = (public / name).read_bytes()
    assert len(data) == meta['bytes'], name
    assert hashlib.sha256(data).hexdigest() == meta['sha256'], name
assert (root / 'LICENSE').read_bytes() == (public / 'LICENSE.txt').read_bytes()
assert 'Copyright (c) 2026 Tixul' in (root / 'LICENSE').read_text()
archive_path = root / 'dist/NgpCraft-Web-Player.zip'
if archive_path.exists():
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        docs = {'README.md', 'VERIFICATION.md', 'INTEGRATION.md'}
        assert set(archive.namelist()) == files | docs
        for name in files | docs:
            original = root / name if name in docs else public / name
            assert archive.read(name) == original.read_bytes(), name
    print('PASS: ZIP matches public files and documentation')
print('PASS: manifest hashes, MIT attribution and ROM-free distribution')
