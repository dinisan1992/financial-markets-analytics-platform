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
from macro_import_manifest import get_macro_import
from services.euro_large_rebuild_service import (
    REBUILD_VERSION,
    TARGET_IMPORT_KEYS,
    build_confirmation,
    build_large_shadow,
    estimate_large_rebuild_capacity,
    swap_confirmation,
    swap_large_shadow,
)
from services.euro_rebuild_service import (
    build_rollback_statement,
    build_swap_statement,
    failed_table_name,
    retained_table_name,
    shadow_table_name,
)
from services.market_data_sync_service import validate_identifier


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Plan, build or swap one memory-bounded EURO shadow. "
            "The default plan does not connect to MySQL."
        )
    )
    parser.add_argument("import_key", choices=TARGET_IMPORT_KEYS)
    parser.add_argument(
        "--stage",
        choices=("plan", "preflight", "build", "swap"),
        default="plan",
    )
    parser.add_argument("--backup-file")
    parser.add_argument("--confirm")
    parser.add_argument(
        "--suffix",
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--chunk-size", type=int, default=50_000)
    parser.add_argument("--insert-batch-size", type=int, default=250)
    parser.add_argument("--workspace-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--operating-reserve-gb", type=float, default=5.0)
    return parser


def build_plan(import_key, suffix):
    contract = get_macro_import(import_key)
    active = contract["table_name"]
    import_keys = (import_key,)
    return {
        "stage": "plan",
        "version": REBUILD_VERSION,
        "import_key": import_key,
        "source_file": Path(contract["csv_path"]).name,
        "active_table": active,
        "shadow_table": shadow_table_name(active, suffix, REBUILD_VERSION),
        "retained_table": retained_table_name(active, suffix, REBUILD_VERSION),
        "failed_table": failed_table_name(active, suffix, REBUILD_VERSION),
        "build_confirmation": build_confirmation(import_key),
        "swap_confirmation": swap_confirmation(import_key),
        "swap_statement": build_swap_statement(
            import_keys,
            suffix,
            version=REBUILD_VERSION,
        ),
        "rollback_statement": build_rollback_statement(
            import_keys,
            suffix,
            version=REBUILD_VERSION,
        ),
        "backup_required": True,
        "memory_bounded_validation": True,
        "database_write_performed": False,
        "active_tables_changed": False,
    }


def print_plan(plan):
    print("EURO large-table rebuild plan")
    print("Database writes: disabled")
    print(f"Import: {plan['import_key']}")
    print(f"Source file: {plan['source_file']}")
    print(f"Active table: {plan['active_table']}")
    print(f"Shadow table: {plan['shadow_table']}")
    print(f"Retained table: {plan['retained_table']}")
    print(f"Failed table: {plan['failed_table']}")
    print(f"Build confirmation: {plan['build_confirmation']}")
    print(f"Swap confirmation: {plan['swap_confirmation']}")
    print(f"Swap statement: {plan['swap_statement']};")
    print(f"Rollback statement: {plan['rollback_statement']};")


def write_report(output_dir, stage, suffix, payload):
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    import_key = str(payload.get("import_key", "euro_large")).lower()
    path = output_dir / f"{import_key}_{stage}_{suffix}.json"
    path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def result_payload(stage, import_key, suffix, result):
    payload = {
        "stage": stage,
        "version": REBUILD_VERSION,
        "import_key": import_key,
        "suffix": suffix,
        "database_write_performed": result["database_write_performed"],
        "active_tables_changed": result["active_tables_changed"],
        "memory_bounded_validation": result["memory_bounded_validation"],
        "backup": {
            "path": str(result["backup"]["path"]),
            "bytes": result["backup"]["bytes"],
            "sha256": result["backup"]["sha256"],
            "tables": result["backup"]["tables"],
        },
        "validations": [
            validation.to_dict() for validation in result["validations"]
        ],
    }
    if stage == "swap":
        payload["final_summaries"] = result["final_summaries"]
        payload["rollback_statement"] = result["rollback_statement"]
        payload["retained_tables"] = result["retained_tables"]
    return payload


def main(argv=None):
    args = build_parser().parse_args(argv)
    validate_identifier(f"suffix_{args.suffix}")
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be positive")
    if args.insert_batch_size < 1:
        raise SystemExit("--insert-batch-size must be positive")
    if args.operating_reserve_gb < 0:
        raise SystemExit("--operating-reserve-gb cannot be negative")

    if args.stage == "plan":
        payload = build_plan(args.import_key, args.suffix)
        print_plan(payload)
        if args.output_dir:
            print(
                f"Report: {write_report(args.output_dir, 'plan', args.suffix, payload)}"
            )
        return 0

    if args.stage == "preflight":
        engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
        try:
            payload = estimate_large_rebuild_capacity(
                engine,
                args.import_key,
                workspace_dir=args.workspace_dir,
                operating_reserve_bytes=int(
                    args.operating_reserve_gb * 1024**3
                ),
            )
        finally:
            engine.dispose()
        print("EURO large-table capacity preflight")
        print("Database writes: disabled")
        print(json.dumps(payload, indent=2, default=str))
        if args.output_dir:
            report = write_report(
                args.output_dir,
                "preflight",
                args.suffix,
                payload,
            )
            print(f"Report: {report}")
        return 0 if payload["capacity_pass"] else 2

    if not args.backup_file or not args.confirm:
        raise SystemExit("--backup-file and --confirm are required")

    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        if args.stage == "build":
            result = build_large_shadow(
                engine=engine,
                import_key=args.import_key,
                backup_file=args.backup_file,
                confirmation=args.confirm,
                suffix=args.suffix,
                chunk_size=args.chunk_size,
                insert_batch_size=args.insert_batch_size,
                workspace_dir=args.workspace_dir,
            )
        else:
            result = swap_large_shadow(
                engine=engine,
                import_key=args.import_key,
                backup_file=args.backup_file,
                confirmation=args.confirm,
                suffix=args.suffix,
                chunk_size=args.chunk_size,
                workspace_dir=args.workspace_dir,
            )
    finally:
        engine.dispose()

    payload = result_payload(
        args.stage,
        args.import_key,
        args.suffix,
        result,
    )
    print(f"Stage: {args.stage}")
    print(f"Database writes: {result['database_write_performed']}")
    print(f"Active tables changed: {result['active_tables_changed']}")
    print(f"Backup SHA-256: {result['backup']['sha256']}")
    for validation in result["validations"]:
        print(
            f"{validation.import_key}: valid={validation.valid} | "
            f"rows={validation.shadow_rows} | "
            f"store_bytes={validation.comparison_store_bytes}"
        )
    if args.stage == "swap":
        print(f"Rollback statement: {result['rollback_statement']};")
    if args.output_dir:
        report = write_report(
            args.output_dir,
            args.stage,
            args.suffix,
            payload,
        )
        print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
