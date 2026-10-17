"""Read-only ML-2 guard. A self-asserted PASS file cannot authorize training."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import zipfile

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'scripts.ml'

from . import reopen_data_gate as gate


def authorized(frozen: Path, bundle: Path | None = None) -> bool:
    try:
        frozen = gate.private_root(frozen)
        if bundle is None:
            return False
        report, private = gate.rebuild(bundle)
        if report['status'] != 'PASS' or report['ml_b_authorized'] is not True:
            return False
        expected = gate.artifacts(report, private)
        return ({p.name for p in frozen.iterdir()} == set(expected)
                and all((frozen/key).is_file() and not (frozen/key).is_symlink()
                        and (frozen/key).read_bytes() == value for key, value in expected.items()))
    except (OSError, ValueError, KeyError, TypeError, OverflowError, zipfile.BadZipFile):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen', required=True, type=Path)
    parser.add_argument('--bundle', required=True, type=Path)
    args = parser.parse_args()
    passed = authorized(args.frozen, args.bundle)
    print('PASS' if passed else 'BLOCKED')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
