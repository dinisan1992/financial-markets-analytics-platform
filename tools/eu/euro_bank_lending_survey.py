import pandas as pd
import mysql.connector

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


db_config = DB_CONFIG

csv_path = EURO_SOURCE_DIR / "Bank Lending Survey.csv"
chunk_size = 50000

# Connect to the database
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

sql = """
INSERT INTO euro_bank_lending_survey (
    key_code, freq, ref_area, bank_selection, bls_item, bls_count, bls_count_detail,
    time_horizon, effect_domain, market_role, bls_agg_method, time_period, obs_value,
    obs_status, obs_conf, obs_pre_break, obs_com, time_format, collection,
    compiling_org, diss_org, decimals, source_agency, title, title_compl, unit, unit_mult
) VALUES (
    %(KEY)s, %(FREQ)s, %(REF_AREA)s, %(BANK_SELECTION)s, %(BLS_ITEM)s, %(BLS_COUNT)s, %(BLS_COUNT_DETAIL)s,
    %(TIME_HORIZON)s, %(EFFECT_DOMAIN)s, %(MARKET_ROLE)s, %(BLS_AGG_METHOD)s, %(TIME_PERIOD)s, %(OBS_VALUE)s,
    %(OBS_STATUS)s, %(OBS_CONF)s, %(OBS_PRE_BREAK)s, %(OBS_COM)s, %(TIME_FORMAT)s, %(COLLECTION)s,
    %(COMPILING_ORG)s, %(DISS_ORG)s, %(DECIMALS)s, %(SOURCE_AGENCY)s, %(TITLE)s, %(TITLE_COMPL)s, %(UNIT)s, %(UNIT_MULT)s
)
"""

# Ler por chunks
for chunk in pd.read_csv(csv_path, chunksize=chunk_size, dtype=str, low_memory=False):
    # Converte todos os NaN ou 'nan' para None
    chunk = chunk.where(pd.notnull(chunk), None)
    chunk = chunk.applymap(lambda x: None if str(x).strip().lower() == 'nan' else x)

    for _, row in chunk.iterrows():
        try:
            cursor.execute(sql, row.to_dict())
        except mysql.connector.IntegrityError as e:
            # Ignorar duplicatas
            if e.errno == 1062:
                continue
            else:
                raise
        except mysql.connector.ProgrammingError as e:
            print(f"Error in row: {row.to_dict()}")
            raise

    conn.commit()
    print(f"{len(chunk)} rows inseridas.")

cursor.close()
conn.close()
print("Import completed!")
