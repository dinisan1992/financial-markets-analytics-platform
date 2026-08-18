from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd


DEMO_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DEMO_ROOT.parent
for path in (str(DEMO_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from asset_config import ASSETS  # noqa: E402
from dashboard.asset_indicators import prepare_asset_technical_data  # noqa: E402
from demo.snapshot_data import load_snapshot_asset_data  # noqa: E402
from macro_data_loader import get_engine  # noqa: E402
from services import data_access_service  # noqa: E402


CRITICAL_COLUMNS = [
    "snapped_at",
    "price",
    "open",
    "high",
    "low",
    "close",
    "total_volume",
    "rsi",
    "stoch_rsi_k",
    "stoch_rsi_d",
    "macd",
    "macd_signal",
    "macd_hist",
    "ema_9",
    "ema_20",
    "ema_50",
    "ema_200",
    "drawdown_pct",
    "rolling_volatility_30d",
]


def main() -> int:
    engine = get_engine()
    start = "2020-01-01"

    live_raw = data_access_service.load_asset_data(
        engine=engine,
        assets_config=ASSETS,
        asset_key="BTC",
        start_date=start,
        end_date=None,
    )
    snapshot_raw = load_snapshot_asset_data(
        ASSETS,
        "BTC",
        start_date=start,
        end_date=None,
    )

    live = prepare_asset_technical_data(live_raw, ASSETS["BTC"])
    snap = prepare_asset_technical_data(snapshot_raw, ASSETS["BTC"])

    columns = [
        column for column in CRITICAL_COLUMNS
        if column in live.columns and column in snap.columns
    ]

    if len(live) != len(snap):
        raise AssertionError(f"BTC row count differs: live={len(live)} snapshot={len(snap)}")

    for column in columns:
        if column == "snapped_at":
            left = pd.to_datetime(live[column]).reset_index(drop=True)
            right = pd.to_datetime(snap[column]).reset_index(drop=True)
            if not left.equals(right):
                raise AssertionError("BTC dates differ")
            continue

        left = pd.to_numeric(live[column], errors="coerce").to_numpy(dtype=float)
        right = pd.to_numeric(snap[column], errors="coerce").to_numpy(dtype=float)
        if not np.allclose(left, right, rtol=1e-10, atol=1e-10, equal_nan=True):
            max_diff = np.nanmax(np.abs(left - right))
            raise AssertionError(f"{column} differs; max absolute difference={max_diff}")

    print("LIVE VS SNAPSHOT BTC COMPARISON PASSED")
    print(f"Rows compared: {len(live):,}")
    print(f"Chart-critical columns compared: {len(columns)}")
    print("The Asset Explorer receives the same BTC observations and derives the same indicators.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
