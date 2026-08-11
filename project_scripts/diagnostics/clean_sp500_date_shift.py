from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine

from config import get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# SETTINGS
# =========================

ASSET_KEY = "SP500"

ORIGINAL_TABLE = ASSETS[ASSET_KEY]["table_name"]
CLEAN_TABLE = "sp500_analysis_clean"

SHIFT_DAYS = -1


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# LIMPAR / AJUSTAR SP500
# =========================

def main():
    print("\nCreating clean SP500 table with adjusted dates...")
    print(f"Original table: {ORIGINAL_TABLE}")
    print(f"Clean table: {CLEAN_TABLE}")
    print(f"Ajuste de datas: {SHIFT_DAYS} dia")

    query = f"""
    SELECT *
    FROM `{ORIGINAL_TABLE}`
    ORDER BY snapped_at;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError(f"Empty table: {ORIGINAL_TABLE}")

    original_rows = len(df)

    df["snapped_at"] = pd.to_datetime(
        df["snapped_at"],
        errors="coerce"
    )

    df = df.dropna(subset=["snapped_at"])
    df = df.sort_values("snapped_at").reset_index(drop=True)

    # Shift dates back by 1 day
    df["snapped_at"] = df["snapped_at"] + pd.DateOffset(days=SHIFT_DAYS)

    # Remove possible duplicates after the shift
    df = df.sort_values("snapped_at")
    df_clean = df.drop_duplicates(
        subset=["snapped_at"],
        keep="last"
    ).copy()

    clean_rows = len(df_clean)
    removed_rows = original_rows - clean_rows

    print(f"Rows originais: {original_rows}")
    print(f"Rows limpas: {clean_rows}")
    print(f"Duplicados removidos: {removed_rows}")

    print(f"Original minimum date: {pd.to_datetime(pd.read_sql(f'SELECT MIN(snapped_at) AS min_date FROM `{ORIGINAL_TABLE}`', engine)['min_date'].iloc[0]).date()}")
    print(f"Original maximum date: {pd.to_datetime(pd.read_sql(f'SELECT MAX(snapped_at) AS max_date FROM `{ORIGINAL_TABLE}`', engine)['max_date'].iloc[0]).date()}")

    print(f"Clean minimum date: {df_clean['snapped_at'].min().date()}")
    print(f"Clean maximum date: {df_clean['snapped_at'].max().date()}")

    df_clean.to_sql(
        name=CLEAN_TABLE,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=500
    )

    print(f"\nTable created successfully: {CLEAN_TABLE}")

    report = pd.DataFrame([
        {
            "asset_key": ASSET_KEY,
            "original_table": ORIGINAL_TABLE,
            "clean_table": CLEAN_TABLE,
            "shift_days": SHIFT_DAYS,
            "original_rows": original_rows,
            "clean_rows": clean_rows,
            "removed_rows": removed_rows,
            "min_date_clean": df_clean["snapped_at"].min().date(),
            "max_date_clean": df_clean["snapped_at"].max().date()
        }
    ])

    report.to_csv(
        "clean_sp500_date_shift_report.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("Report saved to: clean_sp500_date_shift_report.csv")
    print("\nCompleted.")


if __name__ == "__main__":
    main()

