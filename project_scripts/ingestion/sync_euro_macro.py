from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_sqlalchemy_database_url
from macro_import_manifest import get_macro_import_keys
from services.euro_sync_service import (
    apply_euro_sync,
    build_euro_sync_plan,
    sync_confirmation,
)


EURO_IMPORT_KEYS = tuple(get_macro_import_keys("EURO"))


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Plan one memory-bounded EURO source synchronization. "
            "SQL writes require --apply, a scoped backup and exact confirmation."
        )
    )
    parser.add_argument("import_key", choices=EURO_IMPORT_KEYS)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-file")
    parser.add_argument("--confirm")
    parser.add_argument("--chunk-size", type=int, default=25_000)
    parser.add_argument("--insert-batch-size", type=int, default=250)
    parser.add_argument("--workspace-dir", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "euro_sync",
    )
    parser.add_argument("--fail-on-blocker", action="store_true")
    return parser


def _write_report(output_dir, import_key, payload):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{import_key.lower()}_sync_{timestamp}.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return path


def _progress_reporter():
    last_reported = {}

    def report(stage, import_key, rows):
        marker = (stage, import_key)
        previous = last_reported.get(marker, 0)
        if rows - previous >= 250_000:
            print(f"  {import_key} {stage}: {rows:,} rows", flush=True)
            last_reported[marker] = rows

    return report


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be positive")
    if args.insert_batch_size < 1:
        raise SystemExit("--insert-batch-size must be positive")
    if args.apply and (not args.backup_file or not args.confirm):
        raise SystemExit("--apply requires --backup-file and --confirm")

    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    progress = _progress_reporter()
    try:
        if args.apply:
            print("EURO transactional synchronization: write mode requested")
            result = apply_euro_sync(
                engine,
                args.import_key,
                backup_file=args.backup_file,
                confirmation=args.confirm,
                chunk_size=args.chunk_size,
                insert_batch_size=args.insert_batch_size,
                workspace_dir=args.workspace_dir,
                progress_callback=progress,
            )
            payload = {
                "stage": "apply",
                "import_key": args.import_key,
                **result,
            }
            exit_code = 0
        else:
            print("EURO transactional synchronization plan")
            print("Database writes: disabled")
            plan = build_euro_sync_plan(
                engine,
                args.import_key,
                chunk_size=args.chunk_size,
                workspace_dir=args.workspace_dir,
                progress_callback=progress,
            )
            payload = {
                "stage": "plan",
                "import_key": args.import_key,
                "required_confirmation": sync_confirmation(args.import_key),
                "plan": plan.to_dict(),
                "database_write_performed": False,
            }
            exit_code = 2 if args.fail_on_blocker and not plan.write_ready else 0
    finally:
        engine.dispose()

    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    report = _write_report(args.output_dir, args.import_key, payload)
    print(f"Report: {report}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
