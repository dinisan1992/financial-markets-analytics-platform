import pandas as pd
import numpy as np


# =========================
# RSI
# =========================
def calcular_rsi(precos, window=14):
    precos = pd.to_numeric(precos, errors="coerce")

    delta = precos.diff()

    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.ewm(
        alpha=1 / window,
        min_periods=window,
        adjust=False
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / window,
        min_periods=window,
        adjust=False
    ).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    no_loss = avg_loss == 0
    no_gain = avg_gain == 0

    rsi = rsi.mask(no_loss & ~no_gain, 100)
    rsi = rsi.mask(no_gain & ~no_loss, 0)
    rsi = rsi.mask(no_gain & no_loss, 50)

    return rsi


# =========================
# STOCH RSI
# =========================
def calcular_stochrsi(precos, rsi_window=14, stoch_window=14, k_smooth=3, d_smooth=3):
    rsi = calcular_rsi(precos, window=rsi_window)

    min_rsi = rsi.rolling(stoch_window, min_periods=1).min()
    max_rsi = rsi.rolling(stoch_window, min_periods=1).max()

    denominator = (max_rsi - min_rsi).replace(0, np.nan)

    stoch_rsi = ((rsi - min_rsi) / denominator) * 100

    stoch_rsi_k = stoch_rsi.rolling(k_smooth, min_periods=1).mean()
    stoch_rsi_d = stoch_rsi_k.rolling(d_smooth, min_periods=1).mean()

    return stoch_rsi_k, stoch_rsi_d


# =========================
# ATR
# =========================
def calcular_wilder_smoothing(values, window=14):
    """Apply Wilder's recursive moving average with an initial simple mean."""
    values = pd.to_numeric(values, errors="coerce")
    output = pd.Series(np.nan, index=values.index, dtype="float64")
    valid = values.dropna()

    if len(valid) < window:
        return output

    seed_index = valid.index[window - 1]
    previous = valid.iloc[:window].mean()
    output.loc[seed_index] = previous

    for index, current in valid.iloc[window:].items():
        previous = previous + (current - previous) / window
        output.loc[index] = previous

    return output


def calcular_atr(high, low, close, window=14):
    """Calculate Average True Range using Wilder smoothing."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    return calcular_wilder_smoothing(tr, window=window)


# =========================
# ADX
# =========================
def calcular_adx(high, low, close, window=14):
    """Calculate Average Directional Index using Wilder smoothing."""
    high_diff = high.diff()
    low_diff = low.diff()

    plus_dm = high_diff.where(
        (high_diff > -low_diff) & (high_diff > 0),
        0
    )

    minus_dm = (-low_diff).where(
        (-low_diff > high_diff) & (-low_diff > 0),
        0
    )

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    tr = pd.concat(
        [tr1, tr2, tr3],
        axis=1
    ).max(axis=1)

    atr = calcular_wilder_smoothing(tr, window=window)
    plus_dm_smoothed = calcular_wilder_smoothing(plus_dm, window=window)
    minus_dm_smoothed = calcular_wilder_smoothing(minus_dm, window=window)

    plus_di = 100 * (
        plus_dm_smoothed
        /
        atr.replace(0, np.nan)
    )

    minus_di = 100 * (
        minus_dm_smoothed
        /
        atr.replace(0, np.nan)
    )

    dx = 100 * (
        (plus_di - minus_di).abs()
        /
        (plus_di + minus_di).replace(0, np.nan)
    )

    return calcular_wilder_smoothing(dx, window=window)


# =========================
# CCI
# =========================
def calcular_cci(high, low, close, window=20):
    tp = (high + low + close) / 3

    ma = tp.rolling(window=window).mean()

    md = tp.rolling(window=window).apply(
        lambda x: np.fabs(x - x.mean()).mean(),
        raw=True
    )

    cci = (tp - ma) / ((0.015 * md) + 1e-9)

    return cci


# =========================
# OBV
# =========================
def calcular_obv(close, volume):
    if close.empty or volume.empty:
        return pd.Series(dtype="float64", index=close.index)

    direction = np.sign(close.diff())
    direction.iloc[0] = 0

    obv = (direction * volume).cumsum()

    return obv


# =========================
# ENTROPIA DE MERCADO
# =========================
def calcular_market_entropy(close, window=30, bins=10):
    close = pd.to_numeric(close, errors="coerce")
    returns = close.pct_change(fill_method=None)
    returns = returns.replace([np.inf, -np.inf], np.nan)

    entropy_values = []

    for i in range(len(close)):
        if i < window:
            entropy_values.append(np.nan)
            continue

        subset = returns.iloc[i - window:i].dropna()

        if subset.empty:
            entropy_values.append(np.nan)
            continue

        if not np.isfinite(subset).all():
            subset = subset[np.isfinite(subset)]

        if subset.empty:
            entropy_values.append(np.nan)
            continue

        hist, _ = np.histogram(
            subset,
            bins=bins,
            density=True
        )

        hist = hist + 1e-9

        probabilities = hist / hist.sum()

        entropy_value = -np.sum(
            probabilities * np.log(probabilities)
        )

        entropy_values.append(entropy_value)

    return pd.Series(
        entropy_values,
        index=close.index
    )


# =========================
# DRAWDOWN DURATION
# =========================
def calcular_drawdown_duration(close):
    rolling_max = close.cummax()

    drawdown = (close - rolling_max) / (rolling_max + 1e-9)

    durations = []
    duration = 0

    for value in drawdown:
        if value < 0:
            duration += 1
        else:
            duration = 0

        durations.append(duration)

    return pd.Series(
        durations,
        index=close.index
    )


# =========================
# CALCULAR TODOS OS INDICADORES
# =========================
def calcular_indicadores(df, periods_per_year=252):
    """Calculate the canonical in-memory technical indicator set."""

    df = df.copy()

    try:
        periods_per_year = int(periods_per_year)
    except (TypeError, ValueError) as exc:
        raise ValueError("periods_per_year must be a positive integer") from exc

    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be a positive integer")

    required_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume"
    ]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Required column missing for indicators: {col}")

    # =========================
    # RSI
    # =========================
    df["rsi"] = calcular_rsi(df["close"])

    # =========================
    # STOCH RSI
    # =========================
    df["stoch_rsi_k"], df["stoch_rsi_d"] = calcular_stochrsi(
        df["close"],
        rsi_window=14,
        stoch_window=14,
        k_smooth=3,
        d_smooth=3
    )

    # =========================
    # EMAS
    # =========================
    for span in [9, 12, 26, 50, 100, 200]:
        df[f"ema_{span}"] = df["close"].ewm(
            span=span,
            adjust=False
        ).mean()

    # =========================
    # VOLUME SMA
    # =========================
    df["volume_sma_9"] = df["volume"].rolling(window=9).mean()

    # =========================
    # BOLLINGER BANDS
    # =========================
    window_bb = 20
    k = 2

    df["bb_middle"] = df["close"].rolling(window=window_bb).mean()
    df["bb_std"] = df["close"].rolling(window=window_bb).std()

    df["bb_upper"] = df["bb_middle"] + (k * df["bb_std"])
    df["bb_lower"] = df["bb_middle"] - (k * df["bb_std"])

    # =========================
    # MACD
    # =========================
    ema_12 = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema_26 = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    df["macd"] = ema_12 - ema_26

    df["macd_signal"] = df["macd"].ewm(
        span=9,
        adjust=False
    ).mean()

    df["macd_percent"] = 100 * (
        df["macd"]
        /
        (df["close"] + 1e-9)
    )

    # =========================
    # MOMENTUM
    # =========================
    df["momentum_10"] = df["close"] - df["close"].shift(10)

    # =========================
    # ATR
    # =========================
    df["atr"] = calcular_atr(
        df["high"],
        df["low"],
        df["close"]
    )

    # =========================
    # ADX
    # =========================
    df["adx"] = calcular_adx(
        df["high"],
        df["low"],
        df["close"]
    )

    # =========================
    # CCI
    # =========================
    df["cci"] = calcular_cci(
        df["high"],
        df["low"],
        df["close"]
    )

    # =========================
    # OBV
    # =========================
    df["obv"] = calcular_obv(
        df["close"],
        df["volume"]
    )

    # =========================
    # PRICE CHANGE
    # =========================
    observation_returns = (
        df["close"]
        .pct_change(fill_method=None)
        .replace([np.inf, -np.inf], np.nan)
    )
    df["price_change_pct"] = observation_returns * 100

    # =====================================================
    # NEW ADVANCED INDICATORS
    # DataFrame only. They are NOT sent to SQL yet.
    # =====================================================

    # =========================
    # VOLUME Z-SCORE
    # =========================
    volume_mean_20 = df["volume"].rolling(20).mean()
    volume_std_20 = df["volume"].rolling(20).std()

    df["volume_zscore"] = (
        (df["volume"] - volume_mean_20)
        /
        (volume_std_20 + 1e-9)
    )

    # =========================
    # REALIZED VOLATILITY 30D
    # =========================
    df["realized_volatility_30d"] = (
        observation_returns
        .rolling(30)
        .std()
        * np.sqrt(periods_per_year)
        * 100
    )

    df["volatility_periods_per_year"] = periods_per_year

    # =========================
    # VOLATILITY OF VOLATILITY
    # =========================
    df["volatility_of_volatility"] = (
        df["realized_volatility_30d"]
        .rolling(30)
        .std()
    )

    # =========================
    # LIQUIDITY STRESS
    # =========================
    df["liquidity_stress"] = (
        df["realized_volatility_30d"]
        /
        (df["volume"].rolling(30).mean() + 1e-9)
    )

    # =========================
    # DRAWDOWN DURATION
    # =========================
    df["drawdown_duration"] = calcular_drawdown_duration(
        df["close"]
    )

    # =========================
    # MARKET ENTROPY
    # =========================
    df["market_entropy"] = calcular_market_entropy(
        df["close"],
        window=30,
        bins=10
    )

    return df
