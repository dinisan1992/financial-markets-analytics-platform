from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_sqlalchemy_database_url
from services.euro_direct_debits_remediation_service import (
    build_direct_debits_rebuild_plan,
    write_direct_debits_rebuild_plan,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create a read-only Direct Debits shadow-rebuild plan. "
            "This command cannot build, swap or modify a database table."
        )
    )
    parser.add_argument(
        "--suffix",
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "euro_direct_debits",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        plan = build_direct_debits_rebuild_plan(engine, args.suffix)
    finally:
        engine.dispose()
    report = write_direct_debits_rebuild_plan(args.output_dir, plan)

    print(json.dumps(plan, indent=2, ensure_ascii=True, default=str))
    print("Database writes: disabled")
    print("Write path enabled: False")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
