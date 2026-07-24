from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd

from macro_data_loader import get_engine
from asset_config import ASSETS
from dashboard.correlation_data import (
    build_multi_asset_price_frame,
    calculate_returns,
    build_scatter_returns_frame
)

engine = get_engine()

assets = [
    "BTC",
    "SP500",
    "NASDAQ100",
    "GOLD",
    "DXY",
    "VIX",
    "US10Y",
    "WTI_OIL",
    "BRENT_OIL"
]

assets = [a for a in assets if a in ASSETS]

print("ASSETS USED:")
print(assets)

print("\nBUILDING PRICE FRAME...")
price_df = build_multi_asset_price_frame(
    engine,
    assets,
    ASSETS,
    start_date="2020-01-01",
    end_date="2026-12-31",
    forward_fill=True
)

print(price_df.head().to_string())
print(price_df.tail().to_string())
print("\nPRICE DF SHAPE:", price_df.shape)
print("PRICE DF COLUMNS:", price_df.columns.tolist())
print("PRICE NON-NA:")
print(price_df.notna().sum())

print("\nCALCULATING RETURNS...")
returns_df = calculate_returns(price_df)

print(returns_df.head().to_string())
print(returns_df.tail().to_string())
print("\nRETURNS DF SHAPE:", returns_df.shape)
print("RETURNS DF COLUMNS:", returns_df.columns.tolist())
print("RETURNS NON-NA:")
print(returns_df.notna().sum())

print("\nBUILDING SCATTER BTC vs SP500...")
scatter_df = build_scatter_returns_frame(
    returns_df,
    "BTC",
    "SP500"
)

print(scatter_df.head().to_string())
print(scatter_df.tail().to_string())
print("\nSCATTER SHAPE:", scatter_df.shape)
print("SCATTER COLUMNS:", scatter_df.columns.tolist())
print("SCATTER NON-NA:")
print(scatter_df.notna().sum())

