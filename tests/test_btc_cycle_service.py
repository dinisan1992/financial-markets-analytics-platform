import unittest

import pandas as pd

from services.btc_cycle_service import (
    calculate_btc_auto_detected_cycles,
    calculate_btc_halving_impact_from_events,
)


class BtcCycleServiceTests(unittest.TestCase):
    @staticmethod
    def _events(event_date):
        return pd.DataFrame(
            {
                "event_date": pd.to_datetime([event_date]),
                "event_title": ["BTC Halving"],
                "event_category": ["Halving"],
                "event_description": ["Block reward halving"],
                "event_source_table": ["bitcoin_historical_events"],
            }
        )

    def test_halving_impact_uses_known_forward_prices(self):
        prices = pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=11, freq="D"),
                "close": [100.0, 95.0, 90.0, 110.0, 120.0, 150.0, 140.0, 160.0, 155.0, 150.0, 145.0],
            }
        )

        result = calculate_btc_halving_impact_from_events(
            prices,
            self._events("2024-01-01"),
            analysis_window_days=10,
            return_horizons=(5, 10),
        )

        self.assertAlmostEqual(result.iloc[0]["Return +5D %"], 50.0)
        self.assertAlmostEqual(result.iloc[0]["Max Drawdown from Halving %"], -10.0)
        self.assertAlmostEqual(result.iloc[0]["Max Upside from Halving %"], 60.0)

    def test_auto_cycle_detects_known_bear_bottom_and_recovery(self):
        dates = pd.date_range("2024-01-01", periods=51, freq="D")
        prices = [100.0]
        prices.extend([99.0 - index * 2.0 for index in range(30)])
        prices.extend([40.0, 30.0, 20.0, 25.0, 35.0])
        prices.extend([40.0 + index * 4.0 for index in range(1, 16)])
        frame = pd.DataFrame({"snapped_at": dates, "close": prices})

        result = calculate_btc_auto_detected_cycles(
            frame,
            self._events("2024-02-10"),
            min_drawdown_pct=60,
            min_days_after_top=30,
        )

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result.iloc[0]["Drawdown %"], -80.0)
        self.assertEqual(str(result.iloc[0]["Cycle Bottom Date"]), "2024-02-03")
        self.assertEqual(result.iloc[0]["Halving Event"], "BTC Halving")


if __name__ == "__main__":
    unittest.main()
