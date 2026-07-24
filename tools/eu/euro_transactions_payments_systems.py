import pandas as pd
import mysql.connector
from mysql.connector import Error

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# CSV path
csv_file = EURO_SOURCE_DIR / "Transactions in payments systems.csv"

# Function to clean values: transforma NaN em None
def clean_value(x):
    if pd.isna(x):
        return None
    return x

# MySQL connection
try:
    conn = mysql.connector.connect(**DB_CONFIG)
    if conn.is_connected():
        print("✅ Connection established successfully!")
except Error as e:
    print(f"❌ Connection error: {e}")
    exit()

cursor = conn.cursor()

# SQL de insert
sql = """
INSERT INTO euro_transactions_payments_systems (
key_code, FREQ, REF_AREA, COUNT_AREA, TYP_INFO, TYP_TRNSCTN, INTTN_CHNNL, PYMNT_SYSTM,
TRANSFORMATION, UNIT_MEASURE, CURRENCY_TRANS, TIME_PERIOD, OBS_VALUE, OBS_STATUS, CONF_STATUS,
PRE_BREAK_VALUE, COMMENT_OBS, TIME_FORMAT, BREAKS, COMMENT_TS, COMPILING_ORG, DISS_ORG,
TIME_PER_COLLECT, COVERAGE, DATA_COMP, DECIMALS, METHOD_REF, TITLE, TITLE_COMPL, UNIT, UNIT_MULT
) VALUES (
%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

# Ler CSV em chunks
chunksize = 500
for chunk in pd.read_csv(csv_file, chunksize=chunksize, dtype=str):
    # Clean valores NaN
    chunk = chunk.applymap(clean_value)

    # Create lista de tuplas para insert
    data_to_insert = [
        (
            row['KEY'], row['FREQ'], row['REF_AREA'], row['COUNT_AREA'], row['TYP_INFO'],
            row['TYP_TRNSCTN'], row['INTTN_CHNNL'], row['PYMNT_SYSTM'], row['TRANSFORMATION'],
            row['UNIT_MEASURE'], row['CURRENCY_TRANS'], row['TIME_PERIOD'], row['OBS_VALUE'],
            row['OBS_STATUS'], row['CONF_STATUS'], row['PRE_BREAK_VALUE'], row['COMMENT_OBS'],
            row['TIME_FORMAT'], row['BREAKS'], row['COMMENT_TS'], row['COMPILING_ORG'], row['DISS_ORG'],
            row['TIME_PER_COLLECT'], row['COVERAGE'], row['DATA_COMP'], row['DECIMALS'], row['METHOD_REF'],
            row['TITLE'], row['TITLE_COMPL'], row['UNIT'], row['UNIT_MULT']
        )
        for index, row in chunk.iterrows()
    ]

    # Inserir no MySQL
    try:
        cursor.executemany(sql, data_to_insert)
        conn.commit()
        print(f"{len(data_to_insert)} rows inseridas.")
    except Error as e:
        print(f"❌ MySQL error: {e}")
        conn.rollback()

# Close connection
cursor.close()
conn.close()
print("✅ Connection closed.")
