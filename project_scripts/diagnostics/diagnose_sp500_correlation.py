from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# SETTINGS
# =========================

ASSETS_TO_COMPARE = [
    "SP500",
    "NASDAQ100",
    "DOWJONES",
    "RUSSELL2000"
]

START_DATE = "2020-01-01"
END_DATE = None

EXPORT_REPORTS = True


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# LOAD PRICES
# =========================

def load_precos(asset_key):
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

    if START_DATE is not None:
        df = df[df["snapped_at"] >= pd.to_datetime(START_DATE)]

    if END_DATE is not None:
        df = df[df["snapped_at"] <= pd.to_datetime(END_DATE)]

    df = df[["snapped_at", "price"]].copy()
    df = df.rename(columns={"price": asset_key})

    print(
        f"{asset_key:12s} | "
        f"{ASSETS[asset_key]['display_name']:35s} | "
        f"{len(df):6d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# MERGE PRICES
# =========================

def juntar_precos():
    merged = None

    print("\nLoading prices:")
    print("-" * 90)

    for asset_key in ASSETS_TO_COMPARE:
        df = load_precos(asset_key)

        if merged is None:
            merged = df
        else:
            merged = pd.merge(
                merged,
                df,
                on="snapped_at",
                how="inner"
            )

    merged = merged.sort_values("snapped_at").reset_index(drop=True)

    return merged


# =========================
# CALCULAR RETURNS
# =========================

def calcular_returns(precos_df):
    returns_df = pd.DataFrame()
    returns_df["snapped_at"] = precos_df["snapped_at"]

    for asset_key in ASSETS_TO_COMPARE:
        returns_df[asset_key] = precos_df[asset_key].pct_change()

    returns_df = returns_df.dropna().reset_index(drop=True)

    return returns_df


# =========================
# NORMALIZE BASE 100
# =========================

def normalizar_base_100(precos_df):
    norm_df = pd.DataFrame()
    norm_df["snapped_at"] = precos_df["snapped_at"]

    for asset_key in ASSETS_TO_COMPARE:
        first_value = precos_df[asset_key].iloc[0]
        norm_df[asset_key] = (precos_df[asset_key] / first_value) * 100

    return norm_df


# =========================
# ANALYZE DIVERGENCES
# =========================

def analisar_divergencias(returns_df):
    df = returns_df.copy()

    # Absolute return differences between SP500 and the others
    for asset_key in ["NASDAQ100", "DOWJONES", "RUSSELL2000"]:
        df[f"diff_SP500_{asset_key}"] = (
            df["SP500"] - df[asset_key]
        ).abs()

    diff_cols = [
        col for col in df.columns
        if col.startswith("diff_")
    ]

    df["max_diff_vs_SP500"] = df[diff_cols].max(axis=1)

    maiores_divergencias = df.sort_values(
        "max_diff_vs_SP500",
        ascending=False
    ).head(30)

    return maiores_divergencias


# =========================
# MAIN
# =========================

def main():
    print("\nSP500 vs US indices diagnostic")
    print(f"Period: {START_DATE} -> {END_DATE if END_DATE else 'end'}")

    precos_df = juntar_precos()

    print("\nPrices on common dates:")
    print(f"Rows comuns: {len(precos_df)}")
    print(f"Common minimum date: {precos_df['snapped_at'].min().date()}")
    print(f"Common maximum date: {precos_df['snapped_at'].max().date()}")

    print("\nFirst price rows:")
    print(precos_df.head(10))

    print("\nLast price rows:")
    print(precos_df.tail(10))

    returns_df = calcular_returns(precos_df)

    print("\nReturns correlation:")
    corr = returns_df[ASSETS_TO_COMPARE].corr()
    print(corr.round(4))

    print("\nStatistical return summary:")
    print(
        returns_df[ASSETS_TO_COMPARE]
        .describe()
        .T
        .round(6)
    )

    norm_df = normalizar_base_100(precos_df)

    print("\nPerformance normalizada final:")
    final_values = norm_df[ASSETS_TO_COMPARE].iloc[-1].sort_values(ascending=False)
    print(final_values.round(2))

    maiores_divergencias = analisar_divergencias(returns_df)

    print("\nLargest daily divergences: SP500 vs other indices:")
    cols_to_show = [
        "snapped_at",
        "SP500",
        "NASDAQ100",
        "DOWJONES",
        "RUSSELL2000",
        "diff_SP500_NASDAQ100",
        "diff_SP500_DOWJONES",
        "diff_SP500_RUSSELL2000",
        "max_diff_vs_SP500"
    ]

    print(maiores_divergencias[cols_to_show].round(5))

    if EXPORT_REPORTS:
        precos_df.to_csv(
            "diagnose_sp500_prices.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        returns_df.to_csv(
            "diagnose_sp500_returns.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        norm_df.to_csv(
            "diagnose_sp500_normalized.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        maiores_divergencias.to_csv(
            "diagnose_sp500_largest_divergences.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print("\nReports exported:")
        print("diagnose_sp500_prices.csv")
        print("diagnose_sp500_returns.csv")
        print("diagnose_sp500_normalized.csv")
        print("diagnose_sp500_largest_divergences.csv")

    print("\nDiagnostic completed.")


if __name__ == "__main__":
    main()

