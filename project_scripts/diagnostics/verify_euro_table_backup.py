from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_sqlalchemy_database_url
from macro_import_manifest import get_macro_import_keys
from services.euro_backup_restore_service import (
    verification_confirmation,
    verify_euro_backup_restore,
    write_backup_restore_report,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Restore one EURO backup into a generated isolated schema, compare "
            "it with the active table and remove the isolated schema."
        )
    )
    parser.add_argument("import_key", choices=get_macro_import_keys("EURO"))
    parser.add_argument("--backup-file", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--mysql")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "euro_backup_restore",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    expected = verification_confirmation(args.import_key)
    if args.confirm != expected:
        raise ValueError(f"--confirm must exactly match {expected}")
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        report = verify_euro_backup_restore(
            engine,
            args.import_key,
            args.backup_file,
            args.confirm,
            mysql_path=args.mysql,
        )
    finally:
        engine.dispose()
    report_path = write_backup_restore_report(args.output_dir, report)
    print(json.dumps(report, indent=2, ensure_ascii=True, default=str))
    print("Active database writes: disabled")
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
