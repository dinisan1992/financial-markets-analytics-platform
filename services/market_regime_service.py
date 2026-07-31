import numpy as np
import pandas as pd


REGIME_ASSETS = [
    "SP500",
    "NASDAQ100",
    "BTC",
    "VIX",
    "DXY",
    "US10Y",
    "GOLD",
    "BRENT_OIL",
    "FINANCIAL_CONDITIONS",
]

REQUIRED_REGIME_ASSETS = ["SP500", "NASDAQ100", "VIX", "DXY", "US10Y"]


def prepare_market_regime_features(price_df: pd.DataFrame, rolling_window=30):
    """Build regime features on the S&P 500 trading-session calendar."""
    if price_df is None or price_df.empty or "snapped_at" not in price_df:
        return pd.DataFrame()

    missing = [asset for asset in REQUIRED_REGIME_ASSETS if asset not in price_df.columns]
    if missing:
        raise ValueError(f"Missing required regime assets: {', '.join(missing)}")

    frame = price_df.copy()
    frame["snapped_at"] = pd.to_datetime(frame["snapped_at"], errors="coerce")
    frame = frame.dropna(subset=["snapped_at"]).sort_values("snapped_at")

    value_columns = [column for column in frame.columns if column != "snapped_at"]
    frame[value_columns] = frame[value_columns].apply(pd.to_numeric, errors="coerce")

    # The anchor prevents weekends and crypto-only dates from becoming fake sessions.
    frame = frame[frame["SP500"].notna()].copy()
    frame[value_columns] = frame[value_columns].ffill(limit=3)
    frame = frame.dropna(subset=REQUIRED_REGIME_ASSETS).reset_index(drop=True)

    for column in value_columns:
        frame[f"{column}_return_1obs"] = frame[column].pct_change(fill_method=None)
        frame[f"{column}_return_{rolling_window}obs"] = frame[column].pct_change(
            periods=rolling_window,
            fill_method=None,
        )

    frame["sp500_realized_vol"] = (
        frame["SP500_return_1obs"].rolling(rolling_window).std() * np.sqrt(252)
    )
    frame[f"US10Y_change_{rolling_window}obs"] = frame["US10Y"].diff(rolling_window)
    frame[f"VIX_change_{rolling_window}obs"] = frame["VIX"].diff(rolling_window)

    if "FINANCIAL_CONDITIONS" in frame:
        frame[f"FINANCIAL_CONDITIONS_change_{rolling_window}obs"] = frame[
            "FINANCIAL_CONDITIONS"
        ].diff(rolling_window)

    return frame


def classify_market_regime_row(row, rolling_window=30):
    scores = {
        "Risk-On": 0,
        "Risk-Off": 0,
        "High Volatility": 0,
        "Dollar Strength": 0,
        "Yield Pressure": 0,
        "Commodity Shock": 0,
        "Financial Stress": 0,
    }

    suffix = f"_{rolling_window}obs"
    if row.get(f"SP500_return{suffix}", np.nan) > 0.03:
        scores["Risk-On"] += 1
    if row.get(f"NASDAQ100_return{suffix}", np.nan) > 0.04:
        scores["Risk-On"] += 1
    if row.get(f"BTC_return{suffix}", np.nan) > 0.08:
        scores["Risk-On"] += 1
    if row.get("VIX", np.nan) < 20:
        scores["Risk-On"] += 1

    if row.get(f"SP500_return{suffix}", np.nan) < -0.05:
        scores["Risk-Off"] += 1
    if row.get(f"NASDAQ100_return{suffix}", np.nan) < -0.06:
        scores["Risk-Off"] += 1
    if row.get(f"BTC_return{suffix}", np.nan) < -0.12:
        scores["Risk-Off"] += 1
    if row.get("VIX", np.nan) > 25:
        scores["Risk-Off"] += 1

    if row.get("VIX", np.nan) > 25:
        scores["High Volatility"] += 1
    if row.get(f"VIX_change{suffix}", np.nan) > 5:
        scores["High Volatility"] += 1
    if row.get("sp500_realized_vol", np.nan) > 0.25:
        scores["High Volatility"] += 1

    if row.get(f"DXY_return{suffix}", np.nan) > 0.02:
        scores["Dollar Strength"] += 1
    if row.get(f"GOLD_return{suffix}", np.nan) < 0:
        scores["Dollar Strength"] += 1
    if row.get(f"BTC_return{suffix}", np.nan) < 0:
        scores["Dollar Strength"] += 1

    if row.get(f"US10Y_change{suffix}", np.nan) > 0.25:
        scores["Yield Pressure"] += 1
    if row.get(f"NASDAQ100_return{suffix}", np.nan) < -0.04:
        scores["Yield Pressure"] += 1

    brent_return = row.get(f"BRENT_OIL_return{suffix}", np.nan)
    if brent_return > 0.10 or brent_return < -0.15:
        scores["Commodity Shock"] += 1

    if row.get(f"FINANCIAL_CONDITIONS_change{suffix}", np.nan) > 0.15:
        scores["Financial Stress"] += 1
    if row.get("VIX", np.nan) > 30:
        scores["Financial Stress"] += 1
    if row.get(f"SP500_return{suffix}", np.nan) < -0.07:
        scores["Financial Stress"] += 1

    max_score = max(scores.values())
    if max_score == 0:
        return "Neutral", 0

    winners = [name for name, score in scores.items() if score == max_score]
    if len(winners) > 1:
        return f"Mixed: {winners[0]} / {winners[1]}", max_score
    return winners[0], max_score


def classify_market_regimes(feature_df: pd.DataFrame, rolling_window=30):
    if feature_df is None or feature_df.empty:
        return pd.DataFrame()

    frame = feature_df.copy()
    classifications = frame.apply(
        lambda row: classify_market_regime_row(row, rolling_window=rolling_window),
        axis=1,
    )
    frame["market_regime"] = [value[0] for value in classifications]
    frame["regime_score"] = [value[1] for value in classifications]
    return frame


def summarize_regime_performance(regime_df: pd.DataFrame):
    if regime_df is None or regime_df.empty:
        return pd.DataFrame()

    return (
        regime_df.groupby("market_regime", as_index=False)
        .agg(
            Observations=("market_regime", "size"),
            Average_SP500_Daily_Return=("SP500_return_1obs", "mean"),
            Median_VIX=("VIX", "median"),
            Average_Realized_Volatility=("sp500_realized_vol", "mean"),
        )
        .sort_values("Observations", ascending=False)
        .reset_index(drop=True)
    )
