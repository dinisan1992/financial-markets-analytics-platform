import pandas as pd
import mysql.connector

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# =========================
# SETTINGS
# =========================
csv_path = FED_SOURCE_DIR / "Assets Total Assets Total Assets.csv"
db_config = DB_CONFIG
table_name = "fed_total_assets"

# =========================
# LER CSV
# =========================
try:
    df = pd.read_csv(csv_path)
except Exception:
    df = pd.read_csv(csv_path, encoding='latin1')

df.columns = [col.strip().lower() for col in df.columns]
df.rename(columns={'walcl': 'total_assets'}, inplace=True)
df['observation_date'] = pd.to_datetime(df['observation_date'], errors='coerce')
df['total_assets'] = pd.to_numeric(df['total_assets'], errors='coerce')

# =========================
# CONNECTION AND INSERT
# =========================
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# Evitar duplicados
cursor.execute(f"SELECT observation_date FROM {table_name}")
existing_dates = {row[0] for row in cursor.fetchall()}

df_new = df[~df['observation_date'].isin(existing_dates)]
print(f"🔍 {len(df_new)} new records found to insert.")

# Inserir novos data
if not df_new.empty:
    insert_query = f"""
        INSERT INTO {table_name} (observation_date, total_assets)
        VALUES (%s, %s)
    """
    data_to_insert = list(df_new[['observation_date', 'total_assets']].itertuples(index=False, name=None))
    cursor.executemany(insert_query, data_to_insert)
    conn.commit()
    print(f"✅ {len(data_to_insert)} records imported successfully.")
else:
    print("ℹ️ No new record to insert.")

# Close connection
cursor.close()
conn.close()
print("🔒 Connection closed.")
