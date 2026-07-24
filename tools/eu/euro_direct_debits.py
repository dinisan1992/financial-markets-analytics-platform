import pandas as pd
import mysql.connector
import numpy as np

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# =============================
# SETTINGS
# =============================
csv_path = EURO_SOURCE_DIR / "Direct debits (including fraud).csv"
chunk_size = 500

db_config = DB_CONFIG

# =============================
# INSERT FUNCTION
# =============================
def insert_data(chunk, cursor):
    chunk = chunk.replace({np.nan: None})
    sql = """
        INSERT INTO euro_direct_debits (
            key_code, freq, ref_area, count_area, rl_trnsctn, inttn_chnnl, pymnt_schm,
            chnnl_cnsnt, frd_typ, transformation, unit_measure, time_period, obs_value,
            obs_status, conf_status, pre_break_value, comment_obs, time_format, breaks,
            comment_ts, compiling_org, diss_org, time_per_collect, coverage, data_comp,
            decimals, method_ref, title, title_compl, unit, unit_mult
        )
        VALUES (
            %(KEY)s, %(FREQ)s, %(REF_AREA)s, %(COUNT_AREA)s, %(RL_TRNSCTN)s, %(INTTN_CHNNL)s, %(PYMNT_SCHM)s,
            %(CHNNL_CNSNT)s, %(FRD_TYP)s, %(TRANSFORMATION)s, %(UNIT_MEASURE)s, %(TIME_PERIOD)s, %(OBS_VALUE)s,
            %(OBS_STATUS)s, %(CONF_STATUS)s, %(PRE_BREAK_VALUE)s, %(COMMENT_OBS)s, %(TIME_FORMAT)s, %(BREAKS)s,
            %(COMMENT_TS)s, %(COMPILING_ORG)s, %(DISS_ORG)s, %(TIME_PER_COLLECT)s, %(COVERAGE)s, %(DATA_COMP)s,
            %(DECIMALS)s, %(METHOD_REF)s, %(TITLE)s, %(TITLE_COMPL)s, %(UNIT)s, %(UNIT_MULT)s
        )
        ON DUPLICATE KEY UPDATE
            obs_value = VALUES(obs_value),
            obs_status = VALUES(obs_status),
            conf_status = VALUES(conf_status),
            pre_break_value = VALUES(pre_break_value)
    """

    cursor.executemany(sql, chunk.to_dict(orient="records"))


# =============================
# CONNECTION AND CSV READ
# =============================
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    # Detetar automaticamente o delimitador
    with open(csv_path, "r", encoding="utf-8") as f:
        header = f.readline()
    delimiter = ";" if ";" in header else ","

    for chunk in pd.read_csv(csv_path, chunksize=chunk_size, delimiter=delimiter, encoding="utf-8"):
        insert_data(chunk, cursor)
        conn.commit()
        print(f"{len(chunk)} rows inseridas.")

    print("Import completed successfully!")

except Exception as e:
    print("Error:", e)

finally:
    cursor.close()
    conn.close()
