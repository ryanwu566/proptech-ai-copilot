#!/usr/bin/env python3
"""Read-only streaming inventory; never copy datasets or follow symlinks.

Use --hash-mode all on /srv/proptech-data/DB for the acceptance inventory.
The metadata mode is for reference inspection, not an integrity attestation.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path


def inventory(root: Path, *, hash_mode: str = 'all') -> dict:
    root = root.resolve(strict=True)
    # An explicit probe prevents os.walk from treating inaccessible data as empty.
    with os.scandir(root):
        pass
    files = []
    categories = defaultdict(lambda: {'files': 0, 'bytes': 0})
    def fail(error):
        raise error
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=fail):
        dirs.sort()
        for name in dirs[:]:
            path = Path(directory) / name
            if path.is_symlink():
                files.append({'path': str(path.relative_to(root)), 'type': 'symlink', 'hashed': False})
                dirs.remove(name)
        for name in sorted(names):
            path = Path(directory) / name
            relative = path.relative_to(root)
            if path.is_symlink():
                files.append({'path': str(relative), 'type': 'symlink', 'hashed': False})
                continue
            size = path.stat().st_size
            entry = {'path': str(relative), 'bytes': size}
            categories[relative.parts[0]]['files'] += 1
            categories[relative.parts[0]]['bytes'] += size
            do_hash = hash_mode == 'all' or (hash_mode == 'manifests' and (
                'manifest' in name.lower() or 'processed' in relative.parts))
            if do_hash:
                digest = hashlib.sha256()
                with path.open('rb') as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        digest.update(chunk)
                entry['sha256'] = digest.hexdigest()
            files.append(entry)
    return {'schema': 'professor-dataset-inventory-v1', 'root': str(root),
            'created_at': datetime.now(timezone.utc).isoformat(), 'hash_mode': hash_mode,
            'file_count': sum(c['files'] for c in categories.values()),
            'total_bytes': sum(c['bytes'] for c in categories.values()),
            'categories': dict(categories), 'files': files}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/srv/proptech-data/DB'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--hash-mode', choices=['all', 'manifests', 'metadata'], default='all')
    args = parser.parse_args()
    result = inventory(args.root, hash_mode=args.hash_mode)
    # Keep output outside the source tree, including for read-only source mounts.
    if args.output.resolve().is_relative_to(args.root.resolve()):
        parser.error('output must be outside the dataset root')
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, ensure_ascii=False))
