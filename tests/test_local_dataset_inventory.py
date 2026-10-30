import hashlib

from scripts.ops.inventory_local_datasets import inventory


def test_inventory_records_symlink_directories_without_traversing(tmp_path):
    root = tmp_path / 'datasets'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'private.txt').write_text('not part of dataset')
    (root / 'linked').symlink_to(outside, target_is_directory=True)
    (root / 'file.txt').write_bytes(b'data')
    result = inventory(root)
    assert result['file_count'] == 1
    assert result['total_bytes'] == 4
    assert {'path': 'linked', 'type': 'symlink', 'hashed': False} in result['files']
    entry = next(item for item in result['files'] if item['path'] == 'file.txt')
    assert entry['sha256'] == hashlib.sha256(b'data').hexdigest()
    assert not any('private.txt' in item['path'] for item in result['files'])
