from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from macro_data_loader import get_engine

engine = get_engine()

print("=== BTC_ANALYSIS COLUMNS ===")

cols_df = pd.read_sql("DESCRIBE btc_analysis;", engine)
print(cols_df.to_string())

cols = cols_df["Field"].tolist()

if "close" in cols:
    price_col = "close"
elif "price" in cols:
    price_col = "price"
else:
    raise ValueError("Neither 'close' nor 'price' exists in btc_analysis.")

print(f"\nUsing price column: {price_col}")

print("\n=== BTC DATA START SAMPLE ===")

q1 = f"""
SELECT snapped_at, `{price_col}` AS close_price
FROM btc_analysis
WHERE snapped_at >= '2012-01-01'
ORDER BY snapped_at ASC
LIMIT 20;
"""

df1 = pd.read_sql(q1, engine)
print(df1.to_string())

print("\n=== HALVING WINDOWS ===")

q2 = f"""
SELECT snapped_at, `{price_col}` AS close_price
FROM btc_analysis
WHERE
    snapped_at BETWEEN '2012-11-20' AND '2012-12-05'
    OR snapped_at BETWEEN '2016-07-01' AND '2016-07-15'
    OR snapped_at BETWEEN '2020-05-01' AND '2020-05-20'
    OR snapped_at BETWEEN '2024-04-10' AND '2024-04-30'
ORDER BY snapped_at ASC;
"""

df2 = pd.read_sql(q2, engine)
print(df2.to_string())

print("\n=== CLOSEST PRICE TO EACH HALVING ===")

halvings = [
    ("First Bitcoin halving", "2012-11-28"),
    ("Second Bitcoin halving", "2016-07-09"),
    ("Third Bitcoin halving", "2020-05-11"),
    ("Fourth Bitcoin halving", "2024-04-20"),
]

for name, date_value in halvings:
    q = f"""
    SELECT snapped_at, `{price_col}` AS close_price
    FROM btc_analysis
    WHERE snapped_at >= '{date_value}'
    ORDER BY snapped_at ASC
    LIMIT 1;
    """

    df = pd.read_sql(q, engine)

    print(f"\n{name} - {date_value}")
    if df.empty:
        print("No price found.")
    else:
        print(df.to_string(index=False))

