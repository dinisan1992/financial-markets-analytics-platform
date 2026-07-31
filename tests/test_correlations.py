import unittest

import pandas as pd

from dashboard.correlation_data import (
    calculate_returns,
    calculate_rolling_correlation,
)
from services.correlation_quality_service import (
    build_pair_correlation_statistics,
    classify_correlation_confidence,
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

    def test_pair_statistics_report_coverage_period_and_confidence_interval(self):
        observations = 300
        returns_df = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=observations, freq="D"),
                "A": [index / 10000 for index in range(observations)],
                "B": [index / 5000 for index in range(observations)],
            }
        )

        result = build_pair_correlation_statistics(returns_df).iloc[0]

        self.assertEqual(result["common_observations"], observations)
        self.assertEqual(result["coverage_ratio"], 1.0)
        self.assertEqual(result["confidence"], "HIGH")
        self.assertAlmostEqual(result["correlation"], 1.0)
        self.assertLessEqual(result["correlation_ci95_low"], result["correlation"])

    def test_confidence_requires_both_sample_size_and_coverage(self):
        self.assertEqual(classify_correlation_confidence(29, 100), "INSUFFICIENT")
        self.assertEqual(classify_correlation_confidence(300, 60), "LOW")
        self.assertEqual(classify_correlation_confidence(120, 95), "MODERATE")
        self.assertEqual(classify_correlation_confidence(300, 95), "HIGH")

    def test_constant_pair_is_not_reported_as_high_confidence(self):
        returns_df = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=300, freq="D"),
                "A": [0.01] * 300,
                "B": [0.02] * 300,
            }
        )

        result = build_pair_correlation_statistics(returns_df).iloc[0]

        self.assertTrue(pd.isna(result["correlation"]))
        self.assertEqual(result["confidence"], "INSUFFICIENT")
        self.assertTrue(result["potential_bias"])


if __name__ == "__main__":
    unittest.main()
