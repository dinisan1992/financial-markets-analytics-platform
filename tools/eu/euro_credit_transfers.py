import pandas as pd
import mysql.connector

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# =========================
# DATABASE CONFIGURATION
# =========================
db_config = DB_CONFIG

csv_path = EURO_SOURCE_DIR / "Credit transfers (including fraud).csv"
chunk_size = 1000  # adjust according to memory

# =========================
# LIMPEZA SEGURA DE VALORES
# =========================
def clean_value(x):
    if pd.isna(x):
        return None
    if isinstance(x, str):
        x = x.strip()
        if x.lower() == 'nan' or x == '':
            return None
    return x

# =========================
# CONNECTION
# =========================
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
    # Clean todos os valores
    chunk = chunk.applymap(clean_value)

    # Renomear 'KEY' se existir
    if 'KEY' in chunk.columns:
        chunk = chunk.rename(columns={'KEY': 'key_code'})

    # Preparar SQL
    columns = chunk.columns.tolist()
    placeholders = ', '.join([f"%({col})s" for col in columns])
    columns_sql = ', '.join([f"`{col}`" for col in columns])
    sql = f"INSERT IGNORE INTO euro_credit_transfers ({columns_sql}) VALUES ({placeholders})"

    # Converter cada linha em dict e garantir que todos os NaN are None
    data_to_insert = []
    for _, row in chunk.iterrows():
        cleaned_row = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
        data_to_insert.append(cleaned_row)

    # Inserir em batches pequenos
    batch_size = 500
    for i in range(0, len(data_to_insert), batch_size):
        batch = data_to_insert[i:i+batch_size]
        cursor.executemany(sql, batch)
        conn.commit()
        print(f"{len(batch)} rows inseridas.")

cursor.close()
conn.close()
print("✅ Data imported successfully!")
