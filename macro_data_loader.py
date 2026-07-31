import pandas as pd
from sqlalchemy import create_engine

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS
from macro_config import MACRO_ASSETS, get_macro_config
from services.macro_analytics_service import align_macro_to_market_calendar


# =========================
# CONNECTION
# =========================

def get_db_url():
    return get_sqlalchemy_database_url()


def get_engine():
    return create_engine(
        get_db_url(),
        pool_pre_ping=True
    )


# =========================
# FILTRAR DATAS
# =========================

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

    return df.sort_values(date_col).reset_index(drop=True)


# =========================
# CARREGAR INDICADOR MACRO
# =========================

def load_macro(macro_key, engine=None, start_date=None, end_date=None):
    macro_key = macro_key.upper()

    if macro_key not in MACRO_ASSETS:
        raise ValueError(f"Macro indicator not found: {macro_key}")

    if engine is None:
        engine = get_engine()

    cfg = get_macro_config(macro_key)

    table_name = cfg["table_name"]
    date_col = cfg["date_col"]
    value_col = cfg["value_col"]

    query = f"""
    SELECT
        `{date_col}` AS snapped_at,
        `{value_col}` AS value
    FROM `{table_name}`
    ORDER BY `{date_col}`;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError(f"Table macro empty: {table_name}")

    df["snapped_at"] = pd.to_datetime(
        df["snapped_at"],
        errors="coerce"
    )

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce"
    )

    df = df.dropna(subset=["snapped_at", "value"])
    df = df.sort_values("snapped_at").reset_index(drop=True)

    df = filtrar_periodo(
        df=df,
        date_col="snapped_at",
        start_date=start_date,
        end_date=end_date
    )

    if df.empty:
        raise ValueError(f"No macro data after filters: {macro_key}")

    df = df.rename(columns={"value": macro_key})

    print(
        f"{macro_key:35s} | "
        f"{cfg['display_name']:55s} | "
        f"{len(df):7d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df[["snapped_at", macro_key]].copy()


# =========================
# LOAD MULTIPLE MACRO INDICATORS
# =========================

def load_multiplos_macro(
    macro_keys,
    engine=None,
    start_date=None,
    end_date=None,
    how="outer",
    forward_fill=True
):
    if engine is None:
        engine = get_engine()

    merged_df = None
    loaded_macros = []

    print("\nLoading macro indicators:")
    print("-" * 130)

    for macro_key in macro_keys:
        try:
            df_macro = load_macro(
                macro_key=macro_key,
                engine=engine,
                start_date=start_date,
                end_date=end_date
            )

            loaded_macros.append(macro_key)

            if merged_df is None:
                merged_df = df_macro

            else:
                merged_df = pd.merge(
                    merged_df,
                    df_macro,
                    on="snapped_at",
                    how=how
                )

        except Exception as e:
            print(f"ERRORR loading macro {macro_key}: {e}")

    if merged_df is None or merged_df.empty:
        raise ValueError("No macro indicator was loaded.")

    merged_df = merged_df.sort_values("snapped_at").reset_index(drop=True)

    macro_cols = [
        col for col in merged_df.columns
        if col != "snapped_at"
    ]

    if forward_fill:
        merged_df[macro_cols] = merged_df[macro_cols].ffill()

    return merged_df, loaded_macros


# =========================
# CARREGAR ATIVO DE MERCADO
# =========================

def load_asset_market(asset_key, engine=None, start_date=None, end_date=None):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Market asset not found: {asset_key}")

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

    print(
        f"{asset_key:35s} | "
        f"{asset['display_name']:55s} | "
        f"{len(df):7d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# ALINHAR MACRO COM MERCADO
# =========================

def alinhar_macro_com_market(
    macro_key,
    market_asset,
    engine=None,
    start_date=None,
    end_date=None,
    how="outer",
    forward_fill=True
):
    if engine is None:
        engine = get_engine()

    print("\n" + "=" * 130)
    print(f"Aligning macro with market: {macro_key} vs {market_asset}")
    print("=" * 130)

    df_macro = load_macro(
        macro_key=macro_key,
        engine=engine,
        start_date=start_date,
        end_date=end_date
    )

    df_market = load_asset_market(
        asset_key=market_asset,
        engine=engine,
        start_date=start_date,
        end_date=end_date
    )

    merged = align_macro_to_market_calendar(
        macro_df=df_macro,
        market_df=df_market,
        macro_column=macro_key,
        market_column=market_asset,
    )

    if merged.empty:
        raise ValueError(
            f"No aligned observations for {macro_key} vs {market_asset}"
        )

    print(f"Aligned market observations: {len(merged)}")
    print(f"Minimum date: {merged['snapped_at'].min().date()}")
    print(f"Maximum date: {merged['snapped_at'].max().date()}")

    return merged


def alinhar_multiplos_macro_com_market(
    macro_keys,
    market_assets,
    engine=None,
    start_date=None,
    end_date=None,
    how="outer",
    forward_fill=True
):
    if engine is None:
        engine = get_engine()

    print("\n" + "=" * 130)
    print("Aligning multiple macro indicators with multiple market assets")
    print("=" * 130)

    df_macro, loaded_macros = load_multiplos_macro(
        macro_keys=macro_keys,
        engine=engine,
        start_date=start_date,
        end_date=end_date,
        how=how,
        forward_fill=forward_fill
    )

    merged_df = df_macro.copy()
    loaded_markets = []

    print("\nLoading market assets:")
    print("-" * 130)

    for market_asset in market_assets:
        try:
            df_market = load_asset_market(
                asset_key=market_asset,
                engine=engine,
                start_date=start_date,
                end_date=end_date
            )

            loaded_markets.append(market_asset)

            merged_df = pd.merge(
                merged_df,
                df_market,
                on="snapped_at",
                how=how
            )

        except Exception as e:
            print(f"ERRORR loading market {market_asset}: {e}")

    merged_df = merged_df.sort_values("snapped_at").reset_index(drop=True)

    cols = [
        col for col in merged_df.columns
        if col != "snapped_at"
    ]

    if forward_fill:
        merged_df[cols] = merged_df[cols].ffill()

    required_cols = loaded_macros + loaded_markets

    merged_df = merged_df.dropna(
        subset=required_cols,
        how="all"
    ).reset_index(drop=True)

    if merged_df.empty:
        raise ValueError("No aligned data.")

    print("\nData finais alinhados:")
    print(f"Rows: {len(merged_df)}")
    print(f"Minimum date: {merged_df['snapped_at'].min().date()}")
    print(f"Maximum date: {merged_df['snapped_at'].max().date()}")
    print(f"Macros carregados: {loaded_macros}")
    print(f"Markets carregados: {loaded_markets}")

    return merged_df, loaded_macros, loaded_markets


# =========================
# TRANSFORMATIONS
# =========================

def normalizar_base_100(df, exclude_cols=None):
    if exclude_cols is None:
        exclude_cols = ["snapped_at"]

    normalized_df = pd.DataFrame()
    normalized_df["snapped_at"] = df["snapped_at"]

    value_cols = [
        col for col in df.columns
        if col not in exclude_cols
    ]

    for col in value_cols:
        series = pd.to_numeric(
            df[col],
            errors="coerce"
        )

        first_valid = series.dropna()

        if first_valid.empty:
            print(f"Warning: {col} sem valores valid para normalizar.")
            continue

        base_value = first_valid.iloc[0]

        if base_value == 0:
            print(f"Warning: {col} tem valor base zero.")
            continue

        normalized_df[col] = (series / base_value) * 100

    return normalized_df


def calcular_variacoes(df, windows=None):
    if windows is None:
        windows = [30, 90, 180, 252]

    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    value_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in value_cols:
        for window in windows:
            df[f"{col}_pct_change_{window}d"] = df[col].pct_change(
                periods=window,
                fill_method=None
            )
            df[f"{col}_abs_change_{window}d"] = df[col] - df[col].shift(window)

    return df


def calcular_returns_diarios(df):
    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    returns_df = pd.DataFrame()
    returns_df["snapped_at"] = df["snapped_at"]

    value_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in value_cols:
        returns_df[f"{col}_return_1d"] = df[col].pct_change(fill_method=None)

    returns_df = returns_df.replace([float("inf"), float("-inf")], pd.NA)

    return returns_df


# =========================
# QUICK SUMMARY
# =========================

def summary_dataset(df):
    print("\n" + "=" * 120)
    print("RESUMO DO DATASET")
    print("=" * 120)

    print(f"Rows: {len(df)}")

    if "snapped_at" in df.columns and not df.empty:
        print(f"Minimum date: {df['snapped_at'].min()}")
        print(f"Maximum date: {df['snapped_at'].max()}")

    value_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    rows = []

    for col in value_cols:
        series = pd.to_numeric(
            df[col],
            errors="coerce"
        )

        non_null = series.dropna()

        if non_null.empty:
            rows.append({
                "column": col,
                "non_null": 0,
                "null_pct": 100,
                "first_value": None,
                "last_value": None,
                "min": None,
                "max": None
            })

            continue

        rows.append({
            "column": col,
            "non_null": int(non_null.count()),
            "null_pct": round(series.isna().mean() * 100, 2),
            "first_value": round(non_null.iloc[0], 4),
            "last_value": round(non_null.iloc[-1], 4),
            "min": round(non_null.min(), 4),
            "max": round(non_null.max(), 4)
        })

    summary_df = pd.DataFrame(rows)

    print(summary_df)
    print("=" * 120)

    return summary_df


# =========================
# QUICK TEST
# =========================

if __name__ == "__main__":
    engine = get_engine()

    print("\nQuick test macro_data_loader.py")

    test_macro = "FED_M2"
    test_market = "BTC"

    df_test = alinhar_macro_com_market(
        macro_key=test_macro,
        market_asset=test_market,
        engine=engine,
        start_date="2020-01-01",
        end_date=None
    )

    summary_dataset(df_test)

    df_norm = normalizar_base_100(df_test)

    print("\nDataset normalizado:")
    print(df_norm.head())
