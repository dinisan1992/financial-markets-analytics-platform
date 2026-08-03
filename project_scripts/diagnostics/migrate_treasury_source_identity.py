from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import shutil
import sys

import numpy as np
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
    load_existing_market_frame,
    prepare_market_frame,
    read_market_csv,
    validate_identifier,
)
from services.official_market_source_service import (
    H15_US2Y_SOURCE_LABEL,
    prepare_h15_market_frame,
    validate_h15_market_frame,
    write_standard_market_csv,
)


SOURCE_TABLE = "us2y_analysis"
DESTINATION_OLD_IDENTITY_TABLE = "us3m_analysis"


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def validate_sql_backup(path):
    path = Path(path).expanduser().resolve()
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"A non-empty SQL backup is required: {path}")
    content = path.read_text(encoding="utf-8", errors="replace")
    required = (
        "CREATE TABLE `us2y_analysis`",
        "INSERT INTO `us2y_analysis`",
        "1960-01-05",
    )
    missing = [marker for marker in required if marker not in content]
    if missing:
        raise ValueError(f"SQL backup is missing data markers: {missing}")
    return {
        "path": path,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def table_exists(engine, table_name):
    return inspect(engine).has_table(validate_identifier(table_name))


def table_summary(engine, table_name):
    table_name = validate_identifier(table_name)
    query = text(
        f"""
        SELECT
            COUNT(*) AS rows_count,
            COUNT(DISTINCT snapped_at) AS unique_dates,
            MIN(snapped_at) AS first_date,
            MAX(snapped_at) AS last_date,
            SUM(open IS NOT NULL AND high IS NOT NULL
                AND low IS NOT NULL AND close IS NOT NULL) AS native_ohlc_rows
        FROM `{table_name}`
        """
    )
    with engine.connect() as connection:
        return dict(connection.execute(query).mappings().one())


def versioned_name(base, marker, suffix):
    validate_identifier(base)
    validate_identifier(marker)
    validate_identifier(f"suffix_{suffix}")
    tail = f"__{marker}_{suffix}"
    return f"{base[:64 - len(tail)]}{tail}"


def validate_current_identity(engine):
    csv_path = Path(ASSETS["US2Y"]["csv_path"])
    prepared = read_market_csv(csv_path)
    current = load_existing_market_frame(engine, SOURCE_TABLE)
    source = prepared.frame[["snapped_at", "price"]].copy()
    database = current[["snapped_at", "price"]].copy()
    source["snapped_at"] = pd.to_datetime(source["snapped_at"]).dt.normalize()
    database["snapped_at"] = pd.to_datetime(database["snapped_at"]).dt.normalize()
    comparison = source.merge(
        database,
        on="snapped_at",
        how="outer",
        suffixes=("_csv", "_sql"),
        indicator=True,
    )
    if not comparison["_merge"].eq("both").all():
        raise RuntimeError("Current US2Y CSV and SQL dates are not identical")
    price_match = np.isclose(
        comparison["price_csv"],
        comparison["price_sql"],
        rtol=1e-5,
        atol=1e-6,
        equal_nan=True,
    )
    if not price_match.all():
        raise RuntimeError("Current US2Y CSV and SQL prices are not identical")
    summary = table_summary(engine, SOURCE_TABLE)
    if summary["rows_count"] != summary["unique_dates"]:
        raise RuntimeError("Current US2Y table contains duplicate dates")
    return prepared, summary


def create_and_validate_shadow(engine, shadow_table, official_frame):
    shadow_table = validate_identifier(shadow_table)
    prepared = prepare_market_frame(official_frame)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE `{shadow_table}` LIKE `{SOURCE_TABLE}`"))

    schema = get_table_schema(engine, shadow_table)
    empty = pd.DataFrame(columns=prepared.frame.columns)
    plan, actions = build_market_sync_plan(
        asset="US2Y",
        table=shadow_table,
        prepared_source=prepared,
        existing_frame=empty,
        unique_date_key_available=has_unique_date_key(engine, shadow_table),
    )
    applied = apply_market_sync(
        engine,
        shadow_table,
        prepared,
        actions,
        table_schema=schema,
    )
    if applied != len(official_frame):
        raise RuntimeError(f"US2Y shadow write mismatch: {applied} != {len(official_frame)}")

    summary = table_summary(engine, shadow_table)
    expected = validate_h15_market_frame(official_frame)
    checks = {
        "rows_count": expected["rows"],
        "unique_dates": expected["unique_dates"],
        "first_date": expected["first_date"],
        "last_date": expected["last_date"],
        "native_ohlc_rows": 0,
    }
    for key, value in checks.items():
        if summary[key] != value:
            raise RuntimeError(
                f"US2Y shadow validation failed for {key}: {summary[key]} != {value}"
            )

    source_count_query = text(
        f"SELECT COUNT(*) FROM `{shadow_table}` WHERE source_file = :source_file"
    )
    with engine.connect() as connection:
        source_rows = int(
            connection.execute(
                source_count_query,
                {"source_file": H15_US2Y_SOURCE_LABEL},
            ).scalar_one()
        )
    if source_rows != expected["rows"]:
        raise RuntimeError("US2Y shadow source provenance is incomplete")
    return summary


def create_retained_sql_copy(engine, retained_table):
    retained_table = validate_identifier(retained_table)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE TABLE `{retained_table}` LIKE `{SOURCE_TABLE}`"))
        connection.execute(
            text(f"INSERT INTO `{retained_table}` SELECT * FROM `{SOURCE_TABLE}`")
        )
    source_summary = table_summary(engine, SOURCE_TABLE)
    retained_summary = table_summary(engine, retained_table)
    if retained_summary != source_summary:
        raise RuntimeError("Retained SQL copy does not match the source table")
    return retained_summary


def prepare_csv_files(official_frame, csv_backup_dir, suffix):
    current_path = Path(ASSETS["US2Y"]["csv_path"])
    us3m_path = Path(ASSETS["US3M"]["csv_path"])
    backup_dir = Path(csv_backup_dir).expanduser().resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"us2y_as_irx_before_v051_{suffix}.csv"

    if us3m_path.exists():
        raise ValueError(f"US3M CSV already exists: {us3m_path}")
    shutil.copy2(current_path, backup_path)
    if sha256_file(current_path) != sha256_file(backup_path):
        raise RuntimeError("US2Y CSV backup checksum mismatch")
    shutil.copy2(current_path, us3m_path)
    write_standard_market_csv(official_frame, current_path)
    return current_path, us3m_path, backup_path


def apply_migration(engine, package_file, backup_file, csv_backup_dir, suffix):
    backup = validate_sql_backup(backup_file)
    official_frame = prepare_h15_market_frame(package_file)
    official_summary = validate_h15_market_frame(official_frame)
    _, current_summary = validate_current_identity(engine)

    shadow = versioned_name(SOURCE_TABLE, "shadow_v051", suffix)
    retained = versioned_name(SOURCE_TABLE, "pre_v051", suffix)
    for table_name in (DESTINATION_OLD_IDENTITY_TABLE, shadow, retained):
        if table_exists(engine, table_name):
            raise ValueError(f"Migration target already exists: {table_name}")

    print(f"Verified SQL backup: {backup['path']}")
    print(f"  bytes: {backup['bytes']}")
    print(f"  sha256: {backup['sha256']}")
    print(f"Current mislabeled series: {current_summary}")
    print(f"Official US2Y candidate: {official_summary}")

    create_retained_sql_copy(engine, retained)
    shadow_summary = create_and_validate_shadow(engine, shadow, official_frame)
    current_csv, us3m_csv, csv_backup = prepare_csv_files(
        official_frame,
        csv_backup_dir,
        suffix,
    )

    rename_statement = text(
        f"RENAME TABLE `{SOURCE_TABLE}` TO `{DESTINATION_OLD_IDENTITY_TABLE}`, "
        f"`{shadow}` TO `{SOURCE_TABLE}`"
    )
    try:
        with engine.begin() as connection:
            connection.execute(rename_statement)
    except Exception:
        shutil.copy2(csv_backup, current_csv)
        us3m_csv.unlink(missing_ok=True)
        raise

    final_us2y = table_summary(engine, SOURCE_TABLE)
    final_us3m = table_summary(engine, DESTINATION_OLD_IDENTITY_TABLE)
    if final_us2y != shadow_summary:
        raise RuntimeError("Final US2Y table differs from the validated shadow")
    if final_us3m != current_summary:
        raise RuntimeError("Final US3M table differs from the original table")
    if not has_unique_date_key(engine, SOURCE_TABLE):
        raise RuntimeError("Final US2Y table has no unique date key")
    if not has_unique_date_key(engine, DESTINATION_OLD_IDENTITY_TABLE):
        raise RuntimeError("Final US3M table has no unique date key")

    print(f"Final US2Y: {final_us2y}")
    print(f"Final US3M: {final_us3m}")
    print(f"Retained SQL table: {retained}")
    print(f"Retained CSV backup: {csv_backup}")


def print_plan(engine, package_file, backup_file=None):
    official = validate_h15_market_frame(prepare_h15_market_frame(package_file))
    _, current = validate_current_identity(engine)
    print("Treasury source-identity migration plan")
    print("  database_write_performed: False")
    print(f"  current_US2Y_to_US3M: {current}")
    print(f"  official_DGS2_to_US2Y: {official}")
    print(f"  us3m_table_exists: {table_exists(engine, DESTINATION_OLD_IDENTITY_TABLE)}")
    if backup_file:
        backup = validate_sql_backup(backup_file)
        print(f"  verified_backup: {backup['path']}")
        print(f"  backup_sha256: {backup['sha256']}")


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Reclassify the current ^IRX history as US3M and replace US2Y with "
            "the official Federal Reserve H.15 2-year series. Dry-run is default."
        )
    )
    parser.add_argument("--package-file", required=True)
    parser.add_argument("--backup-file")
    parser.add_argument("--csv-backup-dir")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--suffix", default=datetime.now().strftime("%Y%m%d_%H%M%S"))
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    package_file = Path(args.package_file).expanduser().resolve()
    if not package_file.exists():
        raise FileNotFoundError(f"H.15 package not found: {package_file}")
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    if not args.apply:
        print_plan(engine, package_file, backup_file=args.backup_file)
        return
    if not args.backup_file or not args.csv_backup_dir:
        raise SystemExit("--backup-file and --csv-backup-dir are required with --apply")
    apply_migration(
        engine,
        package_file,
        args.backup_file,
        args.csv_backup_dir,
        args.suffix,
    )


if __name__ == "__main__":
    main()
