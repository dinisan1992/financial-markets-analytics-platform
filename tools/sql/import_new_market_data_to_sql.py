from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import create_engine, text


# =========================
# GARANTIR IMPORTS DA RAIZ DO PROJETO
# =========================

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

from config import get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# SETTINGS
# =========================

engine = create_engine(
    get_sqlalchemy_database_url(),
    pool_pre_ping=True
)

# First test only these 3
TEST_MODE = False

TEST_ASSETS = [
    "NASDAQ100",
    "VIX",
    "FINANCIAL_CONDITIONS"
]

# Depois, quando o teste estiver validado, mudar TEST_MODE para False
NEW_ASSET_KEYS = [
    "NASDAQ100",
    "DOWJONES",
    "RUSSELL2000",
    "EUROSTOXX50",
    "DAX",
    "CAC40",
    "NIKKEI225",
    "EMERGING_MARKETS",

    "VIX",
    "MOVE_INDEX",

    "BRENT_OIL",
    "WTI_OIL",
    "NATURAL_GAS",
    "COPPER",
    "SILVER",
    "WHEAT",
    "CORN",

    "YEN",
    "SWISS_FRANC",

    "US3M",
    "US10Y",
    "US2Y",
    "US30Y",
    "GERMANY10Y",
    "UK10Y",
    "JAPAN10Y",

    "FINANCIAL_CONDITIONS",
    "TED_SPREAD"
]


# =========================
# CRIAR TABELA SQL
# =========================

def create_tabela(table_name):
    query = f"""
    CREATE TABLE IF NOT EXISTS `{table_name}` (
        snapped_at DATE PRIMARY KEY,
        price DOUBLE,
        open DOUBLE,
        high DOUBLE,
        low DOUBLE,
        close DOUBLE,
        adj_close DOUBLE,
        total_volume DOUBLE NULL,
        source_file VARCHAR(255),
        inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    with engine.begin() as conn:
        conn.execute(text(query))


# =========================
# PREPARAR DATAFRAME
# =========================

def preparar_dataframe(csv_path):
    df = pd.read_csv(
        csv_path,
        sep=";",
        encoding="utf-8-sig"
    )

    required_cols = [
        "snapped_at",
        "price",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "total_volume",
        "source_file"
    ]

    missing_cols = [
        col for col in required_cols
        if col not in df.columns
    ]

    if missing_cols:
        raise ValueError(f"Missing columns: {missing_cols}")

    df = df[required_cols].copy()

    df["snapped_at"] = pd.to_datetime(
        df["snapped_at"],
        errors="coerce"
    ).dt.date

    numeric_cols = [
        "price",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "total_volume"
    ]

    for col in numeric_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df = df.dropna(subset=["snapped_at", "price"])
    df = df.drop_duplicates(subset=["snapped_at"], keep="last")
    df = df.sort_values("snapped_at")

    return df


# =========================
# CONVERTER NaN PARA None
# =========================

def converter_nan_para_none(df):
    df = df.copy()

    df = df.astype(object)

    df = df.where(pd.notnull(df), None)

    return df


# =========================
# INSERIR DADOS EM BLOCOS
# =========================

def inserir_data(df, table_name, chunk_size=500):
    insert_query = f"""
    INSERT INTO `{table_name}` (
        snapped_at,
        price,
        open,
        high,
        low,
        close,
        adj_close,
        total_volume,
        source_file
    )
    VALUES (
        :snapped_at,
        :price,
        :open,
        :high,
        :low,
        :close,
        :adj_close,
        :total_volume,
        :source_file
    )
    ON DUPLICATE KEY UPDATE
        price = VALUES(price),
        open = VALUES(open),
        high = VALUES(high),
        low = VALUES(low),
        close = VALUES(close),
        adj_close = VALUES(adj_close),
        total_volume = VALUES(total_volume),
        source_file = VALUES(source_file);
    """

    df = converter_nan_para_none(df)

    records = df.to_dict(orient="records")

    total = len(records)

    if total == 0:
        raise ValueError("No records to insert.")

    with engine.begin() as conn:
        for start in range(0, total, chunk_size):
            end = start + chunk_size
            chunk = records[start:end]

            conn.execute(text(insert_query), chunk)

            print(
                f"  Inseridas rows {start + 1} "
                f"a {min(end, total)} de {total}"
            )


# =========================
# VALIDAR TABELA
# =========================

def validar_tabela(table_name):
    query = f"""
    SELECT
        COUNT(*) AS total_rows,
        MIN(snapped_at) AS min_date,
        MAX(snapped_at) AS max_date
    FROM `{table_name}`;
    """

    with engine.begin() as conn:
        result = conn.execute(text(query)).fetchone()

    return {
        "total_rows": result[0],
        "min_date": result[1],
        "max_date": result[2]
    }


# =========================
# IMPORTAR UM ATIVO
# =========================

def importar_asset(asset_key):
    asset = ASSETS[asset_key]

    csv_path = Path(asset["csv_path"])
    table_name = asset["table_name"]

    print("\n" + "=" * 70)
    print(f"A importar: {asset_key}")
    print(f"CSV: {csv_path}")
    print(f"Table: {table_name}")
    print("=" * 70)

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    create_tabela(table_name)

    df = preparar_dataframe(csv_path)

    if df.empty:
        raise ValueError(f"Empty DataFrame after cleaning: {asset_key}")

    print(f"Rows prepared for import: {len(df)}")

    inserir_data(
        df=df,
        table_name=table_name,
        chunk_size=500
    )

    summary = validar_tabela(table_name)

    print(f"OK: {asset_key}")
    print(f"Rows in table: {summary['total_rows']}")
    print(f"Minimum date: {summary['min_date']}")
    print(f"Maximum date: {summary['max_date']}")

    return {
        "asset_key": asset_key,
        "table_name": table_name,
        "csv_rows": len(df),
        "sql_rows": summary["total_rows"],
        "min_date": summary["min_date"],
        "max_date": summary["max_date"],
        "status": "success",
        "error": None
    }


# =========================
# MAIN
# =========================

def main():
    print("\nStarting import of new market data into SQL...")
    print(f"Base do projeto: {BASE_DIR}")

    if TEST_MODE:
        asset_keys = TEST_ASSETS
        print("\nMODO TESTE ATIVO")
        print(f"Assets a importar: {asset_keys}")
    else:
        asset_keys = NEW_ASSET_KEYS
        print("\nMODO COMPLETO ATIVO")
        print(f"Assets a importar: {len(asset_keys)}")

    resultados = []

    for asset_key in asset_keys:
        try:
            resultado = importar_asset(asset_key)
            resultados.append(resultado)

        except Exception as e:
            print(f"ERROR in {asset_key}: {e}")

            resultados.append({
                "asset_key": asset_key,
                "table_name": ASSETS.get(asset_key, {}).get("table_name"),
                "csv_rows": None,
                "sql_rows": None,
                "min_date": None,
                "max_date": None,
                "status": "error",
                "error": str(e)
            })

    print("\n" + "=" * 70)
    print("SUMMARY FINAL")
    print("=" * 70)

    summary_df = pd.DataFrame(resultados)

    print(summary_df)

    output_path = (
        BASE_DIR
        / "new_market_data"
        / "reports"
        / "sql_import_report.csv"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary_df.to_csv(
        output_path,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print(f"\nReport saved to: {output_path}")

    total = len(resultados)
    success = sum(1 for r in resultados if r["status"] == "success")
    errors = sum(1 for r in resultados if r["status"] == "error")

    print(f"\nTotal: {total}")
    print(f"Success: {success}")
    print(f"Errors: {errors}")
    print("\nImport completed.")


if __name__ == "__main__":
    main()
