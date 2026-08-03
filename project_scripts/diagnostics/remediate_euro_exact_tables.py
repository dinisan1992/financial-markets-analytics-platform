from datetime import datetime
from pathlib import Path
import argparse
import json
import sys

from sqlalchemy import create_engine


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_sqlalchemy_database_url
from macro_import_manifest import get_macro_import
from services.euro_exact_rebuild_service import (
    BUILD_EXACT_CONFIRMATION,
    REBUILD_VERSION,
    SWAP_EXACT_CONFIRMATION,
    TARGET_IMPORT_KEYS,
    build_exact_shadows,
    swap_exact_shadows,
)
from services.euro_rebuild_service import retained_table_name, shadow_table_name
from services.market_data_sync_service import validate_identifier


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild three source-complete EURO tables without changing the "
            "active tables before a validated atomic swap. The default plan "
            "is read-only."
        )
    )
    parser.add_argument(
        "--stage",
        choices=("plan", "build", "swap"),
        default="plan",
    )
    parser.add_argument("--backup-file")
    parser.add_argument("--confirm")
    parser.add_argument(
        "--suffix",
        default=datetime.now().strftime("%Y%m%d_%H%M%S"),
    )
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--insert-batch-size", type=int, default=250)
    parser.add_argument("--output-dir")
    return parser


def _write_report(output_dir, stage, suffix, result):
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"euro_exact_{stage}_{suffix}.json"
    payload = {
        "stage": stage,
        "version": REBUILD_VERSION,
        "suffix": suffix,
        "database_write_performed": result["database_write_performed"],
        "active_tables_changed": result["active_tables_changed"],
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
    output_path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    return output_path


def print_plan(suffix):
    print("EURO exact-source rebuild plan")
    print("Database writes: disabled")
    for import_key in TARGET_IMPORT_KEYS:
        table_name = get_macro_import(import_key)["table_name"]
        print(
            f"{import_key}: active={table_name} | "
            f"shadow={shadow_table_name(table_name, suffix, REBUILD_VERSION)} | "
            f"retained={retained_table_name(table_name, suffix, REBUILD_VERSION)}"
        )
    print(f"Build confirmation: {BUILD_EXACT_CONFIRMATION}")
    print(f"Swap confirmation: {SWAP_EXACT_CONFIRMATION}")
    print("active_tables_changed: False")


def main(argv=None):
    args = build_parser().parse_args(argv)
    validate_identifier(f"suffix_{args.suffix}")
    if args.chunk_size < 1:
        raise SystemExit("--chunk-size must be positive")
    if args.insert_batch_size < 1:
        raise SystemExit("--insert-batch-size must be positive")
    if args.stage == "plan":
        print_plan(args.suffix)
        return 0
    if not args.backup_file or not args.confirm:
        raise SystemExit("--backup-file and --confirm are required")

    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        if args.stage == "build":
            result = build_exact_shadows(
                engine=engine,
                backup_file=args.backup_file,
                confirmation=args.confirm,
                suffix=args.suffix,
                chunk_size=args.chunk_size,
                insert_batch_size=args.insert_batch_size,
            )
        else:
            result = swap_exact_shadows(
                engine=engine,
                backup_file=args.backup_file,
                confirmation=args.confirm,
                suffix=args.suffix,
                chunk_size=args.chunk_size,
            )
    finally:
        engine.dispose()

    print(f"Stage: {args.stage}")
    print(f"Database writes: {result['database_write_performed']}")
    print(f"Active tables changed: {result['active_tables_changed']}")
    print(f"Backup SHA-256: {result['backup']['sha256']}")
    for validation in result["validations"]:
        print(
            f"{validation.import_key}: valid={validation.valid} | "
            f"rows={validation.shadow_rows} | "
            f"range={validation.first_period} -> {validation.last_period} | "
            f"hash_mismatches={validation.row_hash_mismatches}"
        )
    if args.stage == "swap":
        print("Retained original tables:")
        for table_name in result["retained_tables"]:
            print(f"  {table_name}")
        print("Reviewed rollback statement:")
        print(result["rollback_statement"] + ";")
    if args.output_dir:
        report = _write_report(
            args.output_dir,
            args.stage,
            args.suffix,
            result,
        )
        print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
