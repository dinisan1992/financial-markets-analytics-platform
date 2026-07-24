import unittest

import pandas as pd

from indicators import calcular_indicadores


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


if __name__ == "__main__":
    unittest.main()
