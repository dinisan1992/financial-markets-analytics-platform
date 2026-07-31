from pathlib import Path
import argparse
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import os
import pandas as pd
import mysql.connector
import numpy as np

from config import DB_CONFIG
from asset_config import ASSETS

from indicators import calcular_indicadores

from risk_detection import identificar_possivel_manipulacao_forte

from charts import gerar_dashboard
from services.legacy_import_service import (
    format_dry_run_report,
    preview_legacy_csv_against_connection,
)


# =========================
# SETTINGS YUAN
# =========================
CSV_PATH = ASSETS["YUAN"]["csv_path"]

TABLE_NAME = "yuan_analysis"

# Se estiver False:
# - calculates indicators in memory;
# - gera chart;
# - does NOT update indicators/manipulation flags in SQL.
#
# Se estiver True:
# - calcula indicadores;
# - updates indicadores no SQL;
# - updates manipulation no SQL.
UPDATE_SQL = False


# =========================
# CONNECT TO THE DATABASE
# =========================
def conectar_bd(config):
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    return conn, cursor


# =========================
# CONVERTER VALORES PARA MYSQL
# =========================
def converter_valor_mysql(valor):
    if pd.isna(valor):
        return None

    if isinstance(valor, pd.Timestamp):
        return valor.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(valor, np.generic):
        return valor.item()

    return valor


# =========================
# CSV IMPORT PREVIEW
# =========================
def preview_csv_import_yuan(csv_path, conn):
    if not os.path.exists(csv_path):
        print(f"CSV not found; import preview skipped: {csv_path}")
        return None

    report, _ = preview_legacy_csv_against_connection(
        asset="YUAN",
        table=TABLE_NAME,
        csv_path=csv_path,
        connection=conn,
    )
    print(format_dry_run_report(report))
    return report


# =========================
# ATUALIZAR INDICADORES SQL
# =========================
def update_indicadores_yuan_sql(df, cursor, conn):
    """
    Updates only existing legacy indicators in the yuan_analysis.

    The new advanced indicators calculated in indicators.py
    are NOT sent to SQL at this stage.
    """

    update_sql = f"""
        UPDATE {TABLE_NAME} SET
            rsi=%s,
            ema_9=%s,
            ema_12=%s,
            ema_26=%s,
            ema_50=%s,
            ema_100=%s,
            ema_200=%s,
            volume_sma_9=%s,
            bb_middle=%s,
            bb_upper=%s,
            bb_lower=%s,
            stoch_rsi=%s,
            macd=%s,
            macd_signal=%s,
            momentum_10=%s,
            atr=%s,
            adx=%s,
            cci=%s,
            obv=%s,
            macd_percent=%s,
            price_change_pct=%s
        WHERE snapped_at=%s
    """

    for _, r in df.iterrows():
        valores = [
            r["rsi"],
            r["ema_9"],
            r["ema_12"],
            r["ema_26"],
            r["ema_50"],
            r["ema_100"],
            r["ema_200"],
            r["volume_sma_9"],
            r["bb_middle"],
            r["bb_upper"],
            r["bb_lower"],
            r["stoch_rsi_k"],
            r["macd"],
            r["macd_signal"],
            r["momentum_10"],
            r["atr"],
            r["adx"],
            r["cci"],
            r["obv"],
            r["macd_percent"],
            r["price_change_pct"],
            r["snapped_at"]
        ]

        valores = [converter_valor_mysql(v) for v in valores]

        cursor.execute(update_sql, valores)

    conn.commit()

    print("✅ YUAN indicators updated in the database.")


# =========================
# UPDATE MANIPULATION FLAGS IN SQL
# =========================
def update_manipulacao_yuan_sql(df, cursor, conn):
    update_sql = f"""
        UPDATE {TABLE_NAME}
        SET manipulation=%s
        WHERE snapped_at=%s
    """

    flags_df = df[df["manipulation"].notnull()].copy()

    if flags_df.empty:
        print("✅ No new manipulation flags to update.")
        return

    for _, row in flags_df.iterrows():
        cursor.execute(
            update_sql,
            (
                row["manipulation"],
                converter_valor_mysql(row["snapped_at"])
            )
        )

    conn.commit()

    print(f"✅ {len(flags_df)} flags de manipulation YUAN updatesdas no SQL.")


# =========================
# MAIN FUNCTION
# =========================
def build_parser():
    parser = argparse.ArgumentParser(description="Validate YUAN market data safely.")
    parser.add_argument(
        "--dry-run-import",
        action="store_true",
        help="Compare the configured CSV with SQL without writing to the database.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    conn = None
    cursor = None

    try:
        # =========================
        # CONNECTION
        # =========================
        conn, cursor = conectar_bd(DB_CONFIG)

        # =========================
        # CSV IMPORT
        # =========================
        if args.dry_run_import:
            preview_csv_import_yuan(csv_path=CSV_PATH, conn=conn)
            return
        print("Base CSV import is disabled. Use --dry-run-import for a read-only preview.")

        # =========================
        # LER DADOS MYSQL
        # =========================
        df = pd.read_sql(
            f"""
            SELECT
                snapped_at,
                price,
                total_volume
            FROM {TABLE_NAME}
            ORDER BY snapped_at ASC
            """,
            conn
        )

        if df.empty:
            print("❌ No data available para YUAN.")
            return

        print(f"✅ Data loaded from table {TABLE_NAME}: {len(df)} rows")

        # =========================
        # FORMATAR DATAS
        # =========================
        df["snapped_at"] = pd.to_datetime(
            df["snapped_at"]
            .astype(str)
            .str.replace(" UTC", "", regex=False),
            errors="coerce"
        )

        df = df.dropna(subset=["snapped_at"])

        # =========================
        # VOLUME
        # =========================
        df["volume"] = df["total_volume"]

        # =========================
        # CREATE SYNTHETIC CANDLESTICK
        # =========================
        df["open"] = df["price"].shift(1)

        df["close"] = df["price"]

        df["high"] = (
            df[["open", "close"]]
            .max(axis=1)
            * 1.01
        )

        df["low"] = (
            df[["open", "close"]]
            .min(axis=1)
            * 0.99
        )

        # Remove primeira linha com NaN no open
        df = df.dropna().reset_index(drop=True)

        if df.empty:
            print("❌ Insufficient data after candle creation.")
            return

        # =========================
        # CALCULAR INDICADORES
        # =========================
        df = calcular_indicadores(df)

        # =========================
        # DETECT MANIPULATION
        # =========================
        df["manipulation"] = None

        flags = identificar_possivel_manipulacao_forte(df)

        for data_flag, motivo in flags:
            df.loc[
                df["snapped_at"] == data_flag,
                "manipulation"
            ] = motivo

        # =========================
        # ATUALIZAR SQL OPCIONAL
        # =========================
        if UPDATE_SQL:
            print("💾 UPDATE_SQL=True -> Updatesndo indicadores e flags no SQL...")

            update_indicadores_yuan_sql(
                df=df,
                cursor=cursor,
                conn=conn
            )

            update_manipulacao_yuan_sql(
                df=df,
                cursor=cursor,
                conn=conn
            )

        else:
            print("⏭️ UPDATE_SQL=False -> SQL not updated. Generating chart with data calculated in memory.")

        # =========================
        # DASHBOARD
        # =========================
        gerar_dashboard(df)

        # =========================
        # LOG
        # =========================
        if flags:
            print("\n⚠️ Possible manipulation signals detected for YUAN:")

            for data, motivo in flags:
                print(f"{data}: {motivo}")

        else:
            print("\n✅ No clear manipulation signal identified no YUAN.")

        print("✅ Processing YUAN completed.")

    except Exception as e:
        print(f"❌ Error during processing YUAN: {e}")

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None:
            conn.close()


# =========================
# EXECUTION
# =========================
if __name__ == "__main__":
    main()

