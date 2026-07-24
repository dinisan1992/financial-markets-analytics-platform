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
csv_file = EURO_SOURCE_DIR / "Indices of Consumer Prices_euro.csv"

# Function to clean NaN values
def clean_value(x):
    if pd.isna(x):
        return None
    return str(x).strip() if isinstance(x, str) else x

# MySQL connection
try:
    conn = mysql.connector.connect(**DB_CONFIG)
    if conn.is_connected():
        print("✅ Connection established successfully!")
except Error as e:
    print(f"❌ Connection error: {e}")
    exit()

cursor = conn.cursor()

# SQL adapted for the table euro_indices_consumer_prices
sql = """
INSERT INTO euro_indices_consumer_prices (
    key_code, freq, ref_area, adjustment, icp_item, sts_institution, icp_suffix, 
    time_period, obs_value, obs_status, obs_conf, obs_pre_break, obs_com, time_format, 
    breaks, collection, compiling_org, data_comp, diss_org, dom_ser_ids, publ_ecb, 
    publ_mu, publ_public, unit_index_base, compilation, coverage, decimals, 
    source_agency, title, title_compl, unit, unit_mult
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

# Ler CSV em chunks
chunksize = 500
try:
    for chunk in pd.read_csv(csv_file, chunksize=chunksize, dtype=str, engine='python'):
        chunk = chunk.applymap(clean_value)

        # Create lista de tuplas para insert
        data_to_insert = [
            (
                row['KEY'],
                row['FREQ'],
                row['REF_AREA'],
                row['ADJUSTMENT'],
                row['ICP_ITEM'],
                row['STS_INSTITUTION'],
                row['ICP_SUFFIX'],
                row['TIME_PERIOD'],
                row['OBS_VALUE'],
                row['OBS_STATUS'],
                row['OBS_CONF'],
                row['OBS_PRE_BREAK'],
                row['OBS_COM'],
                row['TIME_FORMAT'],
                row['BREAKS'],
                row['COLLECTION'],
                row['COMPILING_ORG'],
                row['DATA_COMP'],
                row['DISS_ORG'],
                row['DOM_SER_IDS'],
                row['PUBL_ECB'],
                row['PUBL_MU'],
                row['PUBL_PUBLIC'],
                row['UNIT_INDEX_BASE'],
                row['COMPILATION'],
                row['COVERAGE'],
                row['DECIMALS'],
                row['SOURCE_AGENCY'],
                row['TITLE'],
                row['TITLE_COMPL'],
                row['UNIT'],
                row['UNIT_MULT']
            )
            for _, row in chunk.iterrows()
        ]

        # Inserir no MySQL
        try:
            cursor.executemany(sql, data_to_insert)
            conn.commit()
            print(f"✅ {len(data_to_insert)} rows inserted successfully.")
        except Error as e:
            print(f"❌ MySQL error: {e}")
            conn.rollback()
except Exception as e:
    print(f"❌ Error reading CSV: {e}")

# Close connection
cursor.close()
conn.close()
print("✅ Connection closed.")
