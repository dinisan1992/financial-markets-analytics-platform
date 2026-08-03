from pathlib import Path
import argparse
import sys

from sqlalchemy import create_engine


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_config import ASSETS
from config import get_sqlalchemy_database_url
from services.market_data_sync_service import (
    apply_market_sync,
    build_market_sync_plan,
    format_market_sync_plan,
    get_table_schema,
    has_unique_date_key,
    load_existing_market_frame,
    read_market_csv,
)


def get_engine():
    return create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)


def plan_asset_sync(engine, asset_key):
    asset_key = asset_key.upper()
    if asset_key not in ASSETS:
        raise ValueError(f"Unknown asset key: {asset_key}")

    asset = ASSETS[asset_key]
    table_name = asset["table_name"]
    csv_path = Path(asset["csv_path"])
    prepared = read_market_csv(csv_path)
    schema = get_table_schema(engine, table_name)
    existing = load_existing_market_frame(engine, table_name, table_schema=schema)
    unique_key = has_unique_date_key(engine, table_name)
    plan, actions = build_market_sync_plan(
        asset=asset_key,
        table=table_name,
        prepared_source=prepared,
        existing_frame=existing,
        unique_date_key_available=unique_key,
    )
    return plan, actions, prepared, schema


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Plan a CSV-to-SQL market-data sync. Dry-run is the default; "
            "database writes require --update-sql."
        )
    )
    parser.add_argument("asset_key", nargs="?", help="Configured asset key.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Generate read-only plans for all configured assets.",
    )
    parser.add_argument(
        "--update-sql",
        action="store_true",
        help="Apply the planned insert/update transaction for one asset.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.all and args.asset_key:
        parser.error("Use either asset_key or --all, not both")
    if not args.all and not args.asset_key:
        parser.error("asset_key is required unless --all is used")
    if args.all and args.update_sql:
        parser.error("Bulk SQL writes are disabled; update one explicit asset at a time")

    engine = get_engine()
    asset_keys = list(ASSETS) if args.all else [args.asset_key.upper()]
    failures = []

    for asset_key in asset_keys:
        try:
            plan, actions, prepared, schema = plan_asset_sync(engine, asset_key)
            print(format_market_sync_plan(plan))
            if args.update_sql:
                applied = apply_market_sync(
                    engine=engine,
                    table_name=plan.table,
                    prepared_source=prepared,
                    actions_frame=actions,
                    table_schema=schema,
                )
                print("  execution_database_write_performed: True")
                print(f"  rows_applied: {applied}")
        except Exception as exc:
            failures.append((asset_key, str(exc)))
            print(f"Market CSV sync failed for {asset_key}: {exc}")

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
