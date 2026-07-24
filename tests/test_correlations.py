import unittest

import pandas as pd

from dashboard.correlation_data import (
    calculate_returns,
    calculate_rolling_correlation,
)


class CorrelationCalculationTests(unittest.TestCase):
    def test_returns_use_previous_valid_asset_price_after_calendar_gaps(self):
        price_df = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=5, freq="D"),
                "BTC": [100, 110, 121, 133.1, 146.41],
                "SP500": [1000, None, None, 1100, 1210],
            }
        )

        returns_df = calculate_returns(price_df, method="pct")

        sp500_returns = returns_df.set_index("snapped_at")["SP500"]

        self.assertAlmostEqual(sp500_returns.loc[pd.Timestamp("2024-01-04")], 0.10)
        self.assertAlmostEqual(sp500_returns.loc[pd.Timestamp("2024-01-05")], 0.10)

    def test_rolling_correlation_uses_pairwise_valid_observations(self):
        returns_df = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=9, freq="D"),
                "BTC": [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09],
                "SP500": [0.02, None, 0.04, None, 0.06, None, 0.08, None, 0.10],
            }
        )

        rolling_df = calculate_rolling_correlation(
            returns_df=returns_df,
            asset_x="BTC",
            asset_y="SP500",
            window=3,
        )

        self.assertFalse(rolling_df.empty)
        self.assertEqual(3, len(rolling_df))
        self.assertTrue(rolling_df["rolling_correlation"].notna().all())


if __name__ == "__main__":
    unittest.main()
