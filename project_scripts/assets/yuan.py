from pathlib import Path
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
# CLEAN PRICE
# =========================
def parse_price(valor):
    if pd.isna(valor):
        return np.nan

    valor = (
        str(valor)
        .replace(" ", "")
        .strip()
    )

    # Remove thousands separators, if they exist
    valor = valor.replace(",", "")

    return pd.to_numeric(
        valor,
        errors="coerce"
    )


# =========================
# PARSE VOLUME
# =========================
def parse_volume(valor):
    if pd.isna(valor):
        return 0

    valor = (
        str(valor)
        .upper()
        .replace(" ", "")
        .replace(",", "")
        .strip()
    )

    if valor in ["", "-", "NAN", "NONE"]:
        return 0

    multiplier = 1

    if valor.endswith("K"):
        multiplier = 1_000
        valor = valor[:-1]

    elif valor.endswith("M"):
        multiplier = 1_000_000
        valor = valor[:-1]

    elif valor.endswith("B"):
        multiplier = 1_000_000_000
        valor = valor[:-1]

    try:
        return float(valor) * multiplier

    except Exception:
        return 0


# =========================
# IMPORTAR CSV YUAN
# =========================
def importar_csv_yuan(csv_path, conn, cursor):
    if not os.path.exists(csv_path):
        print("No CSV found, skipping import.")
        return False

    # =========================
    # LER CSV
    # =========================
    df_csv = pd.read_csv(
        csv_path,
        sep=";",
        encoding="utf-8-sig",
        header=0
    )

    print("CSV carregado:")
    print(df_csv.head())

    # =========================
    # NORMALIZAR NOMES DAS COLUNAS
    # =========================
    df_csv.columns = [
        c.strip()
        .lower()
        .replace(" ", "_")
        .replace("%", "percent")
        for c in df_csv.columns
    ]

    print(f"Columns detetadas: {list(df_csv.columns)}")

    # =========================
    # VALIDAR COLUNAS
    # =========================
    required_cols = [
        "snapped_at",
        "price",
        "total_volume"
    ]

    for col in required_cols:
        if col not in df_csv.columns:
            print(f"❌ Required column '{col}' not found in the CSV.")
            return False

    # =========================
    # CONVERTER DATAS
    # =========================
    df_csv["snapped_at"] = pd.to_datetime(
        df_csv["snapped_at"]
        .astype(str)
        .str.replace(" UTC", "", regex=False),
        errors="coerce",
        format="%b %d, %Y"
    )

    # Fallback se o formato acima falhar
    if df_csv["snapped_at"].isna().all():
        df_csv["snapped_at"] = pd.to_datetime(
            df_csv["snapped_at"],
            errors="coerce"
        )

    # =========================
    # LIMPAR PRICE
    # =========================
    df_csv["price"] = df_csv["price"].apply(parse_price)

    # =========================
    # LIMPAR TOTAL_VOLUME
    # =========================
    df_csv["total_volume"] = df_csv["total_volume"].apply(parse_volume)

    # =========================
    # REMOVE INVALID ROWS
    # =========================
    df_csv = df_csv.dropna(
        subset=[
            "snapped_at",
            "price"
        ]
    ).reset_index(drop=True)

    # =========================
    # ORDENAR POR DATA
    # =========================
    df_csv = df_csv.sort_values(
        by="snapped_at"
    ).reset_index(drop=True)

    print(f"{len(df_csv)} rows valid after limpeza:")
    print(df_csv.head())

    if df_csv.empty:
        print("No valid data to import.")
        return False

    # =========================
    # INSERIR / ATUALIZAR DADOS BASE
    # =========================
    insert_sql = f"""
        INSERT INTO {TABLE_NAME}
            (snapped_at, price, total_volume)
        VALUES
            (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            price = VALUES(price),
            total_volume = VALUES(total_volume)
    """

    rows_processadas = 0

    for _, row in df_csv.iterrows():
        cursor.execute(
            insert_sql,
            (
                row["snapped_at"].strftime("%Y-%m-%d %H:%M:%S"),
                row["price"],
                row["total_volume"]
            )
        )

        rows_processadas += 1

    conn.commit()

    print(f"✅ {rows_processadas} rows inseridas/updatesdas em {TABLE_NAME}.")

    return rows_processadas > 0


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
def main():
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
        data_processados = importar_csv_yuan(
            csv_path=CSV_PATH,
            conn=conn,
            cursor=cursor
        )

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

            if data_processados:
                print("⚠️ Base data was inserted/updated, but indicators for those records were not written to SQL yet.")
                print("   Para gravar indicadores no SQL, muda UPDATE_SQL para True e volta a correr.")

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

