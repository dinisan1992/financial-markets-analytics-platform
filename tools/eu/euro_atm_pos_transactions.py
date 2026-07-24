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

# CSV path
csv_path = EURO_SOURCE_DIR / "ATM, OTC and POS terminal transactions.csv"

# Ler CSV
df = pd.read_csv(csv_path, dtype=str)  # Ler tudo como string

# Substituir valores empty ou "nan" por None usando apply + map
df = df.apply(lambda col: col.map(lambda x: None if pd.isna(x) or str(x).strip().lower() == 'nan' else x))

# Connect to the database
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# Inserir data no SQL
for _, row in df.iterrows():
    sql = """
    INSERT INTO euro_atm_pos_transactions (
        key_code, freq, ref_area, count_area, terminal_location, transaction_type,
        reported_transaction, intention_channel, transformation, unit_measure, time_period,
        obs_value, obs_status, conf_status, pre_break_value, comment_obs, time_format, breaks,
        comment_ts, compiling_org, diss_org, time_per_collect, coverage, data_comp, decimals,
        method_ref, title, title_compl, unit, unit_mult
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(sql, tuple(row))

# Commit and close connection
conn.commit()
cursor.close()
conn.close()

print("Data loaded successfully into table euro_atm_pos_transactions!")
