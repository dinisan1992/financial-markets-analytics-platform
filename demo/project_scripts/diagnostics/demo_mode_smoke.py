from __future__ import annotations


from asset_config import ASSETS
from demo.data import (
    build_demo_multi_asset_price_frame,
    load_demo_asset_data,
    load_demo_events,
    load_demo_macro_pair,
)


def main() -> int:
    failures = []

    for asset_key in ASSETS:
        try:
            frame = load_demo_asset_data(
                ASSETS,
                asset_key,
                start_date="2020-01-01",
                end_date="2021-12-31",
            )
            if frame.empty:
                failures.append(f"{asset_key}: empty frame")
                continue
            if not (
                frame["high"] >= frame[["open", "close"]].max(axis=1)
            ).all():
                failures.append(f"{asset_key}: invalid high")
            if not (
                frame["low"] <= frame[["open", "close"]].min(axis=1)
            ).all():
                failures.append(f"{asset_key}: invalid low")
        except Exception as exc:
            failures.append(f"{asset_key}: {exc}")

    prices, report = build_demo_multi_asset_price_frame(
        ASSETS,
        ["BTC", "SP500", "NASDAQ100", "GOLD", "DXY", "VIX", "US10Y", "WTI_OIL"],
        start_date="2020-01-01",
        end_date="2024-12-31",
        return_load_report=True,
    )
    if prices.empty or not report["status"].eq("loaded").all():
        failures.append("multi-asset demo frame failed")

    events = load_demo_events()
    if events.empty:
        failures.append("events are empty")

    macro = load_demo_macro_pair(
        ASSETS,
        "FED_FUNDS_RATE",
        "SP500",
        "2020-01-01",
        "2024-12-31",
    )
    if macro.empty:
        failures.append("macro pair is empty")
    elif not (macro["macro_observation_date"] <= macro["snapped_at"]).all():
        failures.append("macro look-ahead detected")

    if failures:
        print("DEMO SMOKE TEST FAILED")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("DEMO SMOKE TEST PASSED")
    print(f"Assets checked: {len(ASSETS)}")
    print(f"Multi-asset rows: {len(prices):,}")
    print(f"Events: {len(events)}")
    print(f"Macro aligned rows: {len(macro):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
