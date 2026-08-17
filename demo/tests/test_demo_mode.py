from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


DEMO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DEMO_ROOT.parent
for path in (str(DEMO_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from demo.data import (  # noqa: E402
    build_demo_macro_series,
    build_demo_multi_asset_price_frame,
    load_demo_asset_data,
    load_demo_events,
    load_demo_macro_pair,
)


try:
    from asset_config import ASSETS as PROJECT_ASSETS  # noqa: E402
except ImportError:
    PROJECT_ASSETS = None


ASSETS = {
    "BTC": {
        "table_name": "btc_analysis",
        "calendar_type": "continuous",
        "positive_values_expected": True,
        "volume_expected": True,
    },
    "SP500": {
        "table_name": "sp500_analysis",
        "calendar_type": "trading_days",
        "market_type": "equity_index",
        "positive_values_expected": True,
        "volume_expected": True,
    },
    "NASDAQ100": {
        "table_name": "nasdaq100_analysis",
        "calendar_type": "trading_days",
        "market_type": "equity_index",
        "positive_values_expected": True,
        "volume_expected": True,
    },
    "VIX": {
        "table_name": "vix_analysis",
        "calendar_type": "trading_days",
        "positive_values_expected": True,
        "volume_expected": False,
    },
}


class DemoDataTests(unittest.TestCase):
    def test_asset_generation_is_deterministic(self):
        first = load_demo_asset_data(ASSETS, "SP500", "2020-01-01", "2020-12-31")
        second = load_demo_asset_data(ASSETS, "SP500", "2020-01-01", "2020-12-31")
        pd.testing.assert_frame_equal(first, second)

    def test_demo_ohlc_is_internally_consistent(self):
        frame = load_demo_asset_data(ASSETS, "BTC", "2021-01-01", "2021-12-31")
        self.assertFalse(frame.empty)
        self.assertTrue(np.isfinite(frame[["open", "high", "low", "close"]]).all().all())
        self.assertTrue((frame["high"] >= frame[["open", "close"]].max(axis=1)).all())
        self.assertTrue((frame["low"] <= frame[["open", "close"]].min(axis=1)).all())
        self.assertTrue((frame[["open", "high", "low", "close"]] > 0).all().all())

    def test_demo_contains_exact_and_approximate_events(self):
        events = load_demo_events()
        self.assertIn("exact", set(events["date_precision"]))
        self.assertIn("year", set(events["date_precision"]))
        self.assertTrue(events["event_title"].str.contains("halving", case=False).any())

    def test_multi_asset_builder_returns_load_report(self):
        frame, report = build_demo_multi_asset_price_frame(
            ASSETS,
            ["BTC", "SP500", "VIX"],
            start_date="2020-01-01",
            end_date="2020-06-30",
            return_load_report=True,
        )
        self.assertFalse(frame.empty)
        self.assertEqual(set(report["status"]), {"loaded"})
        self.assertTrue({"BTC", "SP500", "VIX"}.issubset(frame.columns))

    def test_macro_alignment_never_uses_future_observation(self):
        frame = load_demo_macro_pair(
            ASSETS,
            macro_key="FED_FUNDS_RATE",
            market_asset="SP500",
            start_date="2020-01-01",
            end_date="2024-12-31",
        )
        self.assertFalse(frame.empty)
        self.assertTrue(
            (frame["macro_observation_date"] <= frame["snapped_at"]).all()
        )
        self.assertTrue((frame["macro_age_days"] >= 0).all())

    def test_asset_history_is_invariant_to_selected_start_date(self):
        wide = load_demo_asset_data(ASSETS, "SP500", "2020-01-01", "2024-12-31")
        narrow = load_demo_asset_data(ASSETS, "SP500", "2021-01-01", "2024-12-31")
        overlap = wide.merge(narrow, on="snapped_at", suffixes=("_wide", "_narrow"))
        self.assertFalse(overlap.empty)
        np.testing.assert_allclose(overlap["price_wide"], overlap["price_narrow"])

    def test_macro_history_is_invariant_to_selected_start_date(self):
        wide = build_demo_macro_series(
            "EURO_HICP_PROCESSED_FOOD", "2000-01-01", "2024-12-31"
        )
        narrow = build_demo_macro_series(
            "EURO_HICP_PROCESSED_FOOD", "2020-01-01", "2024-12-31"
        )
        overlap = wide.merge(narrow, on="snapped_at", suffixes=("_wide", "_narrow"))
        np.testing.assert_allclose(
            overlap["EURO_HICP_PROCESSED_FOOD_wide"],
            overlap["EURO_HICP_PROCESSED_FOOD_narrow"],
        )

    def test_demo_stress_and_macro_levels_are_plausible(self):
        vix = load_demo_asset_data(ASSETS, "VIX", "2020-01-01", "2024-12-31")
        hicp = build_demo_macro_series(
            "EURO_HICP_PROCESSED_FOOD", "2020-01-01", "2024-12-31"
        )
        self.assertTrue(vix["price"].between(8.0, 90.0).all())
        self.assertGreater(float(hicp["EURO_HICP_PROCESSED_FOOD"].median()), 80.0)

    def test_demo_equities_share_a_market_factor(self):
        prices = build_demo_multi_asset_price_frame(
            ASSETS,
            ["SP500", "NASDAQ100"],
            start_date="2020-01-01",
            end_date="2024-12-31",
        )
        returns = prices[["SP500", "NASDAQ100"]].pct_change(fill_method=None)
        self.assertGreater(float(returns.corr().iloc[0, 1]), 0.30)


@unittest.skipIf(PROJECT_ASSETS is None, "Project asset_config is not available")
class ProjectDemoContractTests(unittest.TestCase):
    def test_all_configured_project_assets_generate(self):
        self.assertGreaterEqual(len(PROJECT_ASSETS), 38)
        for asset_key in PROJECT_ASSETS:
            with self.subTest(asset=asset_key):
                frame = load_demo_asset_data(
                    PROJECT_ASSETS,
                    asset_key,
                    start_date="2020-01-01",
                    end_date="2020-12-31",
                )
                self.assertFalse(frame.empty)
                self.assertTrue(frame["price"].notna().all())
                self.assertTrue(frame["close"].notna().all())

    def test_runtime_patch_disables_database_engine(self):
        import importlib
        import os

        from demo.runtime import activate_demo_mode, deactivate_demo_mode

        previous_mode = os.environ.get("DATA_MODE")
        try:
            activate_demo_mode()
            macro_data_loader = importlib.import_module("macro_data_loader")
            self.assertIsNone(macro_data_loader.get_engine())
        finally:
            deactivate_demo_mode()
            if previous_mode is None:
                os.environ.pop("DATA_MODE", None)
            else:
                os.environ["DATA_MODE"] = previous_mode

    def test_default_portfolio_demo_frame_loads(self):
        selected = [
            key
            for key in [
                "BTC",
                "SP500",
                "NASDAQ100",
                "GOLD",
                "DXY",
                "VIX",
                "US10Y",
                "WTI_OIL",
            ]
            if key in PROJECT_ASSETS
        ]
        frame, report = build_demo_multi_asset_price_frame(
            PROJECT_ASSETS,
            selected,
            start_date="2020-01-01",
            end_date="2024-12-31",
            return_load_report=True,
        )
        self.assertFalse(frame.empty)
        self.assertTrue(report["status"].eq("loaded").all())


if __name__ == "__main__":
    unittest.main()
