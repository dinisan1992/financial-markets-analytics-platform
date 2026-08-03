import unittest

import pandas as pd

from services.export_service import dataframe_to_csv_bytes
from services.risk_statistics_service import (
    calculate_return_distribution_summary,
    calculate_suspicion_score,
    filter_df_by_recent_window,
    get_return_column,
)
from services.technical_signal_service import (
    build_current_technical_interpretation,
    calculate_technical_signal_summary,
)


class TechnicalSignalServiceTests(unittest.TestCase):
    def test_calculates_bullish_technical_summary(self):
        df = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=35, freq="D"),
                "close": [100] * 34 + [120],
                "ema_50": [95] * 35,
                "ema_200": [90] * 35,
                "rsi": [55] * 34 + [72],
                "macd": [1.2] * 35,
                "macd_signal": [0.8] * 35,
                "volume_zscore": [0.5] * 34 + [3.0],
                "rolling_volatility_30d": [10] * 34 + [20],
                "suspicious_event": [False] * 27 + [True] * 8,
            }
        )

        summary = calculate_technical_signal_summary(df)

        self.assertEqual(summary["trend"], "Bullish")
        self.assertEqual(summary["price_vs_ema200"], "Above EMA200")
        self.assertEqual(summary["rsi_state"], "Overbought")
        self.assertEqual(summary["macd_state"], "Bullish")
        self.assertEqual(summary["volume_state"], "Volume Spike")
        self.assertEqual(summary["volatility_state"], "Elevated")
        self.assertEqual(summary["suspicious_state"], "High")

    def test_builds_empty_interpretation_when_summary_missing(self):
        self.assertEqual(
            build_current_technical_interpretation({}),
            "No technical interpretation is available.",
        )


class RiskStatisticsServiceTests(unittest.TestCase):
    def test_filters_recent_window_from_latest_available_date(self):
        df = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=40, freq="D"),
                "close": range(40),
            }
        )

        filtered = filter_df_by_recent_window(df, "Last 7D")

        self.assertEqual(len(filtered), 8)
        self.assertEqual(filtered["snapped_at"].min(), pd.Timestamp("2024-02-02"))

    def test_calculates_suspicion_score_level(self):
        df = pd.DataFrame(
            {
                "suspicious_event": [True, True, False, False],
                "volume_spike": [True, False, False, False],
                "possible_pump_dump": [True, False, False, False],
                "high_volume_candle_rejection": [False, True, False, False],
                "extreme_rsi": [True, False, False, False],
            }
        )

        score = calculate_suspicion_score(df)

        self.assertEqual(score["suspicious_events"], 2)
        self.assertEqual(score["pump_dump"], 1)
        self.assertEqual(score["candle_rejection"], 1)
        self.assertEqual(score["spoofing"], 1)
        self.assertEqual(score["risk_level"], "Extreme")
        self.assertEqual(score["score"], 100)

    def test_return_distribution_uses_first_supported_return_column(self):
        df = pd.DataFrame({"daily_return_pct": [1.0, -2.0, 3.0, None]})

        self.assertEqual(get_return_column(df), "daily_return_pct")

        summary = calculate_return_distribution_summary(df)

        self.assertEqual(summary["observations"], 3)
        self.assertAlmostEqual(summary["average_return"], 2 / 3)
        self.assertAlmostEqual(summary["positive_days_pct"], 2 / 3 * 100)
        self.assertAlmostEqual(summary["negative_days_pct"], 1 / 3 * 100)


class ExportServiceTests(unittest.TestCase):
    def test_dataframe_to_csv_bytes_returns_none_for_empty_frame(self):
        self.assertIsNone(dataframe_to_csv_bytes(pd.DataFrame()))

    def test_dataframe_to_csv_bytes_encodes_csv(self):
        csv_data = dataframe_to_csv_bytes(pd.DataFrame({"a": [1], "b": [2]}))

        self.assertEqual(csv_data, b"a,b\r\n1,2\r\n")


if __name__ == "__main__":
    unittest.main()
