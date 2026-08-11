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
from services.euro_direct_debits_shadow_service import (
    BUILD_DIRECT_DEBITS_CONFIRMATION,
    build_direct_debits_shadow,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Build and fully validate the versioned Direct Debits shadow. "
            "This command cannot swap or modify the active table."
        )
    )
    parser.add_argument("--backup-file", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument(
        "--suffix",
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--chunk-size", type=int, default=25_000)
    parser.add_argument("--insert-batch-size", type=int, default=250)
    parser.add_argument("--workspace-dir", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "euro_direct_debits_v069",
    )
    return parser


def _report_payload(result, suffix):
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "shadow_build",
        "version": result["version"],
        "suffix": suffix,
        "import_key": result["import_key"],
        "source": {
            **result["source"],
            "path": str(result["source"]["path"]),
        },
        "backup": {
            **result["backup"],
            "path": str(result["backup"]["path"]),
        },
        "shadow_table": result["shadow_table"],
        "shadow_evidence": result["shadow_evidence"],
        "validations": [
            validation.to_dict() for validation in result["validations"]
        ],
        "active_before": result["active_before"],
        "active_after": result["active_after"],
        "database_write_scope": "versioned_shadow_table_only",
        "database_write_performed": result["database_write_performed"],
        "active_table_changed": result["active_table_changed"],
        "shadow_ready_for_swap_review": result["shadow_ready_for_swap_review"],
        "swap_authorized": result["swap_authorized"],
        "swap_performed": result["swap_performed"],
    }


def write_report(output_dir, suffix, payload):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"euro_direct_debits_shadow_build_{suffix}.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, default=str),
        encoding="utf-8",
    )
    return path


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be positive")
    if args.insert_batch_size < 1:
        raise SystemExit("--insert-batch-size must be positive")
    if args.confirm != BUILD_DIRECT_DEBITS_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {BUILD_DIRECT_DEBITS_CONFIRMATION}"
        )
    if args.workspace_dir is not None:
        args.workspace_dir = args.workspace_dir.expanduser().resolve()
        args.workspace_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        result = build_direct_debits_shadow(
            engine=engine,
            backup_file=args.backup_file,
            confirmation=args.confirm,
            suffix=args.suffix,
            chunk_size=args.chunk_size,
            insert_batch_size=args.insert_batch_size,
            workspace_dir=args.workspace_dir,
        )
    finally:
        engine.dispose()

    payload = _report_payload(result, args.suffix)
    report = write_report(args.output_dir, args.suffix, payload)
    validation = result["validations"][0]
    print(f"Shadow table: {result['shadow_table']}")
    print(f"Rows: {validation.shadow_rows}")
    print(f"Valid: {validation.valid}")
    print(f"Active table changed: {result['active_table_changed']}")
    print("Swap authorized: False")
    print("Swap performed: False")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
