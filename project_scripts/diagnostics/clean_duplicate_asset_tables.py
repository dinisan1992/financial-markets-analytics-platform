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

ASSETS_TO_CLEAN = [
    "GOLD",
    "DXY"
]

CLEAN_TABLE_SUFFIX = "_clean"


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# LIMPAR TABELA
# =========================

def clean_tabela(asset_key):
    asset = ASSETS[asset_key]

    original_table = asset["table_name"]
    clean_table = f"{original_table}{CLEAN_TABLE_SUFFIX}"

    print("\n" + "=" * 100)
    print(f"A clean: {asset_key}")
    print(f"Original table: {original_table}")
    print(f"Clean table: {clean_table}")
    print("=" * 100)

    query = f"""
    SELECT *
    FROM `{original_table}`
    ORDER BY snapped_at;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError(f"Empty table: {original_table}")

    original_rows = len(df)

    df["snapped_at"] = pd.to_datetime(
        df["snapped_at"],
        errors="coerce"
    )

    df = df.dropna(subset=["snapped_at"])

    # Ordenar e manter apenas a last linha por data
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
    print(f"Minimum date: {df_clean['snapped_at'].min().date()}")
    print(f"Maximum date: {df_clean['snapped_at'].max().date()}")

    # Write new clean table
    df_clean.to_sql(
        name=clean_table,
        con=engine,
        if_exists="replace",
        index=False,
        chunksize=500
    )

    print(f"Table created successfully: {clean_table}")

    return {
        "asset_key": asset_key,
        "original_table": original_table,
        "clean_table": clean_table,
        "original_rows": original_rows,
        "clean_rows": clean_rows,
        "removed_rows": removed_rows,
        "min_date": df_clean["snapped_at"].min().date(),
        "max_date": df_clean["snapped_at"].max().date()
    }


# =========================
# MAIN
# =========================

def main():
    print("\nA iniciar limpeza de tabelas duplicadas...")

    resultados = []

    for asset_key in ASSETS_TO_CLEAN:
        try:
            resultado = clean_tabela(asset_key)
            resultados.append(resultado)

        except Exception as e:
            print(f"ERROR in {asset_key}: {e}")

            resultados.append({
                "asset_key": asset_key,
                "error": str(e)
            })

    report_df = pd.DataFrame(resultados)

    print("\n" + "=" * 100)
    print("SUMMARY FINAL")
    print("=" * 100)
    print(report_df)
    print("=" * 100)

    report_df.to_csv(
        "clean_duplicate_tables_report.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nReport saved to: clean_duplicate_tables_report.csv")
    print("Limpeza completed.")


if __name__ == "__main__":
    main()

