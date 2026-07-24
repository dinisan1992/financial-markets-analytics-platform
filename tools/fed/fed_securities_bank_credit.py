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
csv_path = FED_SOURCE_DIR / "Securities in Bank Credit, All Commercial Banks.csv"

# Ler o CSV
df = pd.read_csv(csv_path)

# Conectar ao MySQL
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# Inserir data linha a linha
for index, row in df.iterrows():
    sql = """
    INSERT INTO fed_securities_bank_credit (observation_date, securities_in_bank_credit)
    VALUES (%s, %s)
    ON DUPLICATE KEY UPDATE
        securities_in_bank_credit = VALUES(securities_in_bank_credit)
    """
    cursor.execute(sql, (row['observation_date'], row['SBCACBW027SBOG']))

# Commit and close connection
conn.commit()
cursor.close()
conn.close()

print("CSV loaded successfully into table fed_securities_bank_credit!")
