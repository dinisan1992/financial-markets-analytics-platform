import pandas as pd
import mysql.connector

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# CSV path
csv_path = FED_SOURCE_DIR / "Reserve Bank Credit.csv"

# Ler o CSV
df = pd.read_csv(csv_path, parse_dates=['observation_date'])

# Rename the column to a friendlier name
df.rename(columns={'RSBKCRNS': 'reserve_bank_credit'}, inplace=True)

# Database configuration
db_config = DB_CONFIG

# Connect and insert data
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

for _, row in df.iterrows():
    cursor.execute(
        "INSERT INTO fed_reserve_bank_credit (observation_date, reserve_bank_credit) VALUES (%s, %s)",
        (row['observation_date'], row['reserve_bank_credit'])
    )

conn.commit()
cursor.close()
conn.close()

print("Data loaded successfully!")
