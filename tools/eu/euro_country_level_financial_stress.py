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
csv_path = EURO_SOURCE_DIR / "Country-Level Index of Financial Stress.csv"

chunk_size = 5000

# MySQL connection
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# Ler CSV em chunks
for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
    # Substituir NaN / valores 'nan' por None
    chunk = chunk.applymap(lambda x: None if pd.isna(x) or str(x).strip().lower() == 'nan' else x)

    # Inserir cada linha no MySQL
    for _, row in chunk.iterrows():
        sql = """
            INSERT IGNORE INTO euro_country_level_financial_stress (
                key_code, freq, ref_area, currency, provider_fm, instrument_fm, provider_fm_id, data_type_fm,
                time_period, obs_value, obs_status, obs_conf, obs_pre_break, obs_com, time_format, breaks,
                collection, compiling_org, diss_org, dom_ser_ids, fm_contract_time, fm_coupon_rate,
                fm_identifier, fm_lot_size, fm_maturity, fm_outs_amount, fm_put_call, fm_strike_price,
                publ_mu, publ_public, unit_index_base, compilation, coverage, decimals, source_agency,
                source_pub, title, title_compl, unit, unit_mult
            )
            VALUES (
                %(KEY)s, %(FREQ)s, %(REF_AREA)s, %(CURRENCY)s, %(PROVIDER_FM)s, %(INSTRUMENT_FM)s,
                %(PROVIDER_FM_ID)s, %(DATA_TYPE_FM)s, %(TIME_PERIOD)s, %(OBS_VALUE)s, %(OBS_STATUS)s,
                %(OBS_CONF)s, %(OBS_PRE_BREAK)s, %(OBS_COM)s, %(TIME_FORMAT)s, %(BREAKS)s, %(COLLECTION)s,
                %(COMPILING_ORG)s, %(DISS_ORG)s, %(DOM_SER_IDS)s, %(FM_CONTRACT_TIME)s, %(FM_COUPON_RATE)s,
                %(FM_IDENTIFIER)s, %(FM_LOT_SIZE)s, %(FM_MATURITY)s, %(FM_OUTS_AMOUNT)s, %(FM_PUT_CALL)s,
                %(FM_STRIKE_PRICE)s, %(PUBL_MU)s, %(PUBL_PUBLIC)s, %(UNIT_INDEX_BASE)s, %(COMPILATION)s,
                %(COVERAGE)s, %(DECIMALS)s, %(SOURCE_AGENCY)s, %(SOURCE_PUB)s, %(TITLE)s, %(TITLE_COMPL)s,
                %(UNIT)s, %(UNIT_MULT)s
            )
        """
        cursor.execute(sql, row.to_dict())

    conn.commit()
    print(f"{len(chunk)} rows inseridas.")

cursor.close()
conn.close()

print("✅ Data imported successfully para 'euro_country_level_financial_stress'!")
