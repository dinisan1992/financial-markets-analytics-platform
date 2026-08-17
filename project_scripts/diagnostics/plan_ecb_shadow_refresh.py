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
from services.ecb_shadow_readiness_service import (
    ECB_IMPORT_KEYS,
    PLAN_VERSION,
    build_ecb_shadow_readiness,
    file_sha256,
    load_json,
    pinned_plans,
    validate_ecb_import_key,
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Create a SELECT-only ECB shadow-readiness plan. This command has "
            "no build, apply or swap mode."
        )
    )
    parser.add_argument("import_keys", nargs="*", metavar="IMPORT_KEY")
    parser.add_argument("--staging-dir", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--workspace-dir", type=Path, required=True)
    parser.add_argument("--pin-file", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "ecb_shadow_readiness_v079",
    )
    parser.add_argument("--suffix", default=None)
    parser.add_argument("--operating-reserve-gb", type=float, default=5.0)
    args = parser.parse_args(argv)
    args.import_keys = args.import_keys or list(ECB_IMPORT_KEYS)
    args.import_keys = [validate_ecb_import_key(key) for key in args.import_keys]
    if args.suffix is None:
        args.suffix = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return args


def _audit_path(audit_dir, import_key):
    return Path(audit_dir) / f"{import_key.lower()}.json"


def _write_summary(output_dir, payload):
    output_dir.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        payload,
        indent=2,
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    path = output_dir / "shadow_readiness_summary.json"
    path.write_bytes(encoded)
    digest = sha256(encoded).hexdigest().upper()
    (output_dir / "shadow_readiness_summary.sha256").write_text(
        f"{digest}  {path.name}\n",
        encoding="ascii",
    )
    return path, digest


def main(argv=None):
    args = parse_args(argv)
    staging_dir = args.staging_dir.expanduser().resolve()
    backup_dir = args.backup_dir.expanduser().resolve()
    audit_dir = args.audit_dir.expanduser().resolve()
    workspace_dir = args.workspace_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    for path in (staging_dir, backup_dir, audit_dir, workspace_dir):
        if not path.is_dir():
            raise FileNotFoundError(f"Required ECB directory not found: {path}")
    pin_file = args.pin_file.expanduser().resolve()
    pins = pinned_plans(load_json(pin_file))
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    plans = []
    errors = []
    try:
        for import_key in args.import_keys:
            print(f"ECB shadow readiness: {import_key}", flush=True)
            try:
                plan = build_ecb_shadow_readiness(
                    engine,
                    import_key,
                    pin=pins[import_key],
                    audit_payload=load_json(_audit_path(audit_dir, import_key)),
                    staging_dir=staging_dir,
                    backup_dir=backup_dir,
                    workspace_dir=workspace_dir,
                    suffix=args.suffix,
                    operating_reserve_bytes=int(
                        max(0.0, args.operating_reserve_gb) * 1024**3
                    ),
                )
                plans.append(plan)
                print(
                    "  ready="
                    f"{plan['ready_for_shadow_build_authorization']} | "
                    f"blockers={len(plan['blockers'])} | "
                    f"capacity={plan['capacity']['capacity_pass']}",
                    flush=True,
                )
            except Exception as exc:
                errors.append(
                    {
                        "import_key": import_key,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "database_write_performed": False,
                    }
                )
                print(f"  ERROR: {type(exc).__name__}: {exc}", flush=True)
    finally:
        engine.dispose()
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_version": PLAN_VERSION,
        "suffix": args.suffix,
        "pin_manifest_file": pin_file.name,
        "pin_manifest_sha256": file_sha256(pin_file),
        "requested_imports": list(args.import_keys),
        "ready_count": sum(
            bool(plan["ready_for_shadow_build_authorization"])
            for plan in plans
        ),
        "error_count": len(errors),
        "plans": plans,
        "errors": errors,
        "database_write_performed": False,
        "active_csv_write_performed": False,
        "statements_executed": False,
    }
    report, digest = _write_summary(output_dir, payload)
    print(f"Report: {report}")
    print(f"SHA-256: {digest}")
    print("SQL writes: 0 | active CSV writes: 0")
    return 0 if not errors and payload["ready_count"] == len(args.import_keys) else 2


if __name__ == "__main__":
    raise SystemExit(main())
