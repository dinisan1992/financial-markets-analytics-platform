from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
import mysql.connector
from mysql.connector import Error

from config import DB_CONFIG, EURO_SOURCE_DIR

# CSV path
csv_file = EURO_SOURCE_DIR / "Government Finance Statistics.csv"

# Mapear columns CSV -> columns MySQL
column_map = {
    'KEY':'key_code','FREQ':'freq','ADJUSTMENT':'adjustment','REF_AREA':'ref_area',
    'COUNTERPART_AREA':'counterpart_area','REF_SECTOR':'ref_sector','COUNTERPART_SECTOR':'counterpart_sector',
    'CONSOLIDATION':'consolidation','ACCOUNTING_ENTRY':'accounting_entry','STO':'sto','INSTR_ASSET':'instr_asset',
    'MATURITY':'maturity','EXPENDITURE':'expenditure','UNIT_MEASURE':'unit_measure','CURRENCY_DENOM':'currency_denom',
    'VALUATION':'valuation','PRICES':'prices','TRANSFORMATION':'transformation','CUST_BREAKDOWN':'cust_breakdown',
    'TIME_PERIOD':'time_period','OBS_VALUE':'obs_value','OBS_STATUS':'obs_status','CONF_STATUS':'conf_status',
    'PRE_BREAK_VALUE':'pre_break_value','COMMENT_OBS':'comment_obs','EMBARGO_DATE':'embargo_date','OBS_EDP_WBB':'obs_edp_wbb',
    'TIME_FORMAT':'time_format','COLL_PERIOD':'coll_period','COMMENT_TS':'comment_ts','COMPILING_ORG':'compiling_org',
    'CURRENCY':'currency','CUST_BREAKDOWN_LB':'cust_breakdown_lb','DATA_COMP':'data_comp','DECIMALS':'decimals',
    'DISS_ORG':'diss_org','GFS_ECOFUNC':'gfs_ecofunc','GFS_TAXCAT':'gfs_taxcat','LAST_UPDATE':'last_update',
    'REF_PERIOD_DETAIL':'ref_period_detail','REF_YEAR_PRICE':'ref_year_price','REPYEAREND':'repyearend',
    'REPYEARSTART':'repyearstart','TABLE_IDENTIFIER':'table_identifier','TIME_PER_COLLECT':'time_per_collect',
    'TITLE':'title','TITLE_COMPL':'title_compl','UNIT_MULT':'unit_mult','COMMENT_DSET':'comment_dset'
}

mysql_columns = list(column_map.values())
placeholders = ','.join(['%s'] * len(mysql_columns))
sql = f"INSERT INTO euro_government_finance_statistics ({', '.join(['`'+c+'`' for c in mysql_columns])}) VALUES ({placeholders})"

# Function to convert NaN -> None
def clean_row(row):
    return tuple(None if pd.isna(x) else x for x in row)

# MySQL connection
try:
    conn = mysql.connector.connect(**DB_CONFIG)
    if conn.is_connected():
        print("✅ Connection established successfully!")
except Error as e:
    print(f"❌ Connection error: {e}")
    exit()

cursor = conn.cursor()
chunksize = 500  # adjust according to memory

try:
    for chunk in pd.read_csv(csv_file, chunksize=chunksize, engine='python', dtype=str):
        # Rename all columns for the MySQL table
        chunk = chunk.rename(columns=column_map)

        # Garantir que todas as columns existem na ordem correta
        for c in mysql_columns:
            if c not in chunk.columns:
                chunk[c] = None
        chunk = chunk[mysql_columns]

        # Converter cada linha para tupla e clean NaNs
        data_to_insert = [clean_row(row) for row in chunk.to_numpy()]

        # Inserir no MySQL
        try:
            cursor.executemany(sql, data_to_insert)
            conn.commit()
            print(f"{len(data_to_insert)} rows inseridas.")
        except Error as e:
            print(f"❌ MySQL error: {e}")
            conn.rollback()

except FileNotFoundError:
    print(f"❌ CSV not found: {csv_file}")
except Exception as ex:
    print(f"❌ Other error: {ex}")
finally:
    cursor.close()
    conn.close()
    print("✅ Connection closed.")

