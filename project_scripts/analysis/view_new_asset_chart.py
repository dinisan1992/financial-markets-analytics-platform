from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine

from config import get_sqlalchemy_database_url
from asset_config import ASSETS
from indicators import calcular_indicadores
from risk_detection import identificar_possivel_manipulacao_forte
from charts import gerar_dashboard


# =========================
# ESCOLHER ATIVO
# =========================

ASSET_KEY = "BRENT_OIL"

# Para not pesar demasiado no chart.
# Use None to load everything.
LIMIT_LAST_ROWS = None
# Example mais leve:
# LIMIT_LAST_ROWS = 3000


# =========================
# DATABASE CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# CARREGAR DADOS DO SQL
# =========================

def load_data(asset_key):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Asset not found in ASSETS: {asset_key}")

    asset = ASSETS[asset_key]
    table_name = asset["table_name"]

    query = f"""
    SELECT
        snapped_at,
        price,
        open,
        high,
        low,
        close,
        adj_close,
        total_volume
    FROM `{table_name}`
    ORDER BY snapped_at;
    """

    df = pd.read_sql(
        query,
        engine
    )

    if df.empty:
        raise ValueError(f"Empty table: {table_name}")

    df["snapped_at"] = pd.to_datetime(df["snapped_at"])

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

    # O projeto antigo usa a coluna "volume"
    df["volume"] = df["total_volume"]

    # Some series such as VIX, yields or financial conditions have no volume.
    # Para o chart/indicadores not rebentarem, usamos 0.
    df["volume"] = df["volume"].fillna(0)

    df = df.dropna(subset=["snapped_at", "close"])
    df = df.sort_values("snapped_at").reset_index(drop=True)

    if LIMIT_LAST_ROWS is not None:
        df = df.tail(LIMIT_LAST_ROWS).reset_index(drop=True)

    return df, asset


# =========================
# APPLY MANIPULATION / ANOMALY FLAGS
# =========================

def adicionar_flags_manipulacao(df):
    df = df.copy()

    df["manipulation"] = None

    try:
        flags = identificar_possivel_manipulacao_forte(df)

        flags_dict = {
            pd.to_datetime(date): motivo
            for date, motivo in flags
        }

        df["manipulation"] = df["snapped_at"].map(flags_dict)

    except Exception as e:
        print(f"Warning: not foi possible calcular flags de manipulation: {e}")
        df["manipulation"] = None

    return df


# =========================
# MAIN
# =========================

def main():
    print("\nA load novo asset para chart...")
    print(f"Asset: {ASSET_KEY}")

    df, asset = load_data(ASSET_KEY)

    print(f"Table SQL: {asset['table_name']}")
    print(f"Nome: {asset['display_name']}")
    print(f"Tipo: {asset['market_type']}")
    print(f"Rows carregadas: {len(df)}")
    print(f"Minimum date: {df['snapped_at'].min().date()}")
    print(f"Maximum date: {df['snapped_at'].max().date()}")

    print("\nA calcular indicadores...")
    df = calcular_indicadores(df)

    print("A calcular flags/anomalies...")
    df = adicionar_flags_manipulacao(df)

    print("Generating chart...")
    gerar_dashboard(df)

    print("\nChart completed.")


if __name__ == "__main__":
    main()

