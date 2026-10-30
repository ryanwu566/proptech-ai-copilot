"""Read-only object interface scoped to an operator-configured artifact root.

Only immutable runtime-generated keys are accepted. This is never a network
fallback and never accepts paths from an API request. Directory descriptors and
O_NOFOLLOW prevent symlink swaps between validation and reading (Linux runtime).
"""
from io import BytesIO
import os
from pathlib import Path, PurePosixPath


class LocalArtifactStore:
    def __init__(self, root: str | Path, prefix: str) -> None:
        path = Path(root)
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('local artifact root must be absolute without traversal')
        self.root = path
        self.prefix = prefix + '/'

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        del Bucket
        if not Key.startswith(self.prefix):
            raise ValueError('object outside configured artifact prefix')
        relative = PurePosixPath(Key[len(self.prefix):])
        if (relative.is_absolute() or len(relative.parts) != 2
                or any(part in {'.', '..'} for part in relative.parts)
                or relative.name not in {'manifest.json', 'features.json.gz'}):
            raise ValueError('invalid immutable artifact key')
        # Open each directory relative to its pinned parent. No component may
        # be a symlink, including the root. Replacements cannot redirect an fd.
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open('/', directory_flags)
        try:
            for component in (*self.root.parts[1:], *relative.parts[:-1]):
                next_fd = os.open(component, directory_flags, dir_fd=parent_fd)
                os.close(parent_fd)
                parent_fd = next_fd
            file_fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
        finally:
            os.close(parent_fd)
        # The deployment must additionally mount this root read-only. Bound
        # reads; manifests cannot require artifact-scale allocation.
        limit = 1024 * 1024 if relative.name == 'manifest.json' else 512 * 1024 * 1024
        with os.fdopen(file_fd, 'rb') as stream:
            import stat
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('local artifact is not a regular file')
            payload = stream.read(limit + 1)
        if len(payload) > limit:
            raise ValueError('local artifact exceeds runtime size limit')
        return {'Body': BytesIO(payload)}
