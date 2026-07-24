import pandas as pd
import mysql.connector
from sqlalchemy import create_engine

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# Database configuration
db_config = DB_CONFIG

# CSV path
csv_path = FED_SOURCE_DIR / "Loans and Leases in Bank Credit, All Commercial Banks.csv"

# Ler CSV
df = pd.read_csv(csv_path)
df['observation_date'] = pd.to_datetime(df['observation_date'])

# Rename column for SQL
df = df.rename(columns={'TOTLLNSA': 'total_loans_leases'})

# Conectar e inserir no SQL
engine = create_engine(get_sqlalchemy_database_url())

df.to_sql('fed_loans_leases', con=engine, if_exists='append', index=False)

print("Data loaded successfully!")
