import pandas as pd
import mysql.connector
from sqlalchemy import create_engine

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# Database settings
db_config = DB_CONFIG

# CSV path
csv_path = FED_SOURCE_DIR / "M2SL.csv"

# Ler CSV
df = pd.read_csv(csv_path)
df['observation_date'] = pd.to_datetime(df['observation_date'])

# Rename columns to match the SQL table
df.rename(columns={'M2SL': 'm2'}, inplace=True)

# Create engine SQLAlchemy
engine = create_engine(get_sqlalchemy_database_url())

# Inserir data no SQL
df.to_sql('fed_m2', con=engine, if_exists='append', index=False)

print("M2 data loaded successfully!")
