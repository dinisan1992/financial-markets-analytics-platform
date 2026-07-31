import unittest

import numpy as np
import pandas as pd

from indicators import (
    calcular_adx,
    calcular_atr,
    calcular_drawdown_duration,
    calcular_indicadores,
)


class IndicatorCalculationTests(unittest.TestCase):
    def _frame(self, prices):
        close = list(prices)
        return pd.DataFrame(
            {
                "snapped_at": pd.date_range("2024-01-01", periods=len(close), freq="D"),
                "price": close,
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "volume": [1000] * len(close),
                "total_volume": [1000] * len(close),
            }
        )

    def test_rsi_constant_prices_is_neutral(self):
        df = calcular_indicadores(self._frame([100] * 40))

        self.assertEqual(df["rsi"].dropna().iloc[-1], 50)

    def test_rsi_up_only_prices_is_overbought(self):
        df = calcular_indicadores(self._frame(range(1, 41)))

        self.assertEqual(df["rsi"].dropna().iloc[-1], 100)

    def test_rsi_down_only_prices_is_oversold(self):
        df = calcular_indicadores(self._frame(range(40, 0, -1)))

        self.assertEqual(df["rsi"].dropna().iloc[-1], 0)

    def test_price_change_does_not_fill_missing_prices(self):
        df = calcular_indicadores(self._frame([100, None, 110, 121]))

        self.assertTrue(pd.isna(df.loc[1, "price_change_pct"]))
        self.assertTrue(pd.isna(df.loc[2, "price_change_pct"]))
        self.assertAlmostEqual(df.loc[3, "price_change_pct"], 10.0)

    def test_volatility_uses_configured_periods_per_year(self):
        prices = [100 * (1.01 ** index) for index in range(60)]
        frame = self._frame(prices)

        crypto = calcular_indicadores(frame, periods_per_year=365)
        traditional = calcular_indicadores(frame, periods_per_year=252)

        crypto_vol = crypto["realized_volatility_30d"].dropna().iloc[-1]
        traditional_vol = traditional["realized_volatility_30d"].dropna().iloc[-1]

        self.assertAlmostEqual(
            crypto_vol / traditional_vol,
            np.sqrt(365 / 252),
            places=8,
        )
        self.assertEqual(crypto["volatility_periods_per_year"].iloc[-1], 365)
        self.assertEqual(traditional["volatility_periods_per_year"].iloc[-1], 252)

    def test_periods_per_year_must_be_positive(self):
        with self.assertRaises(ValueError):
            calcular_indicadores(self._frame(range(1, 41)), periods_per_year=0)

    def test_atr_uses_wilder_smoothing(self):
        high = pd.Series([10.0, 12.0, 13.0, 15.0])
        low = pd.Series([8.0, 9.0, 11.0, 12.0])
        close = pd.Series([9.0, 11.0, 12.0, 14.0])

        atr = calcular_atr(high, low, close, window=3)

        self.assertAlmostEqual(atr.iloc[2], 7 / 3)
        self.assertAlmostEqual(atr.iloc[3], (7 / 3) + (3 - (7 / 3)) / 3)

    def test_adx_reaches_100_for_a_persistent_one_way_move(self):
        close = pd.Series([float(value) for value in range(1, 10)])
        high = close + 1
        low = close - 1

        adx = calcular_adx(high, low, close, window=3)

        self.assertAlmostEqual(adx.dropna().iloc[-1], 100.0)

    def test_drawdown_duration_resets_at_a_new_high(self):
        duration = calcular_drawdown_duration(pd.Series([100.0, 90.0, 80.0, 100.0, 95.0]))

        self.assertEqual(duration.tolist(), [0, 1, 2, 0, 1])


if __name__ == "__main__":
    unittest.main()
