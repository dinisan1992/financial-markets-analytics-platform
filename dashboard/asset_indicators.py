import numpy as np
import pandas as pd

from indicators import calcular_indicadores


def prepare_asset_technical_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares technical data for the Asset Explorer.

    Requires at least:
    - snapped_at
    - price

    Optional:
    - total_volume

    Returns a DataFrame with:
    - Synthetic OHLC
    - EMAs
    - Bollinger Bands
    - RSI
    - Stoch RSI
    - MACD
    - Volatility
    - Drawdown
    - Volume z-score
    - Suspicious event flags
    """

    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    if "price" not in df.columns:
        raise ValueError("Required column missing: price")

    if "snapped_at" not in df.columns:
        raise ValueError("Required column missing: snapped_at")

    volume_candidates = [
        "total_volume",
        "volume",
        "Volume",
        "vol",
        "trading_volume"
    ]

    volume_source_col = None

    for candidate in volume_candidates:
        if candidate in df.columns:
            candidate_values = pd.to_numeric(df[candidate], errors="coerce")

            if candidate_values.notna().sum() > 0:
                volume_source_col = candidate
                break

    if volume_source_col is None:
        df["total_volume"] = np.nan
    else:
        df["total_volume"] = pd.to_numeric(
            df[volume_source_col],
            errors="coerce"
        )

    df["snapped_at"] = pd.to_datetime(df["snapped_at"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["total_volume"] = pd.to_numeric(df["total_volume"], errors="coerce")

    df = df.dropna(subset=["snapped_at", "price"]).copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    # =========================
    # PRICE / OHLC
    # =========================

    df["close"] = df["price"]

    # Synthetic OHLC for assets that only have a daily price
    df["open"] = df["close"].shift(1)
    df["open"] = df["open"].fillna(df["close"])

    df["high"] = df[["open", "close"]].max(axis=1) * 1.01
    df["low"] = df[["open", "close"]].min(axis=1) * 0.99

    df["daily_return"] = df["close"].pct_change(fill_method=None)
    df["daily_return_pct"] = df["daily_return"] * 100
    df["price_change_pct"] = df["close"].pct_change(fill_method=None) * 100

    # =========================
    # EMAs
    # =========================

    for window in [9, 20, 50, 100, 200]:
        df[f"ema_{window}"] = df["close"].ewm(
            span=window,
            adjust=False
        ).mean()

    # =========================
    # BOLLINGER BANDS
    # =========================

    df["bb_middle"] = df["close"].rolling(20).mean()
    df["bb_std"] = df["close"].rolling(20).std()
    df["bb_upper"] = df["bb_middle"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_middle"] - 2 * df["bb_std"]

    # =========================
    # RSI
    # =========================

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    df["rsi"] = df["rsi"].replace([np.inf, -np.inf], np.nan)

    # =========================
    # STOCHASTIC RSI
    # =========================

    rsi_min = df["rsi"].rolling(14).min()
    rsi_max = df["rsi"].rolling(14).max()

    df["stoch_rsi"] = (df["rsi"] - rsi_min) / (rsi_max - rsi_min) * 100
    df["stoch_rsi"] = df["stoch_rsi"].replace([np.inf, -np.inf], np.nan)

    df["stoch_rsi_k"] = df["stoch_rsi"].rolling(3).mean()
    df["stoch_rsi_d"] = df["stoch_rsi_k"].rolling(3).mean()

    # =========================
    # MACD
    # =========================

    ema_12 = df["close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["close"].ewm(span=26, adjust=False).mean()

    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # =========================
    # VOLATILITY / DRAWDOWN
    # =========================

    df["rolling_volatility_30d"] = (
        df["daily_return"].rolling(30).std() * np.sqrt(252) * 100
    )

    df["rolling_max"] = df["close"].cummax()
    df["drawdown_pct"] = ((df["close"] / df["rolling_max"]) - 1) * 100

    # =========================
    # VOLUME
    # =========================

    df["volume_sma_30"] = df["total_volume"].rolling(30).mean()
    df["volume_std_30"] = df["total_volume"].rolling(30).std()

    df["volume_zscore"] = (
        (df["total_volume"] - df["volume_sma_30"]) / df["volume_std_30"]
    )

    df["volume_zscore"] = df["volume_zscore"].replace([np.inf, -np.inf], np.nan)

    # Recalcula os indicadores pelo motor central para manter o dashboard
    # consistente com os scripts principais.
    df["volume"] = df["total_volume"]
    df["daily_return"] = df["close"].pct_change(fill_method=None)
    df["daily_return_pct"] = df["daily_return"] * 100

    df = calcular_indicadores(df)

    if "ema_20" not in df.columns:
        df["ema_20"] = df["close"].ewm(
            span=20,
            adjust=False
        ).mean()

    df["macd_hist"] = df["macd"] - df["macd_signal"]

    rsi_min = df["rsi"].rolling(14, min_periods=1).min()
    rsi_max = df["rsi"].rolling(14, min_periods=1).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)

    df["stoch_rsi"] = ((df["rsi"] - rsi_min) / rsi_range) * 100
    df["stoch_rsi"] = df["stoch_rsi"].replace([np.inf, -np.inf], np.nan)

    df["rolling_volatility_30d"] = df["realized_volatility_30d"]
    df["rolling_max"] = df["close"].cummax()
    df["drawdown_pct"] = ((df["close"] / df["rolling_max"]) - 1) * 100
    df["volume_sma_20"] = df["volume"].rolling(20).mean()

    # =========================
    # CANDLE BEHAVIOUR
    # =========================

    df["candle_range"] = df["high"] - df["low"]
    df["candle_body"] = (df["close"] - df["open"]).abs()

    df["body_to_range"] = df["candle_body"] / df["candle_range"]
    df["body_to_range"] = df["body_to_range"].replace([np.inf, -np.inf], np.nan)

    # =========================
    # FLAGS
    # =========================

    df["volume_spike"] = df["volume_zscore"] > 2.5

    df["possible_pump_dump"] = (
        (df["volume_zscore"] > 2.5)
        & (df["price_change_pct"].abs() > 5)
        & (df["body_to_range"] > 0.5)
    )

    df["possible_spoofing"] = (
        (df["volume_zscore"] > 2.5)
        & (df["price_change_pct"].abs() < 0.5)
        & (df["body_to_range"] < 0.3)
    )

    df["extreme_rsi"] = (
        (df["rsi"] > 80)
        | (df["rsi"] < 20)
    )

    df["risk_signal"] = (
        df["possible_pump_dump"]
        | df["possible_spoofing"]
    )

    df["suspicious_event"] = df["risk_signal"]

    # =========================
    # HUMAN-READABLE REASONS
    # =========================

    df["manipulation_reason"] = ""

    df.loc[df["possible_pump_dump"], "manipulation_reason"] += "Possible pump/dump; "
    df.loc[df["possible_spoofing"], "manipulation_reason"] += "Possible spoofing; "
    df.loc[df["volume_spike"], "manipulation_reason"] += "Volume spike; "
    df.loc[df["rsi"] > 80, "manipulation_reason"] += "RSI very high; "
    df.loc[df["rsi"] < 20, "manipulation_reason"] += "RSI very low; "

    df["manipulation_reason"] = df["manipulation_reason"].str.strip()

    return df


def get_suspicious_events(df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns only suspicious events, sorted from newest to oldest.
    """

    if "suspicious_event" not in df.columns:
        return pd.DataFrame()

    suspicious_df = df[df["suspicious_event"]].copy()

    if suspicious_df.empty:
        return suspicious_df

    columns = [
        "snapped_at",
        "close",
        "price_change_pct",
        "total_volume",
        "volume_zscore",
        "rsi",
        "possible_pump_dump",
        "possible_spoofing",
        "volume_spike",
        "extreme_rsi",
        "manipulation_reason"
    ]

    existing_columns = [col for col in columns if col in suspicious_df.columns]

    suspicious_df = suspicious_df[existing_columns].copy()
    suspicious_df = suspicious_df.sort_values("snapped_at", ascending=False)

    return suspicious_df


def calculate_asset_kpis(df: pd.DataFrame) -> dict:
    """
    Calcula KPIs principais para mostrar no topo do Asset Explorer.
    """

    close_series = df["close"].dropna() if "close" in df.columns else pd.Series(dtype=float)

    if close_series.empty:
        return {
            "latest_price": None,
            "total_return": None,
            "latest_rsi": None,
            "latest_macd": None,
            "latest_volatility": None,
            "latest_drawdown": None,
            "suspicious_count": 0,
            "pump_dump_count": 0,
            "spoofing_count": 0,
            "volume_spike_count": 0,
        }

    latest_price = close_series.iloc[-1]
    first_price = close_series.iloc[0]

    total_return = ((latest_price / first_price) - 1) * 100 if first_price != 0 else None

    latest_rsi = (
        df["rsi"].dropna().iloc[-1]
        if "rsi" in df.columns and not df["rsi"].dropna().empty
        else None
    )

    latest_macd = (
        df["macd"].dropna().iloc[-1]
        if "macd" in df.columns and not df["macd"].dropna().empty
        else None
    )

    latest_volatility = (
        df["rolling_volatility_30d"].dropna().iloc[-1]
        if "rolling_volatility_30d" in df.columns and not df["rolling_volatility_30d"].dropna().empty
        else None
    )

    latest_drawdown = (
        df["drawdown_pct"].dropna().iloc[-1]
        if "drawdown_pct" in df.columns and not df["drawdown_pct"].dropna().empty
        else None
    )

    suspicious_count = int(df["suspicious_event"].sum()) if "suspicious_event" in df.columns else 0
    pump_dump_count = int(df["possible_pump_dump"].sum()) if "possible_pump_dump" in df.columns else 0
    spoofing_count = int(df["possible_spoofing"].sum()) if "possible_spoofing" in df.columns else 0
    volume_spike_count = int(df["volume_spike"].sum()) if "volume_spike" in df.columns else 0

    return {
        "latest_price": latest_price,
        "total_return": total_return,
        "latest_rsi": latest_rsi,
        "latest_macd": latest_macd,
        "latest_volatility": latest_volatility,
        "latest_drawdown": latest_drawdown,
        "suspicious_count": suspicious_count,
        "pump_dump_count": pump_dump_count,
        "spoofing_count": spoofing_count,
        "volume_spike_count": volume_spike_count,
    }
