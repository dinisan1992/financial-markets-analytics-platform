import unittest

import pandas as pd

from dashboard.asset_indicators import prepare_asset_technical_data


class AssetIndicatorPreparationV2Tests(unittest.TestCase):
    def _base_frame(self, periods=50):
        return pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=periods, freq="D"),
                "price": [float(100 + index) for index in range(periods)],
                "total_volume": [1000 + index for index in range(periods)],
            }
        )

    def test_preserves_valid_native_ohlc(self):
        frame = self._base_frame()
        frame["open"] = frame["price"] - 0.5
        frame["close"] = frame["price"]
        frame["high"] = frame["price"] + 1.0
        frame["low"] = frame["price"] - 1.0

        result = prepare_asset_technical_data(
            frame,
            asset_cfg={"periods_per_year": 252, "asset_class": "equity_index"},
        )

        self.assertTrue(result["ohlc_source"].eq("native").all())
        self.assertEqual(result.loc[10, "open"], frame.loc[10, "open"])
        self.assertEqual(result.loc[10, "high"], frame.loc[10, "high"])
        self.assertEqual(result.loc[10, "low"], frame.loc[10, "low"])

    def test_synthesizes_only_invalid_rows(self):
        frame = self._base_frame()
        frame["open"] = frame["price"] - 0.5
        frame["close"] = frame["price"]
        frame["high"] = frame["price"] + 1.0
        frame["low"] = frame["price"] - 1.0
        frame.loc[12, "high"] = frame.loc[12, "low"] - 1

        result = prepare_asset_technical_data(frame)

        self.assertEqual(result.loc[11, "ohlc_source"], "native")
        self.assertEqual(result.loc[12, "ohlc_source"], "synthetic")
        self.assertEqual(result.loc[13, "ohlc_source"], "native")

    def test_candle_shape_flags_are_disabled_for_synthetic_ohlc(self):
        frame = self._base_frame()
        frame.loc[40, "price"] = frame.loc[39, "price"] * 1.25
        frame.loc[40, "total_volume"] = 1000000

        result = prepare_asset_technical_data(frame)
        row = result.iloc[40]

        self.assertEqual(row["ohlc_source"], "synthetic")
        self.assertFalse(bool(row["candle_signal_eligible"]))
        self.assertFalse(bool(row["possible_pump_dump"]))
        self.assertFalse(bool(row["possible_spoofing"]))

    def test_native_ohlc_can_trigger_pump_dump_signal(self):
        frame = self._base_frame()
        frame["open"] = frame["price"] - 0.5
        frame["close"] = frame["price"]
        frame["high"] = frame["price"] + 1.0
        frame["low"] = frame["price"] - 1.0
        frame.loc[40, "price"] = frame.loc[39, "price"] * 1.25
        frame.loc[40, "close"] = frame.loc[40, "price"]
        frame.loc[40, "open"] = frame.loc[39, "price"]
        frame.loc[40, "high"] = frame.loc[40, "close"] + 1.0
        frame.loc[40, "low"] = frame.loc[40, "open"] - 1.0
        frame.loc[40, "total_volume"] = 1_000_000

        result = prepare_asset_technical_data(frame)

        self.assertEqual(result.loc[40, "ohlc_source"], "native")
        self.assertTrue(bool(result.loc[40, "possible_pump_dump"]))

    def test_native_ohlc_can_trigger_spoofing_like_signal(self):
        frame = self._base_frame()
        frame["open"] = frame["price"] - 0.5
        frame["close"] = frame["price"]
        frame["high"] = frame["price"] + 1.0
        frame["low"] = frame["price"] - 1.0
        frame.loc[40, "price"] = frame.loc[39, "price"] * 1.001
        frame.loc[40, "close"] = frame.loc[40, "price"]
        frame.loc[40, "open"] = frame.loc[40, "close"] - 0.01
        frame.loc[40, "high"] = frame.loc[40, "close"] + 5.0
        frame.loc[40, "low"] = frame.loc[40, "open"] - 5.0
        frame.loc[40, "total_volume"] = 1_000_000

        result = prepare_asset_technical_data(frame)

        self.assertEqual(result.loc[40, "ohlc_source"], "native")
        self.assertTrue(bool(result.loc[40, "possible_spoofing"]))

    def test_uses_asset_annualization_metadata(self):
        frame = self._base_frame(70)
        result = prepare_asset_technical_data(
            frame,
            asset_cfg={"periods_per_year": 365, "asset_class": "crypto"},
        )

        self.assertTrue(result["volatility_periods_per_year"].eq(365).all())

    def test_non_positive_level_series_get_consistent_synthetic_ohlc(self):
        frame = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=4, freq="D"),
                "price": [-0.5, -0.25, 0.0, 0.1],
            }
        )

        result = prepare_asset_technical_data(
            frame,
            asset_cfg={
                "positive_values_expected": False,
                "periods_per_year": 252,
                "asset_class": "financial_stress",
            },
        )

        self.assertEqual(len(result), 4)
        self.assertTrue((result["high"] >= result[["open", "close"]].max(axis=1)).all())
        self.assertTrue((result["low"] <= result[["open", "close"]].min(axis=1)).all())


if __name__ == "__main__":
    unittest.main()
