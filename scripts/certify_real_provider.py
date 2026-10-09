"""Safe compatibility entrypoint for the existing bounded acceptance runner.

Default is config-only. Live certification requires explicit owner opt-in,
confirmed environment and a one-request budget. No import-time transmission.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.provider_acceptance import main

if __name__ == "__main__":
    raise SystemExit(main())
