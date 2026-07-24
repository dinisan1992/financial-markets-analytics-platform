import numpy as np
import pandas as pd


def calculate_technical_signal_summary(df: pd.DataFrame):
    if df is None or df.empty:
        return {}

    plot_df = df.copy()
    plot_df["snapped_at"] = pd.to_datetime(plot_df["snapped_at"], errors="coerce")
    plot_df = plot_df.dropna(subset=["snapped_at"]).sort_values("snapped_at").reset_index(drop=True)

    if plot_df.empty:
        return {}

    latest = plot_df.iloc[-1]

    signal_date = latest.get("snapped_at", None)
    close = latest.get("close", np.nan)
    ema_50 = latest.get("ema_50", np.nan)
    ema_200 = latest.get("ema_200", np.nan)
    rsi = latest.get("rsi", np.nan)
    macd = latest.get("macd", np.nan)
    macd_signal = latest.get("macd_signal", np.nan)
    volume_zscore = latest.get("volume_zscore", np.nan)
    current_volatility = latest.get("rolling_volatility_30d", np.nan)

    trend = "Neutral"

    if pd.notna(close) and pd.notna(ema_50) and pd.notna(ema_200):
        if close > ema_200 and ema_50 > ema_200:
            trend = "Bullish"
        elif close < ema_200 and ema_50 < ema_200:
            trend = "Bearish"

    price_vs_ema200 = "-"

    if pd.notna(close) and pd.notna(ema_200):
        if close > ema_200:
            price_vs_ema200 = "Above EMA200"
        elif close < ema_200:
            price_vs_ema200 = "Below EMA200"
        else:
            price_vs_ema200 = "At EMA200"

    rsi_state = "-"

    if pd.notna(rsi):
        if rsi >= 70:
            rsi_state = "Overbought"
        elif rsi <= 30:
            rsi_state = "Oversold"
        else:
            rsi_state = "Neutral"

    macd_state = "-"

    if pd.notna(macd) and pd.notna(macd_signal):
        if macd > macd_signal:
            macd_state = "Bullish"
        elif macd < macd_signal:
            macd_state = "Bearish"
        else:
            macd_state = "Neutral"

    volume_state = "-"

    if pd.notna(volume_zscore):
        if volume_zscore >= 2.5:
            volume_state = "Volume Spike"
        elif volume_zscore >= 1:
            volume_state = "Above Average"
        else:
            volume_state = "Normal"

    volatility_state = "-"

    if "rolling_volatility_30d" in plot_df.columns:
        vol_series = plot_df["rolling_volatility_30d"].dropna()

        if not vol_series.empty and pd.notna(current_volatility):
            median_vol = vol_series.median()

            if median_vol > 0 and current_volatility > median_vol * 1.5:
                volatility_state = "Elevated"
            else:
                volatility_state = "Normal"

    suspicious_state = "Low"
    recent_suspicious_count = 0

    if "suspicious_event" in plot_df.columns:
        recent_df = plot_df.tail(30).copy()
        recent_suspicious_count = int(recent_df["suspicious_event"].sum())

        if recent_suspicious_count >= 8:
            suspicious_state = "High"
        elif recent_suspicious_count >= 3:
            suspicious_state = "Moderate"
        else:
            suspicious_state = "Low"

    return {
        "signal_date": signal_date,
        "trend": trend,
        "price_vs_ema200": price_vs_ema200,
        "rsi_state": rsi_state,
        "macd_state": macd_state,
        "volume_state": volume_state,
        "volatility_state": volatility_state,
        "suspicious_state": suspicious_state,
        "recent_suspicious_count": recent_suspicious_count,
    }


def build_current_technical_interpretation(summary: dict, asset_label: str = "The asset"):
    if not summary:
        return "No technical interpretation is available."

    trend = summary.get("trend", "-")
    price_vs_ema200 = summary.get("price_vs_ema200", "-")
    rsi_state = summary.get("rsi_state", "-")
    macd_state = summary.get("macd_state", "-")
    volume_state = summary.get("volume_state", "-")
    volatility_state = summary.get("volatility_state", "-")
    suspicious_state = summary.get("suspicious_state", "-")

    parts = []

    if trend == "Bullish":
        parts.append(f"{asset_label} is currently showing a bullish technical structure")
    elif trend == "Bearish":
        parts.append(f"{asset_label} is currently showing a bearish technical structure")
    else:
        parts.append(f"{asset_label} is currently in a neutral technical structure")

    if price_vs_ema200 == "Above EMA200":
        parts.append("trading above its EMA200")
    elif price_vs_ema200 == "Below EMA200":
        parts.append("trading below its EMA200")

    if macd_state == "Bullish":
        parts.append("with positive MACD momentum")
    elif macd_state == "Bearish":
        parts.append("with negative MACD momentum")

    if rsi_state == "Overbought":
        parts.append("while RSI is in overbought territory")
    elif rsi_state == "Oversold":
        parts.append("while RSI is in oversold territory")
    elif rsi_state == "Neutral":
        parts.append("while RSI remains neutral")

    if volume_state == "Volume Spike":
        parts.append("and current volume is unusually high")
    elif volume_state == "Above Average":
        parts.append("with volume above its recent average")

    if volatility_state == "Elevated":
        parts.append("Volatility is elevated compared with the selected period")
    elif volatility_state == "Normal":
        parts.append("Volatility remains within a normal range for the selected period")

    if suspicious_state == "High":
        parts.append("Recent suspicious activity is high and deserves closer review")
    elif suspicious_state == "Moderate":
        parts.append("Recent suspicious activity is moderate")
    elif suspicious_state == "Low":
        parts.append("Recent suspicious activity is low")

    return ". ".join(parts) + "."
