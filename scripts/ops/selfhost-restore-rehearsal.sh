#!/usr/bin/env bash
set -euo pipefail
umask 077
exec python3 "$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/ops_backup_tools.py" restore "$@"
