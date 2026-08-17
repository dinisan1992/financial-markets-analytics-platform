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
from services.ecb_pcp_swap_service import preflight_pcp_swap
from services.ecb_shadow_readiness_service import file_sha256, load_json


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Revalidate the complete PCP promotion evidence without changing "
            "the database or active CSV."
        )
    )
    parser.add_argument("--readiness-report", type=Path, required=True)
    parser.add_argument("--readiness-sha256", required=True)
    parser.add_argument("--build-report", type=Path, required=True)
    parser.add_argument("--build-sha256", required=True)
    parser.add_argument("--verification-report", type=Path, required=True)
    parser.add_argument("--verification-sha256", required=True)
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--chunk-size", type=int, default=25_000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "ecb_pcp_swap_preflight_v083",
    )
    return parser


def _verified_payload(path, expected_sha256, label):
    path = path.expanduser().resolve()
    actual_sha256 = file_sha256(path)
    if actual_sha256 != expected_sha256.upper():
        raise ValueError(f"{label} SHA-256 mismatch")
    return path, actual_sha256, load_json(path)


def _write_report(output_dir, payload):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        payload,
        indent=2,
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    path = output_dir / "euro_card_payments_swap_preflight.json"
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
    readiness_path, readiness_sha256, readiness_payload = _verified_payload(
        args.readiness_report,
        args.readiness_sha256,
        "Readiness report",
    )
    build_path, build_sha256, build_payload = _verified_payload(
        args.build_report,
        args.build_sha256,
        "PCP build report",
    )
    verification_path, verification_sha256, verification_payload = (
        _verified_payload(
            args.verification_report,
            args.verification_sha256,
            "PCP post-build verification report",
        )
    )
    staging_dir = args.staging_dir.expanduser().resolve()
    backup_dir = args.backup_dir.expanduser().resolve()
    workspace_dir = args.workspace_dir.expanduser().resolve()
    for path in (staging_dir, backup_dir, workspace_dir):
        if not path.is_dir():
            raise FileNotFoundError(f"Required PCP directory not found: {path}")

    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        result = preflight_pcp_swap(
            engine,
            readiness_payload=readiness_payload,
            build_payload=build_payload,
            post_build_payload=verification_payload,
            readiness_report_file=readiness_path.name,
            readiness_report_sha256=readiness_sha256,
            build_report_file=build_path.name,
            build_report_sha256=build_sha256,
            staging_dir=staging_dir,
            backup_dir=backup_dir,
            workspace_dir=workspace_dir,
            chunk_size=args.chunk_size,
        )
    finally:
        engine.dispose()

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        **result,
        "readiness_report_file": readiness_path.name,
        "readiness_report_sha256": readiness_sha256,
        "build_report_file": build_path.name,
        "build_report_sha256": build_sha256,
        "post_build_verification_file": verification_path.name,
        "post_build_verification_sha256": verification_sha256,
    }
    report, digest = _write_report(args.output_dir, payload)
    validation = result["shadow_validation"]
    print(f"Active table: {result['active_table']}")
    print(f"Active rows: {result['active_checkpoint']['data']['rows']:,}")
    print(f"Shadow table: {result['shadow_table']}")
    print(f"Shadow rows: {validation['shadow_rows']:,}")
    print(f"Source-to-shadow valid: {validation['valid']}")
    print("Database write performed: False")
    print("Swap authorized: False")
    print("Swap performed: False")
    print(f"Report: {report}")
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
