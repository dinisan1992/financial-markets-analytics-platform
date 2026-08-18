from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


DEMO_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DEMO_ROOT.parent
for path in (str(DEMO_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from asset_config import ASSETS  # noqa: E402
from euro_series_config import EURO_SERIES  # noqa: E402
from macro_config import MACRO_ASSETS  # noqa: E402
from demo.snapshot_data import (  # noqa: E402
    build_snapshot_multi_asset_price_frame,
    load_snapshot_asset_data,
    load_snapshot_events,
    snapshot_manifest,
)


def main() -> int:
    failures = []
    manifest = snapshot_manifest()

    missing_assets = sorted(set(ASSETS) - set(manifest.get("assets", {})))
    if missing_assets:
        failures.append(f"missing assets: {missing_assets}")

    missing_fed = sorted(set(MACRO_ASSETS) - set(manifest.get("fed", {})))
    if missing_fed:
        failures.append(f"missing FED series: {missing_fed}")

    enabled_euro = {
        key for key, cfg in EURO_SERIES.items()
        if cfg.get("enabled", True) is True
    }
    missing_euro = sorted(enabled_euro - set(manifest.get("euro", {})))
    if missing_euro:
        failures.append(f"missing EURO series: {missing_euro}")

    for asset_key in ASSETS:
        try:
            frame = load_snapshot_asset_data(ASSETS, asset_key, "2020-01-01", None)
            if frame.empty:
                failures.append(f"{asset_key}: empty")
            elif "price" not in frame.columns:
                failures.append(f"{asset_key}: price missing")
        except Exception as exc:
            failures.append(f"{asset_key}: {exc}")

    prices, report = build_snapshot_multi_asset_price_frame(
        ASSETS,
        ["BTC", "SP500", "NASDAQ100", "GOLD", "DXY", "VIX", "US10Y", "WTI_OIL"],
        start_date="2020-01-01",
        end_date=None,
        return_load_report=True,
    )
    if prices.empty or not report["status"].eq("loaded").all():
        failures.append("default multi-asset frame failed")

    events = load_snapshot_events()
    if events.empty:
        failures.append("event snapshot is empty")

    if failures:
        print("PUBLIC SNAPSHOT VALIDATION FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    btc = load_snapshot_asset_data(ASSETS, "BTC", "2020-01-01", None)
    print("PUBLIC SNAPSHOT VALIDATION PASSED")
    print(f"Assets: {len(ASSETS)}")
    print(f"FED series: {len(MACRO_ASSETS)}")
    print(f"EURO active series: {len(enabled_euro)}")
    print(f"Events: {len(events)}")
    print(f"BTC 2020+ rows: {len(btc):,}")
    print(f"Multi-asset rows: {len(prices):,}")
    print(f"Snapshot generated: {manifest.get('generated_at_utc')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
