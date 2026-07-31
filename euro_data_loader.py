import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS
from euro_series_config import EURO_SERIES
from services.macro_analytics_service import align_macro_to_market_calendar


# =========================
# CONNECTION
# =========================

def get_engine():
    return create_engine(
        get_sqlalchemy_database_url(),
        pool_pre_ping=True
    )


# =========================
# HELPERS SQL
# =========================

def coluna_existe(table_name, column_name, engine):
    query = """
    SELECT COUNT(*) AS column_count
    FROM information_schema.columns
    WHERE table_schema = :database
      AND table_name = :table_name
      AND column_name = :column_name;
    """

    with engine.begin() as conn:
        result = conn.execute(
            text(query),
            {
                "database": DB_CONFIG["database"],
                "table_name": table_name,
                "column_name": column_name
            }
        ).fetchone()

    return result[0] > 0


def chooser_coluna_preco(table_name, engine):
    preferred_cols = [
        "price",
        "close",
        "adj_close",
        "value",
        "OBS_VALUE",
        "obs_value"
    ]

    for col in preferred_cols:
        if coluna_existe(table_name, col, engine):
            return col

    raise ValueError(
        f"No price/value column was found em {table_name}"
    )


def chooser_coluna_data_market(table_name, engine):
    preferred_cols = [
        "snapped_at",
        "date",
        "TIME_PERIOD",
        "time_period",
        "observation_date"
    ]

    for col in preferred_cols:
        if coluna_existe(table_name, col, engine):
            return col

    raise ValueError(
        f"No date column was found em {table_name}"
    )


# =========================
# PARSING DE DATAS EURO
# =========================

def parse_euro_period(value):
    if pd.isna(value):
        return pd.NaT

    text_value = str(value).strip()

    if text_value == "":
        return pd.NaT

    # Mensal: 2020-01
    try:
        if len(text_value) == 7 and text_value[4] == "-":
            return pd.to_datetime(text_value + "-01", errors="coerce")
    except Exception:
        pass

    # Anual: 2020
    try:
        if len(text_value) == 4 and text_value.isdigit():
            return pd.to_datetime(text_value + "-01-01", errors="coerce")
    except Exception:
        pass

    # Semestral: 2022-S1 / 2022-S2
    try:
        if "-S1" in text_value:
            year = text_value.split("-S1")[0]
            return pd.to_datetime(f"{year}-01-01", errors="coerce")

        if "-S2" in text_value:
            year = text_value.split("-S2")[0]
            return pd.to_datetime(f"{year}-07-01", errors="coerce")
    except Exception:
        pass

    # Trimestral: 2020-Q1 / 2020-Q2 / 2020-Q3 / 2020-Q4
    try:
        if "-Q" in text_value:
            year, quarter = text_value.split("-Q")
            quarter_month_map = {
                "1": "01",
                "2": "04",
                "3": "07",
                "4": "10"
            }
            month = quarter_month_map.get(quarter)

            if month:
                return pd.to_datetime(f"{year}-{month}-01", errors="coerce")
    except Exception:
        pass

    return pd.to_datetime(text_value, errors="coerce")


# =========================
# LOAD EURO SERIES
# =========================

def load_euro_series(series_key, engine=None, start_date=None, end_date=None):
    if engine is None:
        engine = get_engine()

    if series_key not in EURO_SERIES:
        raise ValueError(f"EURO series not configured: {series_key}")

    cfg = EURO_SERIES[series_key]

    if cfg.get("enabled", True) is not True:
        raise ValueError(f"EURO series disabled: {series_key}")

    table_name = cfg["table_name"]
    key_code = cfg["key_code"]
    key_col = cfg["key_col"]
    date_col = cfg["date_col"]
    value_col = cfg["value_col"]

    query = f"""
    SELECT
        `{date_col}` AS period_raw,
        `{value_col}` AS value
    FROM `{table_name}`
    WHERE `{key_col}` = :key_code
      AND `{date_col}` IS NOT NULL
      AND `{value_col}` IS NOT NULL
    ORDER BY `{date_col}`;
    """

    df = pd.read_sql(
        text(query),
        engine,
        params={"key_code": key_code}
    )

    if df.empty:
        raise ValueError(
            f"EURO series has no data: {series_key} | {table_name} | {key_code}"
        )

    df["snapped_at"] = df["period_raw"].apply(parse_euro_period)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["snapped_at", "value"]).copy()

    df = (
        df
        .groupby("snapped_at", as_index=False)["value"]
        .mean()
        .sort_values("snapped_at")
        .reset_index(drop=True)
    )

    df = df.rename(columns={"value": series_key})

    if start_date is not None:
        df = df[df["snapped_at"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["snapped_at"] <= pd.to_datetime(end_date)]

    df = df.reset_index(drop=True)

    print(
        f"{series_key} | {cfg['display_name']} | "
        f"{len(df)} rows | "
        f"{df['snapped_at'].min().date() if not df.empty else None} -> "
        f"{df['snapped_at'].max().date() if not df.empty else None}"
    )

    return df


# =========================
# CARREGAR ATIVO DE MERCADO
# =========================

def load_market_asset(asset_key, engine=None, start_date=None, end_date=None):
    if engine is None:
        engine = get_engine()

    if asset_key not in ASSETS:
        raise ValueError(f"Market asset not configured: {asset_key}")

    cfg = ASSETS[asset_key]
    table_name = cfg["table_name"]

    date_col = chooser_coluna_data_market(table_name, engine)
    price_col = chooser_coluna_preco(table_name, engine)

    query = f"""
    SELECT
        `{date_col}` AS snapped_at,
        `{price_col}` AS value
    FROM `{table_name}`
    WHERE `{date_col}` IS NOT NULL
      AND `{price_col}` IS NOT NULL
    ORDER BY `{date_col}`;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError(f"Market asset has no data: {asset_key}")

    df["snapped_at"] = pd.to_datetime(df["snapped_at"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["snapped_at", "value"]).copy()

    df = (
        df
        .groupby("snapped_at", as_index=False)["value"]
        .mean()
        .sort_values("snapped_at")
        .reset_index(drop=True)
    )

    df = df.rename(columns={"value": asset_key})

    if start_date is not None:
        df = df[df["snapped_at"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["snapped_at"] <= pd.to_datetime(end_date)]

    df = df.reset_index(drop=True)

    print(
        f"{asset_key} | {cfg['display_name']} | "
        f"{len(df)} rows | "
        f"{df['snapped_at'].min().date() if not df.empty else None} -> "
        f"{df['snapped_at'].max().date() if not df.empty else None}"
    )

    return df


# =========================
# ALINHAR EURO COM MERCADO
# =========================

def alinhar_euro_com_market(
    euro_series_key,
    market_asset,
    engine=None,
    start_date=None,
    end_date=None,
    how="outer",
    forward_fill=True
):
    if engine is None:
        engine = get_engine()

    print(
        f"\nAligning EURO with market: "
        f"{euro_series_key} vs {market_asset}"
    )

    euro_df = load_euro_series(
        series_key=euro_series_key,
        engine=engine,
        start_date=start_date,
        end_date=end_date
    )

    market_df = load_market_asset(
        asset_key=market_asset,
        engine=engine,
        start_date=start_date,
        end_date=end_date
    )

    df = align_macro_to_market_calendar(
        macro_df=euro_df,
        market_df=market_df,
        macro_column=euro_series_key,
        market_column=market_asset,
    )

    print(f"Aligned market observations: {len(df)}")

    if not df.empty:
        print(f"Minimum date: {df['snapped_at'].min().date()}")
        print(f"Maximum date: {df['snapped_at'].max().date()}")

    return df


# =========================
# TRANSFORMATIONS
# =========================

def normalizar_base_100(df):
    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    value_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in value_cols:
        series = df[col].dropna()

        if series.empty:
            continue

        base_value = series.iloc[0]

        if base_value == 0:
            continue

        df[col] = (df[col] / base_value) * 100

    return df


def calcular_variacoes(df, windows=None):
    if windows is None:
        windows = [90, 180, 252]

    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    value_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in value_cols:
        for window in windows:
            df[f"{col}_pct_change_{window}obs"] = df[col].pct_change(
                periods=window,
                fill_method=None
            )
            df[f"{col}_abs_change_{window}obs"] = df[col] - df[col].shift(window)

    return df


def summary_dataset(df):
    print("\nRESUMO DO DATASET")
    print("=" * 100)

    print(f"Rows: {len(df)}")

    if not df.empty:
        print(f"Minimum date: {df['snapped_at'].min()}")
        print(f"Maximum date: {df['snapped_at'].max()}")

    rows = []

    for col in df.columns:
        if col == "snapped_at":
            continue

        series = df[col]

        rows.append({
            "column": col,
            "non_null": int(series.notna().sum()),
            "null_pct": round(series.isna().mean() * 100, 2),
            "first_value": series.dropna().iloc[0] if not series.dropna().empty else None,
            "last_value": series.dropna().iloc[-1] if not series.dropna().empty else None,
            "min": series.min(),
            "max": series.max()
        })

    summary_df = pd.DataFrame(rows)

    print(summary_df)
    print("=" * 100)

    return summary_df


# =========================
# QUICK TEST
# =========================

if __name__ == "__main__":
    print("\nQuick test euro_data_loader.py")

    engine = get_engine()

    df = alinhar_euro_com_market(
        euro_series_key="EURO_HICP_EX_TOBACCO",
        market_asset="STOXX600",
        engine=engine,
        start_date="2000-01-01",
        end_date=None,
        how="outer",
        forward_fill=True
    )

    summary_dataset(df)

    norm_df = normalizar_base_100(df)

    print("\nDataset normalizado:")
    print(norm_df.head())
