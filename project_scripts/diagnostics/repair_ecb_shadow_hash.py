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
from services.ecb_shadow_build_service import (
    BUILDABLE_IMPORT_KEYS,
    active_table_checkpoint,
    repair_confirmation,
    repair_shadow_storage_hash,
    shadow_table_evidence,
    validate_readiness_report,
)
from services.ecb_shadow_readiness_service import (
    PLAN_VERSION,
    file_sha256,
    load_json,
)
from services.euro_rebuild_service import validate_existing_shadows


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Repair one representation-equivalent technical hash in an ECB "
            "shadow, then validate the complete shadow twice. No swap exists."
        )
    )
    parser.add_argument("import_key", choices=BUILDABLE_IMPORT_KEYS)
    parser.add_argument("--readiness-report", type=Path, required=True)
    parser.add_argument("--readiness-sha256", required=True)
    parser.add_argument("--source-file", type=Path, required=True)
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--key-code", required=True)
    parser.add_argument("--time-period", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--chunk-size", type=int, default=25_000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "ecb_shadow_build_v079",
    )
    return parser


def _write_report(output_dir, payload):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        payload,
        indent=2,
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    path = output_dir / (
        f"{payload['import_key'].lower()}_shadow_repair_"
        f"{payload['suffix']}.json"
    )
    path.write_bytes(encoded)
    digest = sha256(encoded).hexdigest().upper()
    path.with_suffix(".sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="ascii",
    )
    return path, digest


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be positive")
    expected_confirmation = repair_confirmation(args.import_key)
    if args.confirm != expected_confirmation:
        raise ValueError(
            f"--confirm must exactly match {expected_confirmation}"
        )
    readiness_report = args.readiness_report.expanduser().resolve()
    readiness_sha256 = file_sha256(readiness_report)
    if readiness_sha256 != args.readiness_sha256.upper():
        raise ValueError("Readiness report SHA-256 mismatch")
    readiness_payload = load_json(readiness_report)
    suffix, plan = validate_readiness_report(
        readiness_payload,
        args.import_key,
    )
    shadow_table = plan["planned_names"]["shadow_table"]
    source_path = args.source_file.expanduser().resolve()
    workspace_dir = args.workspace_dir.expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"ECB source file not found: {source_path}")
    if not workspace_dir.is_dir():
        raise FileNotFoundError(f"ECB workspace not found: {workspace_dir}")

    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        active_before = active_table_checkpoint(engine, args.import_key)
        repair = repair_shadow_storage_hash(
            engine,
            args.import_key,
            shadow_table,
            source_path,
            args.key_code,
            args.time_period,
            confirmation=args.confirm,
        )
        validation_kwargs = {
            "version": PLAN_VERSION,
            "memory_bounded": True,
            "workspace_dir": workspace_dir,
            "source_path_overrides": {args.import_key: source_path},
        }
        first = validate_existing_shadows(
            engine,
            suffix,
            args.chunk_size,
            (args.import_key,),
            **validation_kwargs,
        )[0]
        second = validate_existing_shadows(
            engine,
            suffix,
            args.chunk_size,
            (args.import_key,),
            **validation_kwargs,
        )[0]
        evidence = shadow_table_evidence(engine, shadow_table)
        active_after = active_table_checkpoint(engine, args.import_key)
    finally:
        engine.dispose()
    if active_after != active_before:
        raise RuntimeError("Active ECB table changed during shadow hash repair")

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "shadow_hash_repair_and_validation",
        "version": PLAN_VERSION,
        "import_key": args.import_key,
        "suffix": suffix,
        "shadow_table": shadow_table,
        "repair": repair,
        "first_validation": first.to_dict(),
        "second_validation": second.to_dict(),
        "shadow_evidence": evidence,
        "active_before": active_before,
        "active_after": active_after,
        "active_table_changed": False,
        "shadow_ready_for_swap_review": True,
        "swap_authorized": False,
        "swap_performed": False,
        "readiness_report_file": readiness_report.name,
        "readiness_report_sha256": readiness_sha256,
    }
    report, digest = _write_report(args.output_dir, payload)
    print(f"Shadow table: {shadow_table}")
    print(f"Technical hashes repaired: {repair['rows_updated']}")
    print(f"Rows: {first.shadow_rows:,}")
    print(f"First validation: {first.valid}")
    print(f"Second validation: {second.valid}")
    print("Active table changed: False")
    print("Swap authorized: False")
    print("Swap performed: False")
    print(f"Report: {report}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
