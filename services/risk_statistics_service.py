import numpy as np
import pandas as pd


def filter_df_by_recent_window(df: pd.DataFrame, window_label: str):
    if df is None or df.empty or "snapped_at" not in df.columns:
        return df

    if window_label == "Full Period":
        return df.copy()

    days_map = {
        "Last 7D": 7,
        "Last 30D": 30,
        "Last 90D": 90,
    }

    days = days_map.get(window_label)

    if days is None:
        return df.copy()

    plot_df = df.copy()
    plot_df["snapped_at"] = pd.to_datetime(plot_df["snapped_at"], errors="coerce")
    plot_df = plot_df.dropna(subset=["snapped_at"]).copy()

    if plot_df.empty:
        return plot_df

    max_date = plot_df["snapped_at"].max()
    min_date = max_date - pd.Timedelta(days=days)

    return plot_df[plot_df["snapped_at"] >= min_date].copy()


def _empty_suspicion_score():
    return {
        "score": 0,
        "risk_level": "Low",
        "suspicious_events": 0,
        "volume_spikes": 0,
        "pump_dump": 0,
        "spoofing": 0,
        "extreme_rsi": 0,
        "days_count": 0,
        "suspicious_rate": 0,
    }


def calculate_suspicion_score(df: pd.DataFrame):
    if df is None or df.empty:
        return _empty_suspicion_score()

    risk_df = df.copy()

    days_count = len(risk_df)

    if days_count == 0:
        return _empty_suspicion_score()

    suspicious_events = int(risk_df["suspicious_event"].sum()) if "suspicious_event" in risk_df.columns else 0
    volume_spikes = int(risk_df["volume_spike"].sum()) if "volume_spike" in risk_df.columns else 0
    pump_dump = int(risk_df["possible_pump_dump"].sum()) if "possible_pump_dump" in risk_df.columns else 0
    spoofing = int(risk_df["possible_spoofing"].sum()) if "possible_spoofing" in risk_df.columns else 0
    extreme_rsi = int(risk_df["extreme_rsi"].sum()) if "extreme_rsi" in risk_df.columns else 0

    suspicious_rate = suspicious_events / days_count
    volume_spike_rate = volume_spikes / days_count
    pump_dump_rate = pump_dump / days_count
    spoofing_rate = spoofing / days_count
    extreme_rsi_rate = extreme_rsi / days_count

    score = 0

    score += min(suspicious_rate * 100 * 2.0, 30)
    score += min(volume_spike_rate * 100 * 1.5, 20)
    score += min(pump_dump_rate * 100 * 4.0, 20)
    score += min(spoofing_rate * 100 * 4.0, 20)
    score += min(extreme_rsi_rate * 100 * 1.0, 10)

    if days_count <= 30 and suspicious_events >= 5:
        score += 10

    if pump_dump >= 1:
        score += 5

    if spoofing >= 1:
        score += 5

    score = round(min(score, 100), 1)

    if score >= 75:
        risk_level = "Extreme"
    elif score >= 50:
        risk_level = "High"
    elif score >= 25:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    return {
        "score": score,
        "risk_level": risk_level,
        "suspicious_events": suspicious_events,
        "volume_spikes": volume_spikes,
        "pump_dump": pump_dump,
        "spoofing": spoofing,
        "extreme_rsi": extreme_rsi,
        "days_count": days_count,
        "suspicious_rate": suspicious_rate,
    }


def get_return_column(df: pd.DataFrame):
    for col in ["daily_return_pct", "price_change_pct", "return_1d", "return_1d_pct"]:
        if col in df.columns:
            return col
    return None


def calculate_return_distribution_summary(df: pd.DataFrame):
    if df is None or df.empty:
        return {}

    return_col = get_return_column(df)

    if return_col is None:
        return {}

    returns = pd.to_numeric(df[return_col], errors="coerce").dropna()

    if returns.empty:
        return {}

    positive_days = (returns > 0).sum()
    negative_days = (returns < 0).sum()
    total_days = len(returns)

    return {
        "return_col": return_col,
        "average_return": returns.mean(),
        "median_return": returns.median(),
        "best_day": returns.max(),
        "worst_day": returns.min(),
        "positive_days_pct": (positive_days / total_days) * 100 if total_days else np.nan,
        "negative_days_pct": (negative_days / total_days) * 100 if total_days else np.nan,
        "observations": total_days,
    }
