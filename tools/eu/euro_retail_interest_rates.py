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
csv_file = EURO_SOURCE_DIR / "Retail Interest Rates.csv"

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
INSERT INTO euro_retail_interest_rates (
key_code, FREQ, REF_AREA, BS_REP_SECTOR, BS_ITEM, MATURITY_ORIG, BS_COUNT_SECTOR,
CURRENCY_TRANS, IR_BUS_COV, IR_FV_TYPE, RIR_SUFFIX, TIME_PERIOD, OBS_VALUE, OBS_STATUS,
OBS_CONF, OBS_PRE_BREAK, OBS_COM, TIME_FORMAT, BREAKS, COLLECTION, DOM_SER_IDS, PUBL_ECB,
PUBL_MU, PUBL_PUBLIC, COMPILATION, COVERAGE, DECIMALS, NAT_TITLE, TITLE, TITLE_COMPL,
UNIT, UNIT_MULT
) VALUES (
%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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
            row['KEY'], row['FREQ'], row['REF_AREA'], row['BS_REP_SECTOR'], row['BS_ITEM'],
            row['MATURITY_ORIG'], row['BS_COUNT_SECTOR'], row['CURRENCY_TRANS'], row['IR_BUS_COV'],
            row['IR_FV_TYPE'], row['RIR_SUFFIX'], row['TIME_PERIOD'], row['OBS_VALUE'], row['OBS_STATUS'],
            row['OBS_CONF'], row['OBS_PRE_BREAK'], row['OBS_COM'], row['TIME_FORMAT'], row['BREAKS'],
            row['COLLECTION'], row['DOM_SER_IDS'], row['PUBL_ECB'], row['PUBL_MU'], row['PUBL_PUBLIC'],
            row['COMPILATION'], row['COVERAGE'], row['DECIMALS'], row['NAT_TITLE'], row['TITLE'],
            row['TITLE_COMPL'], row['UNIT'], row['UNIT_MULT']
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
