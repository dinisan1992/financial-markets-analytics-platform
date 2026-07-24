import pandas as pd
import mysql.connector

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# =========================
# DATABASE SETTINGS
# =========================
db_config = DB_CONFIG

# =========================
# CARREGAR O CSV
# =========================
csv_path = FED_SOURCE_DIR / "Charge-Off Rate on Credit Card Loans, All Commercial Banks.csv"
df = pd.read_csv(csv_path)

# Rename columns to match the SQL table
df.columns = ['observation_date', 'charge_off_rate']

# Converter a data para o formato correto
df['observation_date'] = pd.to_datetime(df['observation_date'])

# =========================
# INSERIR NO MySQL
# =========================
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        sql = """
        INSERT INTO fed_charge_off_rate_credit_cards (observation_date, charge_off_rate)
        VALUES (%s, %s)
        """
        cursor.execute(sql, (row['observation_date'].strftime('%Y-%m-%d'), float(row['charge_off_rate'])))

    conn.commit()
    print(f"{len(df)} rows inserted successfully into table fed_charge_off_rate_credit_cards!")

except Exception as e:
    print("Error inserting data:", e)

finally:
    cursor.close()
    conn.close()
