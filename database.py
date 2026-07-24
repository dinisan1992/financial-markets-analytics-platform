import os
import pandas as pd
import mysql.connector
import numpy as np


# =========================
# CONNECT TO THE DATABASE
# =========================
def conectar_bd(config):
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    return conn, cursor


# =========================
# IMPORTAR CSV E ATUALIZAR MYSQL
# =========================
def importar_csv_e_update_mysql(csv_path, conn, cursor):
    if not os.path.exists(csv_path):
        print("No CSV found, skipping import.")
        return

    df_csv = pd.read_csv(csv_path)

    required_columns = [
        "snapped_at",
        "price",
        "total_volume"
    ]

    for col in required_columns:
        if col not in df_csv.columns:
            print(f"❌ Coluna '{col}' not found in the CSV.")
            return

    df_csv["snapped_at"] = pd.to_datetime(
        df_csv["snapped_at"]
        .astype(str)
        .str.replace(" UTC", "", regex=False),
        errors="coerce"
    )

    df_csv["price"] = pd.to_numeric(
        df_csv["price"],
        errors="coerce"
    )

    df_csv["total_volume"] = pd.to_numeric(
        df_csv["total_volume"],
        errors="coerce"
    )

    df_csv = df_csv.dropna(
        subset=[
            "snapped_at",
            "price",
            "total_volume"
        ]
    ).reset_index(drop=True)

    if df_csv.empty:
        print("No valid data to import.")
        return

    cursor.execute("SELECT snapped_at FROM btc_analysis")

    datas_existentes = set(
        pd.to_datetime(row[0])
        for row in cursor.fetchall()
    )

    df_novos = df_csv[
        ~df_csv["snapped_at"].isin(datas_existentes)
    ].copy()

    if df_novos.empty:
        print("No new data to import.")
        return

    insert_sql = """
        INSERT INTO btc_analysis
            (snapped_at, price, total_volume)
        VALUES
            (%s, %s, %s)
    """

    for _, row in df_novos.iterrows():
        cursor.execute(
            insert_sql,
            (
                row["snapped_at"].strftime("%Y-%m-%d %H:%M:%S"),
                converter_valor_mysql(row["price"]),
                converter_valor_mysql(row["total_volume"])
            )
        )

    conn.commit()

    print(f"{len(df_novos)} new records inserted into the table.")


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
# ATUALIZAR INDICADORES NO SQL
# =========================
def update_indicadores_sql(df, cursor, conn):
    """
    Updates only indicators that already existed in the btc_analysis table.

    The new advanced indicators are NOT sent to SQL at this stage.
    """

    update_sql = """
        UPDATE btc_analysis SET
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

    print("✅ Indicators updated in the database.")


# =========================
# UPDATE MANIPULATION FLAGS IN SQL
# =========================
def update_manipulacao_sql(df, cursor, conn):
    update_manip_sql = """
        UPDATE btc_analysis
        SET manipulation=%s
        WHERE snapped_at=%s
    """

    flags_df = df[df["manipulation"].notnull()].copy()

    if flags_df.empty:
        print("✅ No new manipulation flags to update.")
        return

    for _, row in flags_df.iterrows():
        cursor.execute(
            update_manip_sql,
            (
                row["manipulation"],
                converter_valor_mysql(row["snapped_at"])
            )
        )

    conn.commit()

    print(f"✅ {len(flags_df)} manipulation flags updated in SQL.")
