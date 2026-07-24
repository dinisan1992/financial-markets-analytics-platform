import pandas as pd
import mysql.connector

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


db_config = DB_CONFIG

csv_path = EURO_SOURCE_DIR / "Balance Sheet Items.csv"

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

sql = """
INSERT IGNORE INTO euro_balance_sheet_items (
    key_code, freq, ref_area, adjustment, bs_rep_sector, bs_item, maturity_orig, data_type,
    count_area, bs_count_sector, currency_trans, bs_suffix, time_period, obs_value, obs_status,
    obs_conf, obs_pre_break, obs_com, time_format, breaks, collection, compiling_org, diss_org,
    dom_ser_ids, publ_ecb, publ_mu, publ_public, unit_index_base, compilation, decimals,
    nat_title, source_agency, title, title_compl, unit, unit_mult
) VALUES (
    %(KEY)s, %(FREQ)s, %(REF_AREA)s, %(ADJUSTMENT)s, %(BS_REP_SECTOR)s, %(BS_ITEM)s,
    %(MATURITY_ORIG)s, %(DATA_TYPE)s, %(COUNT_AREA)s, %(BS_COUNT_SECTOR)s, %(CURRENCY_TRANS)s,
    %(BS_SUFFIX)s, %(TIME_PERIOD)s, %(OBS_VALUE)s, %(OBS_STATUS)s, %(OBS_CONF)s, %(OBS_PRE_BREAK)s,
    %(OBS_COM)s, %(TIME_FORMAT)s, %(BREAKS)s, %(COLLECTION)s, %(COMPILING_ORG)s, %(DISS_ORG)s,
    %(DOM_SER_IDS)s, %(PUBL_ECB)s, %(PUBL_MU)s, %(PUBL_PUBLIC)s, %(UNIT_INDEX_BASE)s, %(COMPILATION)s,
    %(DECIMALS)s, %(NAT_TITLE)s, %(SOURCE_AGENCY)s, %(TITLE)s, %(TITLE_COMPL)s, %(UNIT)s, %(UNIT_MULT)s
)
"""


chunk_size = 50000
for chunk in pd.read_csv(csv_path, low_memory=False, chunksize=chunk_size):
    # Substituir NaN ou string 'nan' por None
    chunk = chunk.replace({pd.NA: None, float('nan'): None, 'nan': None})

    # Converter tipos object mistos para string para evitar problemas
    chunk = chunk.astype(object).where(pd.notnull(chunk), None)

    # Inserir cada linha
    for _, row in chunk.iterrows():
        cursor.execute(sql, row.to_dict())

    conn.commit()
    print(f"{len(chunk)} rows inseridas.")

cursor.close()
conn.close()
print("Import complete!")
