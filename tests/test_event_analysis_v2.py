import unittest

import pandas as pd

from services.event_analysis_service import (
    calculate_event_forward_returns,
    calculate_event_recovery_analysis,
)


class EventAnalysisV2Tests(unittest.TestCase):
    def setUp(self):
        self.prices = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=12, freq="D"),
                "close": [100, 95, 90, 92, 98, 101, 103, 102, 105, 106, 107, 108],
            }
        )

    def test_excludes_approximate_events_by_default(self):
        events = pd.DataFrame(
            {
                "event_date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "date_precision": ["year", "exact"],
                "event_title": ["Approximate", "Exact"],
            }
        )

        result = calculate_event_forward_returns(events, self.prices, horizons=(1,))

        self.assertEqual(result["Event"].tolist(), ["Exact"])
        self.assertEqual(result["Date Precision"].tolist(), ["exact"])

    def test_calculates_known_forward_return(self):
        events = pd.DataFrame(
            {
                "event_date": pd.to_datetime(["2024-01-01"]),
                "date_precision": ["exact"],
                "event_title": ["Test"],
            }
        )

        result = calculate_event_forward_returns(events, self.prices, horizons=(5,))

        self.assertAlmostEqual(result.iloc[0]["Return +5D %"], 1.0)

    def test_event_market_date_never_precedes_event_date(self):
        events = pd.DataFrame(
            {
                "event_date": pd.to_datetime(["2024-01-06"]),
                "date_precision": ["exact"],
                "event_title": ["Weekend Event"],
            }
        )
        market_prices = pd.DataFrame(
            {
                "snapped_at": pd.to_datetime(["2024-01-05", "2024-01-08", "2024-01-09"]),
                "close": [100.0, 101.0, 102.0],
            }
        )

        result = calculate_event_forward_returns(events, market_prices, horizons=(1,))

        self.assertGreaterEqual(result.iloc[0]["Market Date"], result.iloc[0]["Event Date"])

    def test_recovery_analysis_finds_trough_and_recovery(self):
        event = {"event_date": "2024-01-01", "date_precision": "exact"}

        result, report = calculate_event_recovery_analysis(
            event=event,
            asset_keys=["TEST"],
            assets_config={"TEST": {"display_name": "Test Asset"}},
            load_asset_data_func=lambda **kwargs: self.prices,
            horizon_days=10,
        )

        self.assertEqual(result.iloc[0]["Max Drawdown %"], -10.0)
        self.assertEqual(result.iloc[0]["Days to Trough"], 2)
        self.assertEqual(result.iloc[0]["Recovery Days"], 5)
        self.assertEqual(report.iloc[0]["status"], "loaded")


if __name__ == "__main__":
    unittest.main()
