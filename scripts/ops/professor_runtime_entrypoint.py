#!/usr/bin/env python3
"""Stage 2 API startup/validation boundary. Output contains fixed categories only."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import resource
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from services.selfhost_secret_files import CORE, SecretRefused, install_log_redaction, runtime_environment


class SafeParser(argparse.ArgumentParser):
    def error(self, message): raise SecretRefused('invalid_arguments')


def main(argv=None):
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        parser = SafeParser(description=__doc__)
        parser.add_argument('operation', choices=('api', 'validate', 'health'), default='api', nargs='?')
        args = parser.parse_args(argv)
        environment = runtime_environment(Path('/run/secrets'), dict(os.environ))
        install_log_redaction([environment[name] for name in CORE.values()])
        os.environ.clear(); os.environ.update(environment)
        if args.operation == 'validate':
            print(json.dumps({'status': 'pass', 'profile': 'local', 'core_files': 5,
                'guards': 'disabled_operations_preserved', 'values_returned': False})); return 0
        if args.operation == 'health':
            from scripts.ops.selfhost_runtime import health
            print(json.dumps(health(Path('/run/secrets')))); return 0
        # Stay in-process so the redaction boundary survives Uvicorn logging setup.
        import uvicorn
        uvicorn.run('backend.api_main:app', host='0.0.0.0', port=8080, proxy_headers=False)
        return 0
    except SecretRefused as error:
        print(json.dumps({'status': 'refused', 'reason_code': str(error)})); return 1
    except (Exception, KeyboardInterrupt):
        print(json.dumps({'status': 'refused', 'reason_code': 'startup_failed_details_suppressed'})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
