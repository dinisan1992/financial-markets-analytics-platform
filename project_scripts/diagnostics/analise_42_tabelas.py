from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine, inspect, text

from config import get_sqlalchemy_database_url

# ==========================
# CONNECTION CONFIGURATION
# ==========================
db_url = get_sqlalchemy_database_url()
engine = create_engine(db_url)
inspector = inspect(engine)

# ==========================
# INFORMATION EXTRACTION
# ==========================
tables_info = []

for table_name in inspector.get_table_names():
    try:
        # Count the number of records
        with engine.connect() as conn:
            count_query = text(f"SELECT COUNT(*) AS total FROM `{table_name}`")
            count_result = conn.execute(count_query).fetchone()
            total_records = count_result[0] if count_result else 0

        # Extract columns
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        num_columns = len(columns)

        # Store info
        tables_info.append({
            "Table": table_name,
            "No. Records": total_records,
            "No. Columns": num_columns,
            "Columns": ", ".join(columns)
        })
        print(f"✅ {table_name}: {total_records} records, {num_columns} columns")

    except Exception as e:
        print(f"⚠️ Error processing {table_name}: {e}")
        tables_info.append({
            "Table": table_name,
            "No. Records": "Error",
            "No. Columns": "Error",
            "Columns": str(e)
        })

# ==========================
# CREATE REPORT
# ==========================
df_info = pd.DataFrame(tables_info)
output_path = "complete_tables_summary.csv"
df_info.to_csv(output_path, index=False, encoding="utf-8-sig")

print(f"\n✅ Full report created successfully: {output_path}")

