import unittest

import pandas as pd

from services.macro_analytics_service import (
    align_macro_to_market_calendar,
    prepare_macro_market_features,
)


class MacroAnalyticsServiceTests(unittest.TestCase):
    def test_alignment_uses_market_dates_and_never_future_macro_values(self):
        macro = pd.DataFrame(
            {
                "snapped_at": pd.to_datetime(["2024-01-01", "2024-01-04"]),
                "MACRO": [10.0, 20.0],
            }
        )
        market = pd.DataFrame(
            {
                "snapped_at": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-05"]),
                "MARKET": [100.0, 101.0, 102.0],
            }
        )

        result = align_macro_to_market_calendar(
            macro,
            market,
            "MACRO",
            "MARKET",
            max_macro_age_days=10,
        )

        self.assertEqual(result["snapped_at"].tolist(), market["snapped_at"].tolist())
        self.assertEqual(result["MACRO"].tolist(), [10.0, 10.0, 20.0])
        self.assertEqual(result["macro_age_days"].tolist(), [1, 2, 1])

    def test_features_are_observation_based(self):
        dates = pd.bdate_range("2024-01-01", periods=120)
        aligned = pd.DataFrame(
            {
                "snapped_at": dates,
                "macro_observation_date": dates,
                "macro_age_days": 0,
                "MACRO": [100.0 + index for index in range(120)],
                "MARKET": [200.0 + index * 2 for index in range(120)],
            }
        )

        result = prepare_macro_market_features(aligned, "MACRO", "MARKET")

        self.assertIn("rolling_correlation_90obs", result)
        self.assertIn("MACRO_zscore_90obs", result)
        self.assertNotIn("annualized_volatility", result)


if __name__ == "__main__":
    unittest.main()
