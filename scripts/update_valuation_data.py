"""Skeleton for a scheduled valuation-data updater.

This command intentionally does not download or clean full Taiwan datasets in
the web-service runtime. A reviewed GitHub Actions or backend scheduler should
provide a local ZIP and external database destination in the future.
"""

from __future__ import annotations

import argparse
from pathlib import Path


RUNTIME_WARNING = "正式更新請由 GitHub Actions 或後台排程執行，不應在 Render runtime 執行。"


def build_parser() -> argparse.ArgumentParser:
    """Build the future updater command interface."""

    parser = argparse.ArgumentParser(description="Valuation data updater skeleton")
    parser.add_argument("--local-zip", type=Path, help="Future local official OpenData ZIP input")
    parser.add_argument("--database-url", help="Future Supabase/Postgres destination; do not commit credentials")
    parser.add_argument("--dry-run", action="store_true", help="Show intended actions without writing data")
    return parser


def main() -> int:
    """Print safe next steps without downloading or importing a large dataset."""

    args = build_parser().parse_args()
    print(RUNTIME_WARNING)
    if args.local_zip:
        print(f"Local ZIP input configured: {args.local_zip}")
        print("ZIP normalization and database upsert are placeholders and have not been enabled.")
    else:
        print("No local ZIP supplied. Automatic official-data download is intentionally disabled.")
    if args.database_url:
        print("External database destination configured through runtime arguments.")
    else:
        print("No external database destination configured.")
    print("Dry run complete." if args.dry_run else "No data was downloaded or written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
