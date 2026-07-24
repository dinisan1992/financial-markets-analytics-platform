import pandas as pd
import mysql.connector
from mysql.connector import Error

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# =============================
# SETTINGS
# =============================
csv_path = EURO_SOURCE_DIR / "Losses due to fraud by liability bearer.csv"
table_name = "euro_losses_due_to_fraud"

# =============================
# CLEANING FUNCTION
# =============================
def clean_value(x):
    if pd.isna(x):
        return None
    if isinstance(x, str):
        x = x.strip().replace(',', '.')
        if x == '':
            return None
    return x

# =============================
# MYSQL CONNECTION
# =============================
try:
    conn = mysql.connector.connect(**DB_CONFIG)

    if conn.is_connected():
        print("✅ Connection established successfully!")

        cursor = conn.cursor()

        # =============================
        # LEITURA DO CSV POR CHUNKS
        # =============================
        chunksize = 1000
        for chunk in pd.read_csv(csv_path, chunksize=chunksize, encoding='utf-8'):
            chunk = chunk.applymap(clean_value)

            # renomear a coluna KEY -> key_code
            if 'KEY' in chunk.columns:
                chunk.rename(columns={'KEY': 'key_code'}, inplace=True)

            # preparar a query
            columns = [
                "key_code","FREQ","REF_AREA","COUNT_AREA","TYP_TRNSCTN","RL_TRNSCTN",
                "LBLTY_BRR","FRD_TYP","TRANSFORMATION","UNIT_MEASURE","TIME_PERIOD",
                "OBS_VALUE","OBS_STATUS","CONF_STATUS","PRE_BREAK_VALUE","COMMENT_OBS",
                "TIME_FORMAT","BREAKS","COMMENT_TS","COMPILING_ORG","DISS_ORG",
                "TIME_PER_COLLECT","COVERAGE","DATA_COMP","DECIMALS","METHOD_REF",
                "TITLE","TITLE_COMPL","UNIT","UNIT_MULT"
            ]

            placeholders = ",".join(["%s"] * len(columns))
            sql = f"""
                INSERT INTO {table_name} ({','.join(columns)})
                VALUES ({placeholders})
            """

            # preparar data
            data = [tuple(row[col] if col in row else None for col in columns) for _, row in chunk.iterrows()]

            # inserir no MySQL
            try:
                cursor.executemany(sql, data)
                conn.commit()
                print(f"✅ Inserido {cursor.rowcount} records.")
            except Error as e:
                print(f"❌ MySQL error: {e}")

except Error as e:
    print(f"❌ Connection error: {e}")

finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
        print("✅ Connection closed.")
