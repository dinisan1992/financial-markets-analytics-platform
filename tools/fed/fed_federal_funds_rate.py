import pandas as pd
import mysql.connector
from sqlalchemy import create_engine

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# CSV path
csv_path = FED_SOURCE_DIR / "Federal Funds Effective Rate.csv"

# Ler CSV
df = pd.read_csv(csv_path)
df['observation_date'] = pd.to_datetime(df['observation_date'])

# Rename column to the table standard
df.rename(columns={'FEDFUNDS': 'federal_funds_rate'}, inplace=True)

# Connection com MySQL
db_url = get_sqlalchemy_database_url()
engine = create_engine(db_url)

# Insert data into the table 'fed_federal_funds_rate'
df.to_sql('fed_federal_funds_rate', con=engine, if_exists='append', index=False)

print("Data loaded successfully!")
