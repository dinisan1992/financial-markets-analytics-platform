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
    build_ecb_shadow,
)
from services.ecb_shadow_readiness_service import (
    build_confirmation,
    file_sha256,
    load_json,
    pinned_plans,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Build and completely validate one authorized ECB shadow. "
            "This command has no swap or active-table promotion mode."
        )
    )
    parser.add_argument("import_key", choices=BUILDABLE_IMPORT_KEYS)
    parser.add_argument("--readiness-report", type=Path, required=True)
    parser.add_argument("--readiness-sha256", required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--pin-file", type=Path, required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--chunk-size", type=int, default=25_000)
    parser.add_argument("--insert-batch-size", type=int, default=500)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "ecb_shadow_build_v079",
    )
    return parser


def _audit_path(audit_dir, import_key):
    return Path(audit_dir) / f"{import_key.lower()}.json"


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
        f"{payload['import_key'].lower()}_shadow_build_"
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
    if args.insert_batch_size < 1:
        raise SystemExit("--insert-batch-size must be positive")
    expected_confirmation = build_confirmation(args.import_key)
    if args.confirm != expected_confirmation:
        raise ValueError(
            f"--confirm must exactly match {expected_confirmation}"
        )

    readiness_report = args.readiness_report.expanduser().resolve()
    actual_readiness_sha256 = file_sha256(readiness_report)
    if actual_readiness_sha256 != args.readiness_sha256.upper():
        raise ValueError("Readiness report SHA-256 mismatch")
    staging_dir = args.staging_dir.expanduser().resolve()
    backup_dir = args.backup_dir.expanduser().resolve()
    audit_dir = args.audit_dir.expanduser().resolve()
    workspace_dir = args.workspace_dir.expanduser().resolve()
    for path in (staging_dir, backup_dir, audit_dir, workspace_dir):
        if not path.is_dir():
            raise FileNotFoundError(f"Required ECB directory not found: {path}")
    pin_file = args.pin_file.expanduser().resolve()
    pin = pinned_plans(load_json(pin_file))[args.import_key]
    audit_payload = load_json(_audit_path(audit_dir, args.import_key))

    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        result = build_ecb_shadow(
            engine,
            args.import_key,
            confirmation=args.confirm,
            readiness_payload=load_json(readiness_report),
            pin=pin,
            audit_payload=audit_payload,
            staging_dir=staging_dir,
            backup_dir=backup_dir,
            workspace_dir=workspace_dir,
            chunk_size=args.chunk_size,
            insert_batch_size=args.insert_batch_size,
        )
    finally:
        engine.dispose()

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "shadow_build",
        **result,
        "readiness_report_file": readiness_report.name,
        "readiness_report_sha256": actual_readiness_sha256,
        "database_write_scope": "versioned_shadow_table_only",
    }
    report, digest = _write_report(args.output_dir, payload)
    print(f"Shadow table: {result['shadow_table']}")
    print(f"Rows: {result['initial_validation']['shadow_rows']:,}")
    print(f"Initial validation: {result['initial_validation']['valid']}")
    print(f"Repeated validation: {result['repeated_validation']['valid']}")
    print(f"Active table changed: {result['active_table_changed']}")
    print("Swap authorized: False")
    print("Swap performed: False")
    print(f"Report: {report}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
