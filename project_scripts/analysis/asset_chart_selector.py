from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS
from indicators import calcular_indicadores
from risk_detection import identificar_possivel_manipulacao_forte
from charts import gerar_dashboard


# =========================
# SETTINGS
# =========================

LIMIT_LAST_ROWS = None
# Para charts mais leves, podes usar:
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
# ASSET LISTS
# =========================

def obter_assets_disponiveis():
    """
    Returns only assets configured in asset_config.py.
    """

    assets = []

    for asset_key, asset_data in ASSETS.items():
        assets.append({
            "asset_key": asset_key,
            "display_name": asset_data["display_name"],
            "market_type": asset_data["market_type"],
            "table_name": asset_data["table_name"],
            "symbol": asset_data["symbol"]
        })

    return assets


def mostrar_menu(assets):
    print("\n" + "=" * 80)
    print("CHART SELECTOR - MARKET ANALYTICS")
    print("=" * 80)

    for i, asset in enumerate(assets, start=1):
        print(
            f"{i:02d} - "
            f"{asset['display_name']} "
            f"({asset['symbol']}) "
            f"| {asset['market_type']}"
        )

    print("=" * 80)
    print("0 - Exit")
    print("=" * 80)


def chooser_asset(assets):
    while True:
        choice = input("\nChoose the asset number: ").strip()

        if choice == "0":
            return None

        if not choice.isdigit():
            print("Invalid choice. Enter the number only.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(assets):
            print("Number outside the list.")
            continue

        return assets[choice_num - 1]


# =========================
# CARREGAR DADOS
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

    # Compatibilidade com o resto do projeto
    df["volume"] = df["total_volume"]

    # Series como VIX, yields, TED Spread, Financial Conditions podem not ter volume
    df["volume"] = df["volume"].fillna(0)

    df = df.dropna(subset=["snapped_at", "close"])
    df = df.sort_values("snapped_at").reset_index(drop=True)

    if LIMIT_LAST_ROWS is not None:
        df = df.tail(LIMIT_LAST_ROWS).reset_index(drop=True)

    return df, asset


# =========================
# ANOMALY / MANIPULATION FLAGS
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
        print(f"Warning: not foi possible calcular flags/anomalies: {e}")
        df["manipulation"] = None

    return df


# =========================
# GENERATE CHART
# =========================

def gerar_grafico_asset(asset_key):
    print("\n" + "=" * 80)
    print(f"A load chart para: {asset_key}")
    print("=" * 80)

    df, asset = load_data(asset_key)

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
    gerar_dashboard(
        df,
        asset_name=asset["display_name"]
    )

    print("\nChart completed.")


# =========================
# MAIN
# =========================

def main():
    assets = obter_assets_disponiveis()

    while True:
        mostrar_menu(assets)

        asset_escolhido = chooser_asset(assets)

        if asset_escolhido is None:
            print("\nExiting the chart selector.")
            break

        try:
            gerar_grafico_asset(asset_escolhido["asset_key"])

        except Exception as e:
            print(f"\nERRORR generating chart:")
            print(e)

        input("\nPressiona ENTER para voltar ao menu...")


if __name__ == "__main__":
    main()

