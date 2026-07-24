import pandas as pd
import mysql.connector

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

from config import DB_CONFIG, EURO_SOURCE_DIR, FED_SOURCE_DIR, get_sqlalchemy_database_url


# ==============================
# DATABASE CONFIGURATION
# ==============================
db_config = DB_CONFIG

# CSV file path
csv_path = FED_SOURCE_DIR / "Consumer Loans Credit Cards and Other Revolving Plans, All Commercial Banks.csv"

# ==============================
# LEITURA DO CSV
# ==============================
df = pd.read_csv(csv_path)

# Rename columns to match the SQL table
df.columns = ['observation_date', 'consumer_loans']

# Converter datas
df['observation_date'] = pd.to_datetime(df['observation_date'])

# ==============================
# DATABASE INSERT
# ==============================
try:
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        sql = """
        INSERT INTO fed_consumer_loans_credit_cards (observation_date, consumer_loans)
        VALUES (%s, %s)
        """
        cursor.execute(sql, (row['observation_date'].date(), row['consumer_loans']))

    conn.commit()
    print(f"{len(df)} records inserted successfully em 'fed_consumer_loans_credit_cards'.")

except Exception as e:
    print("Error inserting data:", e)

finally:
    cursor.close()
    conn.close()
