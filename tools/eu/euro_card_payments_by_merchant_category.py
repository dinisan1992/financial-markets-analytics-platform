import pandas as pd
import mysql.connector
import numpy as np
from mysql.connector import errorcode

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# ==============================
# MYSQL CONNECTION CONFIGURATION
# ==============================
db_config = DB_CONFIG

# ==============================
# CLEANING FUNCTION
# ==============================
def clean_chunk(df):
    """
    Limpa o DataFrame garantindo que todos os 'NaN', 'nan', 'None', etc.,
    are converted to None (acceptable in MySQL).
    """
    # Substituir NaN do NumPy por None
    df = df.replace({np.nan: None})

    # Convert to string and strip whitespace
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # Substituir strings invalid por None
    df = df.replace({
        "nan": None, "NaN": None, "None": None, "": None, "NULL": None, "null": None
    })

    return df

# ==============================
# CAMINHO DO CSV
# ==============================
csv_path = EURO_SOURCE_DIR / "Electronic card payments sent by merchant category.csv"

# ==============================
# READ AND INSERT
# ==============================
chunk_size = 500

try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    for chunk in pd.read_csv(csv_path, chunksize=chunk_size, dtype=str):
        chunk = clean_chunk(chunk)

        # Convert numeric columns (where it makes sense)
        for col in ['OBS_VALUE', 'PRE_BREAK_VALUE', 'DECIMALS', 'UNIT_MULT']:
            if col in chunk.columns:
                chunk[col] = pd.to_numeric(chunk[col], errors='coerce')

        # Substituir novamente qualquer NaN residual por None
        chunk = chunk.replace({np.nan: None})

        # Converter DataFrame para lista de tuplos
        batch = [tuple(x) for x in chunk.values]

        sql = """
        INSERT INTO euro_card_payments_by_merchant_category (
            key_code, freq, ref_area, count_area, trmnl_lctn, rmt_inttn, mrchnt_ctgry_cd,
            transformation, unit_measure, time_period, obs_value, obs_status, conf_status,
            pre_break_value, comment_obs, time_format, breaks, comment_ts, compiling_org,
            diss_org, time_per_collect, coverage, data_comp, decimals, method_ref, title,
            title_compl, unit, unit_mult
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            obs_value = VALUES(obs_value),
            conf_status = VALUES(conf_status),
            pre_break_value = VALUES(pre_break_value),
            comment_obs = VALUES(comment_obs)
        """

        cursor.executemany(sql, batch)
        conn.commit()
        print(f"{len(batch)} rows inseridas.")

except mysql.connector.Error as err:
    print(f"❌ MySQL error: {err}")

finally:
    if cursor:
        cursor.close()
    if conn:
        conn.close()
    print("✅ Connection closed.")
