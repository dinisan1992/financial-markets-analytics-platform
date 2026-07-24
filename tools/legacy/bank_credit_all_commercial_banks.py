from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import os
import pandas as pd
import mysql.connector

from config import DB_CONFIG, FED_SOURCE_DIR


# ========================
# SETTINGS
# ========================
CSV_PATH = FED_SOURCE_DIR / "Bank Credit, All Commercial Banks.csv"

TABLE_NAME = "fed_bank_credit"

DATE_COLUMN = "observation_date"

VALUE_COLUMN = "totbkcr"


# ========================
# CONNECT TO THE DATABASE
# ========================
def conectar_bd(config):
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()
    return conn, cursor


# ========================
# LER E LIMPAR CSV
# ========================
def load_csv(csv_path):
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return pd.DataFrame()

    df = pd.read_csv(csv_path)

    # ========================
    # VALIDAR E RENOMEAR COLUNAS
    # ========================
    if len(df.columns) < 2:
        print("❌ CSV does not have enough columns.")
        return pd.DataFrame()

    df = df.iloc[:, :2].copy()

    df.columns = [
        DATE_COLUMN,
        VALUE_COLUMN
    ]

    # ========================
    # CONVERTER TIPOS
    # ========================
    df[DATE_COLUMN] = pd.to_datetime(
        df[DATE_COLUMN],
        errors="coerce"
    )

    df[VALUE_COLUMN] = pd.to_numeric(
        df[VALUE_COLUMN],
        errors="coerce"
    )

    # ========================
    # REMOVE INVALID ROWS
    # ========================
    df = df.dropna(
        subset=[
            DATE_COLUMN,
            VALUE_COLUMN
        ]
    ).reset_index(drop=True)

    # ========================
    # ORDENAR POR DATA
    # ========================
    df = df.sort_values(
        by=DATE_COLUMN
    ).reset_index(drop=True)

    return df


# ========================
# OBTER DATAS EXISTENTES
# ========================
def obter_datas_existentes(cursor):
    query = f"""
        SELECT {DATE_COLUMN}
        FROM {TABLE_NAME}
    """

    cursor.execute(query)

    datas_existentes = set(
        pd.to_datetime(row[0])
        for row in cursor.fetchall()
    )

    return datas_existentes


# ========================
# INSERIR NOVOS REGISTOS
# ========================
def inserir_novos_records(df, cursor, conn):
    if df.empty:
        print("❌ DataFrame vazio. Nada para inserir.")
        return

    datas_existentes = obter_datas_existentes(cursor)

    df_novos = df[
        ~df[DATE_COLUMN].isin(datas_existentes)
    ].copy()

    if df_novos.empty:
        print(f"✅ No new data to import into {TABLE_NAME}.")
        return

    insert_query = f"""
        INSERT INTO {TABLE_NAME}
            ({DATE_COLUMN}, {VALUE_COLUMN})
        VALUES
            (%s, %s)
    """

    for _, row in df_novos.iterrows():
        cursor.execute(
            insert_query,
            (
                row[DATE_COLUMN].strftime("%Y-%m-%d"),
                float(row[VALUE_COLUMN])
            )
        )

    conn.commit()

    print(f"✅ {len(df_novos)} new rows inserted into the table {TABLE_NAME}.")


# ========================
# MAIN FUNCTION
# ========================
def main():
    conn = None
    cursor = None

    try:
        print(f"📥 Loading CSV: {CSV_PATH}")

        df = load_csv(CSV_PATH)

        if df.empty:
            print("❌ No valid data found in the CSV.")
            return

        print(f"✅ {len(df)} valid rows loaded.")
        print(df.head())

        conn, cursor = conectar_bd(DB_CONFIG)

        inserir_novos_records(
            df=df,
            cursor=cursor,
            conn=conn
        )

        print("✅ Processing completed.")

    except Exception as e:
        print(f"❌ Error during processing: {e}")

    finally:
        if cursor is not None:
            cursor.close()

        if conn is not None:
            conn.close()


# ========================
# EXECUTION
# ========================
if __name__ == "__main__":
    main()

