import unittest

import pandas as pd

from services.market_regime_service import (
    classify_market_regimes,
    prepare_market_regime_features,
    summarize_regime_performance,
)


class MarketRegimeServiceTests(unittest.TestCase):
    def _price_frame(self):
        periods = 90
        return pd.DataFrame(
            {
                "snapped_at": pd.bdate_range("2024-01-01", periods=periods),
                "SP500": [100.0 + index for index in range(periods)],
                "NASDAQ100": [100.0 + index * 1.5 for index in range(periods)],
                "BTC": [100.0 + index * 3.0 for index in range(periods)],
                "VIX": [15.0] * periods,
                "DXY": [100.0] * periods,
                "US10Y": [4.0] * periods,
                "GOLD": [2000.0] * periods,
                "BRENT_OIL": [80.0] * periods,
                "FINANCIAL_CONDITIONS": [0.0] * periods,
            }
        )

    def test_preparation_and_classification_produce_risk_on_regime(self):
        features = prepare_market_regime_features(self._price_frame(), rolling_window=30)
        regimes = classify_market_regimes(features, rolling_window=30)

        self.assertEqual(regimes.iloc[-1]["market_regime"], "Risk-On")
        self.assertEqual(regimes.iloc[-1]["regime_score"], 4)

    def test_summary_counts_all_classified_observations(self):
        features = prepare_market_regime_features(self._price_frame(), rolling_window=30)
        regimes = classify_market_regimes(features, rolling_window=30)
        summary = summarize_regime_performance(regimes)

        self.assertEqual(int(summary["Observations"].sum()), len(regimes))


if __name__ == "__main__":
    unittest.main()
