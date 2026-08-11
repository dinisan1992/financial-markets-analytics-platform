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
from services.euro_direct_debits_diagnostic_service import (
    diagnose_euro_direct_debits,
    write_direct_debits_diagnostic,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose Direct Debits period-key differences using SELECT only. "
            "This command has no database write mode."
        )
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
        diagnostic = diagnose_euro_direct_debits(engine)
    finally:
        engine.dispose()
    outputs = write_direct_debits_diagnostic(args.output_dir, diagnostic)

    print(json.dumps(diagnostic["summary"], indent=2, ensure_ascii=True))
    print(diagnostic["frequency_alignment"].to_string(index=False))
    print("Database writes: disabled")
    for label, path in outputs.items():
        print(f"{label}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
