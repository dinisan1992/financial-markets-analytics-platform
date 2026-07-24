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
csv_path = FED_SOURCE_DIR / "Delinquency Rate on Credit Card Loans, All Commercial Banks.csv"

# Ler CSV
df = pd.read_csv(csv_path)
df['observation_date'] = pd.to_datetime(df['observation_date'])
df.rename(columns={'DRCCLACBS': 'delinquency_rate'}, inplace=True)

# Conectar ao MySQL
db_url = get_sqlalchemy_database_url()
engine = create_engine(db_url)

# Inserir data no SQL
df.to_sql('fed_credit_card_delinquency', con=engine, if_exists='append', index=False)

print("Data inserted successfully!")
