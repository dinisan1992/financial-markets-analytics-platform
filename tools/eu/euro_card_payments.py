import pandas as pd
import mysql.connector

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# Database configuration
db_config = DB_CONFIG

csv_path = EURO_SOURCE_DIR / "Card payments and cash withdrawals using cards (including fraud data).csv"
chunk_size = 50000

conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

sql = """
INSERT INTO euro_card_payments (
    key_code, freq, ref_area, count_area, trmnl_lctn, typ_trnsctn, rl_trnsctn, inttn_chnnl,
    rmt_inttn, pymnt_schm, crd_fnctn, sca, frd_typ, transformation, unit_measure,
    time_period, obs_value, obs_status, conf_status, pre_break_value, comment_obs,
    time_format, breaks, comment_ts, compiling_org, diss_org, time_per_collect,
    coverage, data_comp, decimals, method_ref, title, title_compl, unit, unit_mult
) VALUES (
    %(KEY)s, %(FREQ)s, %(REF_AREA)s, %(COUNT_AREA)s, %(TRMNL_LCTN)s, %(TYP_TRNSCTN)s, %(RL_TRNSCTN)s,
    %(INTTN_CHNNL)s, %(RMT_INTTN)s, %(PYMNT_SCHM)s, %(CRD_FNCTN)s, %(SCA)s, %(FRD_TYP)s,
    %(TRANSFORMATION)s, %(UNIT_MEASURE)s, %(TIME_PERIOD)s, %(OBS_VALUE)s, %(OBS_STATUS)s,
    %(CONF_STATUS)s, %(PRE_BREAK_VALUE)s, %(COMMENT_OBS)s, %(TIME_FORMAT)s, %(BREAKS)s,
    %(COMMENT_TS)s, %(COMPILING_ORG)s, %(DISS_ORG)s, %(TIME_PER_COLLECT)s, %(COVERAGE)s,
    %(DATA_COMP)s, %(DECIMALS)s, %(METHOD_REF)s, %(TITLE)s, %(TITLE_COMPL)s, %(UNIT)s, %(UNIT_MULT)s
)
"""

for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
    # Substituir todos os NaN por None
    chunk = chunk.where(pd.notnull(chunk), None)

    # Remove any "nan" string or whitespace
    for col in chunk.columns:
        chunk[col] = chunk[col].apply(lambda x: None if x is None else str(x).strip())
        chunk[col] = chunk[col].apply(lambda x: None if x == 'nan' else x)

    for _, row in chunk.iterrows():
        try:
            cursor.execute(sql, row.to_dict())
        except mysql.connector.IntegrityError:
            continue  # ignora duplicados
        except mysql.connector.ProgrammingError as e:
            print(f"Error inserting row: {e}")
            continue

    conn.commit()
    print(f"{len(chunk)} rows inseridas.")

cursor.close()
conn.close()
print("Import completed!")
