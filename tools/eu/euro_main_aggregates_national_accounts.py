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
csv_file = EURO_SOURCE_DIR / "Main aggregates, national accounts_euro.csv"

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

# Insert SQL with all columns (adapted to the MySQL table)
sql = """
INSERT INTO euro_main_aggregates_national_accounts (
key_code, FREQ, ADJUSTMENT, REF_AREA, COUNTERPART_AREA, REF_SECTOR, COUNTERPART_SECTOR,
ACCOUNTING_ENTRY, STO, INSTR_ASSET, ACTIVITY, EXPENDITURE, UNIT_MEASURE, PRICES,
TRANSFORMATION, TIME_PERIOD, OBS_VALUE, OBS_STATUS, CONF_STATUS, PRE_BREAK_VALUE,
COMMENT_OBS, EMBARGO_DATE, TIME_FORMAT, COMMENT_TS, COMPILING_ORG, CURRENCY,
DATA_COMP, DECIMALS, DISS_ORG, LAST_UPDATE, REF_PERIOD_DETAIL, REF_YEAR_PRICE,
REPYEAREND, REPYEARSTART, TABLE_IDENTIFIER, TIME_PER_COLLECT, TITLE, TITLE_COMPL,
UNIT_MULT, COMMENT_DSET
) VALUES (
%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

# Read CSV in chunks to avoid memory overload
chunksize = 500
for chunk in pd.read_csv(csv_file, chunksize=chunksize, engine='python', dtype=str):
    # Clean valores NaN
    chunk = chunk.applymap(clean_value)

    # Create lista de tuplas para insert
    data_to_insert = [
        (
            row['KEY'], row['FREQ'], row['ADJUSTMENT'], row['REF_AREA'], row['COUNTERPART_AREA'],
            row['REF_SECTOR'], row['COUNTERPART_SECTOR'], row['ACCOUNTING_ENTRY'], row['STO'],
            row['INSTR_ASSET'], row['ACTIVITY'], row['EXPENDITURE'], row['UNIT_MEASURE'], row['PRICES'],
            row['TRANSFORMATION'], row['TIME_PERIOD'], row['OBS_VALUE'], row['OBS_STATUS'], row['CONF_STATUS'],
            row['PRE_BREAK_VALUE'], row['COMMENT_OBS'], row['EMBARGO_DATE'], row['TIME_FORMAT'], row['COMMENT_TS'],
            row['COMPILING_ORG'], row['CURRENCY'], row['DATA_COMP'], row['DECIMALS'], row['DISS_ORG'],
            row['LAST_UPDATE'], row['REF_PERIOD_DETAIL'], row['REF_YEAR_PRICE'], row['REPYEAREND'],
            row['REPYEARSTART'], row['TABLE_IDENTIFIER'], row['TIME_PER_COLLECT'], row['TITLE'], row['TITLE_COMPL'],
            row['UNIT_MULT'], row['COMMENT_DSET']
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
