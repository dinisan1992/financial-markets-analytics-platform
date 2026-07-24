import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# SQL CONNECTION
# =========================

def get_db_url():
    return get_sqlalchemy_database_url()


def get_engine():
    return create_engine(
        get_db_url(),
        pool_pre_ping=True
    )


# =========================
# DATES / PERIODS
# =========================

def calcular_data_inicio_anos(anos):
    hoje = pd.Timestamp.today().normalize()
    data_inicio = hoje - pd.DateOffset(years=anos)

    return data_inicio.strftime("%Y-%m-%d")


def filtrar_periodo(df, date_col="snapped_at", start_date=None, end_date=None):
    df = df.copy()

    df[date_col] = pd.to_datetime(
        df[date_col],
        errors="coerce"
    )

    df = df.dropna(subset=[date_col])

    if start_date is not None:
        df = df[df[date_col] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df[date_col] <= pd.to_datetime(end_date)]

    return df


# =========================
# ASSET LOADING
# =========================

def load_asset(asset_key, engine=None, start_date=None, end_date=None):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Asset not found: {asset_key}")

    if engine is None:
        engine = get_engine()

    asset = ASSETS[asset_key]
    table_name = asset["table_name"]

    query = f"""
    SELECT
        snapped_at,
        price
    FROM `{table_name}`
    ORDER BY snapped_at;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError(f"Empty table: {table_name}")

    df["snapped_at"] = pd.to_datetime(
        df["snapped_at"],
        errors="coerce"
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    df = df.dropna(subset=["snapped_at", "price"])
    df = df.sort_values("snapped_at").reset_index(drop=True)

    df = filtrar_periodo(
        df=df,
        date_col="snapped_at",
        start_date=start_date,
        end_date=end_date
    )

    if df.empty:
        raise ValueError(f"No data after filters: {asset_key}")

    df = df[["snapped_at", "price"]].copy()
    df = df.rename(columns={"price": asset_key})

    return df


def load_multiplos_assets(
    asset_keys,
    engine=None,
    start_date=None,
    end_date=None,
    how="outer",
    forward_fill=True
):
    if engine is None:
        engine = get_engine()

    merged_df = None
    loaded_assets = []

    for asset_key in asset_keys:
        try:
            df_asset = load_asset(
                asset_key=asset_key,
                engine=engine,
                start_date=start_date,
                end_date=end_date
            )

            loaded_assets.append(asset_key)

            if merged_df is None:
                merged_df = df_asset

            else:
                merged_df = pd.merge(
                    merged_df,
                    df_asset,
                    on="snapped_at",
                    how=how
                )

        except Exception as e:
            print(f"ERRORR loading {asset_key}: {e}")

    if merged_df is None or merged_df.empty:
        raise ValueError("No asset was loaded.")

    merged_df = merged_df.sort_values("snapped_at").reset_index(drop=True)

    asset_cols = [
        col for col in merged_df.columns
        if col != "snapped_at"
    ]

    if forward_fill:
        merged_df[asset_cols] = merged_df[asset_cols].ffill()

    return merged_df, loaded_assets


# =========================
# TRANSFORMATIONS
# =========================

def normalizar_base_100(df):
    df = df.copy()

    normalized_df = pd.DataFrame()
    normalized_df["snapped_at"] = df["snapped_at"]

    asset_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in asset_cols:
        series = df[col].copy()
        first_valid = series.dropna()

        if first_valid.empty:
            continue

        base_value = first_valid.iloc[0]

        if base_value == 0:
            continue

        normalized_df[col] = (series / base_value) * 100

    return normalized_df


def calcular_returns(df):
    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    returns_df = pd.DataFrame()
    returns_df["snapped_at"] = df["snapped_at"]

    asset_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in asset_cols:
        returns_df[col] = df[col].pct_change()

    returns_df = returns_df.replace([float("inf"), float("-inf")], pd.NA)

    return returns_df


def calcular_drawdown(series):
    running_max = series.cummax()
    drawdown = (series / running_max) - 1

    return drawdown


# =========================
# MENUS SIMPLES
# =========================

def chooser_periodo_terminal():
    print("\n" + "=" * 80)
    print("CHOOSE PERIOD")
    print("=" * 80)
    print("1 - Since 2020")
    print("2 - Last 1 year")
    print("3 - Last 3 years")
    print("4 - Last 5 years")
    print("5 - Last 10 years")
    print("6 - Full available history")
    print("7 - Custom date")
    print("=" * 80)

    while True:
        choice = input("\nChoose the period: ").strip()

        if choice == "1":
            return "2020-01-01", None, "Since 2020"

        if choice == "2":
            return calcular_data_inicio_anos(1), None, "Last 1 year"

        if choice == "3":
            return calcular_data_inicio_anos(3), None, "Last 3 years"

        if choice == "4":
            return calcular_data_inicio_anos(5), None, "Last 5 years"

        if choice == "5":
            return calcular_data_inicio_anos(10), None, "Last 10 years"

        if choice == "6":
            return None, None, "Full history"

        if choice == "7":
            return chooser_periodo_personalizado_terminal()

        print("Invalid choice.")


def chooser_periodo_personalizado_terminal():
    print("\nRecommended format: YYYY-MM-DD")

    while True:
        start_date = input("\nStart date: ").strip()

        try:
            pd.to_datetime(start_date)
            break

        except Exception:
            print("Invalid start date.")

    end_date = input("End date or ENTER to use the end: ").strip()

    if end_date == "":
        end_date = None

    else:
        try:
            pd.to_datetime(end_date)

        except Exception:
            print("Invalid end date. Using the end.")
            end_date = None

    label = f"{start_date} until {end_date if end_date else 'end'}"

    return start_date, end_date, label


# =========================
# EXPORT / NOMES SEGUROS
# =========================

def safe_filename(text):
    text = str(text).lower().strip()

    text = text.replace(" ", "_")
    text = text.replace("/", "_")
    text = text.replace("\\", "_")
    text = text.replace(":", "_")

    text = re.sub(r"[^a-z0-9_\-\.]", "", text)

    return text[:120]


def export_dataframe(df, filename, sep=";", encoding="utf-8-sig"):
    output_path = Path(filename)

    df.to_csv(
        output_path,
        index=False,
        sep=sep,
        encoding=encoding
    )

    print(f"Report saved to: {output_path}")

    return output_path
