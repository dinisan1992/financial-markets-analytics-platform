from pathlib import Path
import argparse
import sys

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_config import ASSETS
from config import get_sqlalchemy_database_url
from indicators import calcular_indicadores
from services.data_access_service import deduplicate_market_observations


REQUIRED_CSV_COLUMNS = [
    "snapped_at",
    "price",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "total_volume",
    "source_file",
]


def get_engine():
    return create_engine(
        get_sqlalchemy_database_url(),
        pool_pre_ping=True,
    )


def normalize_columns(df):
    df = df.copy()
    df.columns = [
        str(col)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("%", "percent")
        for col in df.columns
    ]
    return df


def prepare_csv_dataframe(csv_path):
    df = pd.read_csv(
        csv_path,
        sep=";",
        encoding="utf-8-sig",
    )
    df = normalize_columns(df)

    missing_cols = [
        col for col in REQUIRED_CSV_COLUMNS
        if col not in df.columns
    ]

    if missing_cols:
        raise ValueError(f"Missing CSV columns: {missing_cols}")

    df = df[REQUIRED_CSV_COLUMNS].copy()
    df["snapped_at"] = pd.to_datetime(df["snapped_at"], errors="coerce").dt.date

    numeric_cols = [
        "price",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "total_volume",
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["snapped_at", "price"])
    df = df.drop_duplicates(subset=["snapped_at"], keep="last")
    df = df.sort_values("snapped_at").reset_index(drop=True)

    return df


def get_table_columns(engine, table_name):
    query = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = :table_name
        """
    )

    with engine.connect() as conn:
        rows = conn.execute(query, {"table_name": table_name}).fetchall()

    return {row[0] for row in rows}


def load_sql_dataframe(engine, table_name):
    columns = get_table_columns(engine, table_name)

    if not columns:
        raise ValueError(f"Table not found: {table_name}")

    required = {"snapped_at", "price"}
    missing_required = required - columns

    if missing_required:
        raise ValueError(f"Missing table columns in {table_name}: {sorted(missing_required)}")

    selected_cols = [
        col for col in REQUIRED_CSV_COLUMNS
        if col in columns
    ]

    quoted_cols = ", ".join(f"`{col}`" for col in selected_cols)
    query = f"""
    SELECT {quoted_cols}
    FROM `{table_name}`
    WHERE snapped_at IS NOT NULL
      AND price IS NOT NULL
    ORDER BY snapped_at;
    """

    return pd.read_sql(query, engine)


def prepare_indicator_frame(df):
    df = normalize_columns(df)
    df["snapped_at"] = pd.to_datetime(df["snapped_at"], errors="coerce")

    for col in ["price", "open", "high", "low", "close", "total_volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["snapped_at", "price"])
    df = deduplicate_market_observations(df, date_column="snapped_at")

    if "close" not in df.columns or df["close"].isna().all():
        df["close"] = df["price"]

    if "open" not in df.columns or df["open"].isna().all():
        df["open"] = df["close"].shift(1)

    if "high" not in df.columns or df["high"].isna().all():
        df["high"] = df[["open", "close"]].max(axis=1)

    if "low" not in df.columns or df["low"].isna().all():
        df["low"] = df[["open", "close"]].min(axis=1)

    if "total_volume" not in df.columns:
        df["total_volume"] = 0

    df["volume"] = df["total_volume"].fillna(0)
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    return df


def validate_asset_key(asset_key):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Unknown asset key: {asset_key}")

    return asset_key


def process_asset(asset_key, source="sql", update_sql=False):
    if update_sql:
        raise ValueError(
            "SQL updates moved to sync_market_data.py so every write has a dry-run plan"
        )

    asset_key = validate_asset_key(asset_key)
    asset = ASSETS[asset_key]
    table_name = asset["table_name"]
    csv_path = Path(asset["csv_path"])
    engine = get_engine()

    print("\n" + "=" * 70)
    print(f"Asset: {asset_key} | {asset['display_name']}")
    print(f"Table: {table_name}")
    print(f"CSV: {csv_path}")
    print(f"Source: {source}")
    print(f"Update SQL: {update_sql}")
    print("=" * 70)

    if source == "csv":
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {csv_path}")
        raw_df = prepare_csv_dataframe(csv_path)
    else:
        raw_df = load_sql_dataframe(engine, table_name)

    if raw_df.empty:
        raise ValueError(f"No data loaded for {asset_key}")

    indicator_df = prepare_indicator_frame(raw_df)

    if indicator_df.empty:
        raise ValueError(f"Not enough rows after OHLC preparation for {asset_key}")

    indicator_df = calcular_indicadores(indicator_df)
    indicator_df = indicator_df.replace([np.inf, -np.inf], pd.NA)

    min_date = indicator_df["snapped_at"].min().date()
    max_date = indicator_df["snapped_at"].max().date()

    print(f"Rows loaded: {len(raw_df)}")
    print(f"Indicator rows: {len(indicator_df)}")
    print(f"Date range: {min_date} -> {max_date}")
    print("Status: OK")

    return {
        "asset_key": asset_key,
        "table_name": table_name,
        "rows_loaded": len(raw_df),
        "indicator_rows": len(indicator_df),
        "min_date": min_date,
        "max_date": max_date,
        "status": "success",
    }


def build_parser(default_asset_key=None):
    parser = argparse.ArgumentParser(
        description="Validate or update one configured new-market asset."
    )
    parser.add_argument(
        "asset_key",
        nargs="?",
        default=default_asset_key,
        help="Asset key from asset_config.py, for example NASDAQ100.",
    )
    parser.add_argument(
        "--source",
        choices=["sql", "csv"],
        default="sql",
        help="Read source used for validation/calculation. Default: sql.",
    )
    parser.add_argument(
        "--update-sql",
        action="store_true",
        help="Deprecated: use sync_market_data.py after reviewing its dry-run.",
    )
    return parser


def main(default_asset_key=None, argv=None):
    parser = build_parser(default_asset_key=default_asset_key)
    args = parser.parse_args(argv)

    if not args.asset_key:
        parser.error("asset_key is required")
    if args.update_sql:
        parser.error(
            "SQL updates moved to sync_market_data.py; run its dry-run before --update-sql"
        )

    process_asset(
        asset_key=args.asset_key,
        source=args.source,
        update_sql=args.update_sql,
    )


if __name__ == "__main__":
    main()
