from pathlib import Path
from datetime import datetime
import argparse
import sys

import pandas as pd
from sqlalchemy import create_engine, inspect, text


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
    get_table_schema,
    has_unique_date_key,
    read_market_csv,
    validate_identifier,
)


TARGETS = {
    "SP500": "sp500_analysis_clean",
    "GOLD": "gold_analysis_clean",
    "DXY": "dxy_analysis_clean",
    "EURO": "euro_analysis",
    "YUAN": "yuan_analysis",
    "LIBRA": "libra_analysis",
    "SSECOMPOSITE": "ssecomposite_analysis",
}
CSV_REBUILD_ASSETS = {"SP500"}


def versioned_table_name(table_name, marker, suffix):
    validate_identifier(table_name)
    validate_identifier(marker)
    validate_identifier(f"suffix_{suffix}")
    tail = f"__{marker}_{suffix}"
    return f"{table_name[:64 - len(tail)]}{tail}"


def table_exists(engine, table_name):
    return inspect(engine).has_table(table_name)


def scalar(engine, query, parameters=None):
    with engine.connect() as connection:
        return connection.execute(text(query), parameters or {}).scalar_one()


def table_summary(engine, table_name):
    validate_identifier(table_name)
    query = f"""
    SELECT
        COUNT(*) AS rows_count,
        COUNT(DISTINCT snapped_at) AS unique_dates,
        MIN(snapped_at) AS first_date,
        MAX(snapped_at) AS last_date
    FROM `{table_name}`
    """
    with engine.connect() as connection:
        row = connection.execute(text(query)).mappings().one()
    return dict(row)


def create_ranked_shadow(engine, source_table, shadow_table):
    source_table = validate_identifier(source_table)
    shadow_table = validate_identifier(shadow_table)
    schema = get_table_schema(engine, source_table)
    columns = [row["column_name"] for row in schema]
    quoted = ", ".join(f"`{validate_identifier(column)}`" for column in columns)
    completeness_columns = [column for column in columns if column != "snapped_at"]
    completeness = " + ".join(
        f"(`{validate_identifier(column)}` IS NOT NULL)"
        for column in completeness_columns
    ) or "0"

    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE `{shadow_table}` LIKE `{source_table}`"))
        connection.execute(
            text(
                f"""
                INSERT INTO `{shadow_table}` ({quoted})
                SELECT {quoted}
                FROM (
                    SELECT
                        {quoted},
                        ROW_NUMBER() OVER (
                            PARTITION BY `snapped_at`
                            ORDER BY ({completeness}) DESC
                        ) AS `_canonical_rank`
                    FROM `{source_table}`
                    WHERE `snapped_at` IS NOT NULL
                ) AS ranked
                WHERE `_canonical_rank` = 1
                """
            )
        )


def create_csv_shadow(engine, asset_key, source_table, shadow_table):
    source_table = validate_identifier(source_table)
    shadow_table = validate_identifier(shadow_table)
    prepared = read_market_csv(ASSETS[asset_key]["csv_path"])

    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE `{shadow_table}` LIKE `{source_table}`"))
        connection.execute(
            text(
                f"ALTER TABLE `{shadow_table}` "
                "MODIFY `snapped_at` DATETIME NOT NULL, "
                "ADD UNIQUE KEY `uq_snapped_at` (`snapped_at`)"
            )
        )

    schema = get_table_schema(engine, shadow_table)
    empty = pd.DataFrame(columns=prepared.frame.columns)
    plan, actions = build_market_sync_plan(
        asset=asset_key,
        table=shadow_table,
        prepared_source=prepared,
        existing_frame=empty,
        unique_date_key_available=True,
    )
    applied = apply_market_sync(
        engine=engine,
        table_name=shadow_table,
        prepared_source=prepared,
        actions_frame=actions,
        table_schema=schema,
    )
    if applied != plan.valid_source_rows:
        raise RuntimeError(
            f"CSV shadow row mismatch for {asset_key}: {applied} != {plan.valid_source_rows}"
        )
    return prepared


def add_daily_key(engine, table_name):
    table_name = validate_identifier(table_name)
    with engine.begin() as connection:
        connection.execute(
            text(
                f"ALTER TABLE `{table_name}` "
                "MODIFY `snapped_at` DATETIME NOT NULL, "
                "ADD UNIQUE KEY `uq_snapped_at` (`snapped_at`)"
            )
        )


def validate_ranked_shadow(engine, source_table, shadow_table):
    source = table_summary(engine, source_table)
    shadow = table_summary(engine, shadow_table)
    if shadow["rows_count"] != source["unique_dates"]:
        raise RuntimeError(
            f"Shadow count mismatch for {source_table}: "
            f"{shadow['rows_count']} != {source['unique_dates']}"
        )
    mismatch_query = f"""
    SELECT COUNT(*)
    FROM `{source_table}` AS source
    JOIN `{shadow_table}` AS shadow
      ON shadow.snapped_at = source.snapped_at
    WHERE NOT (shadow.price <=> source.price)
       OR NOT (shadow.total_volume <=> source.total_volume)
    """
    if int(scalar(engine, mismatch_query)) != 0:
        raise RuntimeError(f"Base-value mismatch in shadow table: {shadow_table}")


def build_rename_statement(targets, suffix):
    pairs = []
    for table_name in targets.values():
        backup = versioned_table_name(table_name, "pre_v050", suffix)
        shadow = versioned_table_name(table_name, "shadow", suffix)
        pairs.extend(
            [
                f"`{table_name}` TO `{backup}`",
                f"`{shadow}` TO `{table_name}`",
            ]
        )
    return "RENAME TABLE " + ", ".join(pairs)


def print_plan(engine, suffix, writes_enabled=False):
    print("Market-table remediation plan")
    print(f"Database writes: {'enabled' if writes_enabled else 'disabled'}")
    for asset_key, table_name in TARGETS.items():
        summary = table_summary(engine, table_name)
        mode = "rebuild_from_csv" if asset_key in CSV_REBUILD_ASSETS else "deduplicate_clone"
        print(
            f"{asset_key}: {table_name} | mode={mode} | rows={summary['rows_count']} | "
            f"unique_dates={summary['unique_dates']} | unique_key={has_unique_date_key(engine, table_name)}"
        )
        print(
            f"  shadow={versioned_table_name(table_name, 'shadow', suffix)} | "
            f"retained_backup={versioned_table_name(table_name, 'pre_v050', suffix)}"
        )


def apply_remediation(engine, suffix, backup_file, resume=False):
    backup_path = Path(backup_file).expanduser().resolve()
    if not backup_path.exists() or backup_path.stat().st_size == 0:
        raise ValueError(f"A verified non-empty backup file is required: {backup_path}")

    for table_name in TARGETS.values():
        shadow = versioned_table_name(table_name, "shadow", suffix)
        retained = versioned_table_name(table_name, "pre_v050", suffix)
        if not table_exists(engine, table_name):
            raise ValueError(f"Source table not found: {table_name}")
        if table_exists(engine, retained):
            raise ValueError(f"Retained backup name already exists for {table_name}")
        if table_exists(engine, shadow) and not resume:
            raise ValueError(
                f"Shadow already exists for {table_name}; inspect it or use --resume"
            )

    for asset_key, table_name in TARGETS.items():
        shadow = versioned_table_name(table_name, "shadow", suffix)
        print(f"Building shadow table: {asset_key} -> {shadow}")
        if asset_key in CSV_REBUILD_ASSETS:
            prepared = read_market_csv(ASSETS[asset_key]["csv_path"])
            if not table_exists(engine, shadow):
                create_csv_shadow(engine, asset_key, table_name, shadow)
            summary = table_summary(engine, shadow)
            if summary["rows_count"] != len(prepared.frame):
                raise RuntimeError(f"CSV validation failed for {shadow}")
        else:
            if not table_exists(engine, shadow):
                create_ranked_shadow(engine, table_name, shadow)
            if not has_unique_date_key(engine, shadow):
                add_daily_key(engine, shadow)
            validate_ranked_shadow(engine, table_name, shadow)
        if not has_unique_date_key(engine, shadow):
            raise RuntimeError(f"Unique date key was not created: {shadow}")

    rename_statement = build_rename_statement(TARGETS, suffix)
    with engine.begin() as connection:
        connection.execute(text(rename_statement))

    for table_name in TARGETS.values():
        summary = table_summary(engine, table_name)
        if summary["rows_count"] != summary["unique_dates"]:
            raise RuntimeError(f"Post-swap duplicates remain in {table_name}")
        if not has_unique_date_key(engine, table_name):
            raise RuntimeError(f"Post-swap unique key missing in {table_name}")
        print(
            f"Validated: {table_name} | rows={summary['rows_count']} | "
            f"range={summary['first_date']} -> {summary['last_date']}"
        )


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create and validate shadow market tables, then atomically swap them. "
            "Dry-run is the default."
        )
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse already-created shadow tables after an interrupted pre-swap run.",
    )
    parser.add_argument("--backup-file")
    parser.add_argument(
        "--suffix",
        default=datetime.now().strftime("%Y%m%d"),
        help="Identifier-safe suffix for shadow and retained backup tables.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    validate_identifier(f"suffix_{args.suffix}")
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    print_plan(engine, args.suffix, writes_enabled=args.apply)
    if not args.apply:
        return
    if not args.backup_file:
        raise SystemExit("--backup-file is required with --apply")
    apply_remediation(
        engine,
        args.suffix,
        args.backup_file,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()
