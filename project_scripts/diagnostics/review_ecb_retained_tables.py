from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_sqlalchemy_database_url
from services.ecb_retention_review_service import review_ecb_retained_tables


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Review retained ECB rollback tables through SELECT-only access. "
            "This command cannot delete or modify a table."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "ecb_retention_review_v088",
    )
    return parser


def write_report(output_dir, payload):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    complete = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    encoded = json.dumps(
        complete,
        indent=2,
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    path = output_dir / "ecb_retained_table_review.json"
    path.write_bytes(encoded)
    digest = sha256(encoded).hexdigest().upper()
    path.with_suffix(".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="ascii",
    )
    return path, digest


def main(argv=None):
    args = build_parser().parse_args(argv)
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        payload = review_ecb_retained_tables(engine)
    finally:
        engine.dispose()
    report, digest = write_report(args.output_dir, payload)
    for contract in payload["contracts"]:
        retained = contract["retained_evidence"]
        rows = retained["exact_rows"] if retained else "missing"
        print(
            f"{contract['import_key']}: {contract['status']} | "
            f"retained_rows={rows}"
        )
    print(f"Database writes: {payload['database_write_performed']}")
    print(f"Tables deleted: {payload['table_deleted']}")
    print(f"Report: {report}")
    print(f"SHA-256: {digest}")
    return 0 if payload["summary"]["all_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
