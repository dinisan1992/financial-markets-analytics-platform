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
from services.euro_direct_debits_swap_service import (
    SWAP_DIRECT_DEBITS_CONFIRMATION,
    swap_direct_debits_active,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Atomically retain the active Direct Debits table and promote the "
            "validated v0.6.9 shadow. Automatic rollback is enabled."
        )
    )
    parser.add_argument("--backup-file", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--suffix", required=True)
    parser.add_argument("--chunk-size", type=int, default=25_000)
    parser.add_argument("--workspace-dir", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "euro_direct_debits_v070",
    )
    return parser


def report_payload(result, suffix):
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "atomic_swap",
        "version": result["version"],
        "shadow_version": result["shadow_version"],
        "suffix": suffix,
        "import_key": result["import_key"],
        "source": {**result["source"], "path": str(result["source"]["path"])},
        "backup": {**result["backup"], "path": str(result["backup"]["path"])},
        "validations": [
            validation.to_dict() for validation in result["validations"]
        ],
        "active_before": result["active_before"],
        "active_after": result["active_after"],
        "retained_table": result["retained_table"],
        "retained_checkpoint": result["retained_checkpoint"],
        "promoted_with_hash_evidence": result["promoted_with_hash_evidence"],
        "final_active_evidence": result["final_active_evidence"],
        "swap_statement": result["swap_statement"],
        "rollback_statement": result["rollback_statement"],
        "hash_column_drop_stage": result["hash_column_drop_stage"],
        "database_write_performed": result["database_write_performed"],
        "active_table_changed": result["active_table_changed"],
        "swap_authorized": result["swap_authorized"],
        "swap_performed": result["swap_performed"],
        "rollback_performed": result["rollback_performed"],
    }


def write_report(output_dir, suffix, payload):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"euro_direct_debits_atomic_swap_{suffix}.json"
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, default=str),
        encoding="utf-8",
    )
    return path


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be positive")
    if args.confirm != SWAP_DIRECT_DEBITS_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {SWAP_DIRECT_DEBITS_CONFIRMATION}"
        )
    if args.workspace_dir is not None:
        args.workspace_dir = args.workspace_dir.expanduser().resolve()
        args.workspace_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        result = swap_direct_debits_active(
            engine=engine,
            backup_file=args.backup_file,
            confirmation=args.confirm,
            suffix=args.suffix,
            chunk_size=args.chunk_size,
            workspace_dir=args.workspace_dir,
        )
    finally:
        engine.dispose()

    payload = report_payload(result, args.suffix)
    report = write_report(args.output_dir, args.suffix, payload)
    print(f"Active table: {result['validations'][0].active_table}")
    print(f"Rows: {result['final_active_evidence']['rows']}")
    print(f"Retained table: {result['retained_table']}")
    print(f"Swap performed: {result['swap_performed']}")
    print(f"Rollback performed: {result['rollback_performed']}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
