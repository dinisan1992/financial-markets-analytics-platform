import pandas as pd
import mysql.connector
import numpy as np

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# =========================
# SETTINGS
# =========================
csv_path = EURO_SOURCE_DIR / "E-money payment transactions (including fraud data).csv"

db_config = DB_CONFIG

table_name = 'euro_emoney_payment_transactions'
chunksize = 1000  # reads the file in chunks to avoid memory overload

# =========================
# CLEANING FUNCTION
# =========================
def clean_value(value):
    """Cleans null values and whitespace, and converts 'nan' or empty values to None."""
    if pd.isna(value) or str(value).strip().lower() in ['nan', 'na', '', 'none']:
        return None
    return str(value).strip()

# =========================
# DATABASE CONNECTION
# =========================
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

print(f"📥 Importing data from: {csv_path}")

# =========================
# READ AND INSERT
# =========================
for chunk in pd.read_csv(csv_path, chunksize=chunksize, encoding='utf-8'):
    chunk.columns = [c.strip().lower().replace(" ", "_") for c in chunk.columns]  # normalizes headers
    chunk = chunk.applymap(clean_value)

    insert_query = f"""
    INSERT INTO {table_name} (
        key_code, freq, ref_area, count_area, typ_trnsctn, rl_trnsctn, inttn_chnnl, rmt_inttn,
        sca, frd_typ, transformation, unit_measure, time_period, obs_value, obs_status,
        conf_status, pre_break_value, comment_obs, time_format, breaks, comment_ts, compiling_org,
        diss_org, time_per_collect, coverage, data_comp, decimals, method_ref, title, title_compl,
        unit, unit_mult
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    """

    # converare dos valores por linha
    for _, row in chunk.iterrows():
        values = tuple(row.get(col, None) for col in chunk.columns)
        try:
            cursor.execute(insert_query, values)
        except Exception as e:
            print(f"❌ Error a inserir linha: {e}")
            print("Problematic row:", row.to_dict())

    conn.commit()
    print(f"✅ Inserido chunk com {len(chunk)} records.")

# =========================
# CLOSE CONNECTION
# =========================
cursor.close()
conn.close()
print("🏁 Import completed and connection closed.")
