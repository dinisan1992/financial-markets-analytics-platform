import numpy as np
import pandas as pd

from indicators import calcular_indicadores


OHLC_COLUMNS = ["open", "high", "low", "close"]
VOLUME_CANDIDATES = [
    "total_volume",
    "volume",
    "Volume",
    "vol",
    "trading_volume",
]


def _native_ohlc_mask(
    df: pd.DataFrame,
    positive_values_expected: bool = True,
) -> pd.Series:
    """Return rows containing internally consistent, positive native OHLC."""
    if any(column not in df.columns for column in OHLC_COLUMNS):
        return pd.Series(False, index=df.index, dtype=bool)

    ohlc = df[OHLC_COLUMNS].apply(pd.to_numeric, errors="coerce")
    finite = pd.Series(
        np.isfinite(ohlc.to_numpy(dtype=float)).all(axis=1),
        index=df.index,
    )

    valid = (
        finite
        & (ohlc["high"] >= ohlc[["open", "close"]].max(axis=1))
        & (ohlc["low"] <= ohlc[["open", "close"]].min(axis=1))
        & (ohlc["high"] >= ohlc["low"])
    )
    if positive_values_expected:
        valid &= (ohlc > 0).all(axis=1)
    return valid


def _prepare_ohlc(
    df: pd.DataFrame,
    positive_values_expected: bool = True,
) -> pd.DataFrame:
    """Preserve valid native candles and synthesize only incomplete rows."""
    output = df.copy()

    for column in OHLC_COLUMNS:
        if column in output.columns:
            output[column] = pd.to_numeric(output[column], errors="coerce")

    native_mask = _native_ohlc_mask(
        output,
        positive_values_expected=positive_values_expected,
    )

    if "price" in output.columns:
        synthetic_close = pd.to_numeric(output["price"], errors="coerce")
    elif "close" in output.columns:
        synthetic_close = pd.to_numeric(output["close"], errors="coerce")
    else:
        raise ValueError("Required price field missing: expected price or close")

    if "close" in output.columns:
        synthetic_close = synthetic_close.fillna(output["close"])

    synthetic_open = synthetic_close.shift(1).fillna(synthetic_close)
    synthetic_upper = pd.concat([synthetic_open, synthetic_close], axis=1).max(axis=1)
    synthetic_lower = pd.concat([synthetic_open, synthetic_close], axis=1).min(axis=1)
    synthetic_padding = (
        pd.concat([synthetic_open.abs(), synthetic_close.abs()], axis=1)
        .max(axis=1)
        .clip(lower=1e-9)
        * 0.01
    )
    synthetic_high = synthetic_upper + synthetic_padding
    synthetic_low = synthetic_lower - synthetic_padding

    synthetic_values = {
        "open": synthetic_open,
        "high": synthetic_high,
        "low": synthetic_low,
        "close": synthetic_close,
    }

    for column in OHLC_COLUMNS:
        native_values = output[column] if column in output.columns else np.nan
        output[column] = pd.Series(native_values, index=output.index).where(
            native_mask,
            synthetic_values[column],
        )

    output["ohlc_source"] = np.where(native_mask, "native", "synthetic")
    output["native_ohlc_valid"] = native_mask

    return output


def _prepare_volume(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()
    volume_source = None

    for candidate in VOLUME_CANDIDATES:
        if candidate not in output.columns:
            continue

        values = pd.to_numeric(output[candidate], errors="coerce")
        if values.notna().any():
            volume_source = candidate
            break

    if volume_source is None:
        output["total_volume"] = np.nan
    else:
        output["total_volume"] = pd.to_numeric(
            output[volume_source],
            errors="coerce",
        )

    output["volume"] = output["total_volume"]
    output["volume_source"] = volume_source or "unavailable"

    return output


def prepare_asset_technical_data(
    df: pd.DataFrame,
    asset_cfg: dict | None = None,
) -> pd.DataFrame:
    """Build the canonical technical dataset used by the Asset Explorer.

    Native OHLC is retained row by row when it is complete and internally
    consistent. Synthetic candles are used only for rows without valid OHLC.
    Candle-shape anomaly signals are disabled for synthetic rows.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    asset_cfg = asset_cfg or {}
    periods_per_year = int(asset_cfg.get("periods_per_year", 252))
    positive_values_expected = bool(asset_cfg.get("positive_values_expected", True))

    output = df.copy()

    if "snapped_at" not in output.columns:
        raise ValueError("Required column missing: snapped_at")

    output["snapped_at"] = pd.to_datetime(output["snapped_at"], errors="coerce")

    if "price" in output.columns:
        output["price"] = pd.to_numeric(output["price"], errors="coerce")

    output = output.dropna(subset=["snapped_at"]).copy()
    output = output.sort_values("snapped_at").reset_index(drop=True)
    output = _prepare_volume(output)
    output = _prepare_ohlc(
        output,
        positive_values_expected=positive_values_expected,
    )
    output["close"] = pd.to_numeric(output["close"], errors="coerce").replace(
        [np.inf, -np.inf],
        np.nan,
    )
    output = output.dropna(subset=["close"])
    if positive_values_expected:
        output = output[output["close"] > 0]
    output = output.reset_index(drop=True)

    output = calcular_indicadores(
        output,
        periods_per_year=periods_per_year,
    )

    output["daily_return"] = output["price_change_pct"] / 100
    output["daily_return_pct"] = output["price_change_pct"]
    output["macd_hist"] = output["macd"] - output["macd_signal"]
    output["stoch_rsi"] = output["stoch_rsi_k"]
    output["rolling_volatility_30d"] = output["realized_volatility_30d"]
    output["rolling_max"] = output["close"].cummax()
    output["drawdown_pct"] = ((output["close"] / output["rolling_max"]) - 1) * 100
    output["volume_sma_20"] = output["volume"].rolling(20).mean()

    output["candle_range"] = output["high"] - output["low"]
    output["candle_body"] = (output["close"] - output["open"]).abs()
    output["body_to_range"] = (
        output["candle_body"]
        / output["candle_range"].replace(0, np.nan)
    )

    volume_available = output["volume"].notna() & (output["volume"] > 0)
    native_candle = output["ohlc_source"].eq("native")
    output["candle_signal_eligible"] = native_candle & volume_available

    output["volume_spike"] = volume_available & (output["volume_zscore"] > 2.5)
    output["possible_pump_dump"] = (
        output["candle_signal_eligible"]
        & output["volume_spike"]
        & (output["price_change_pct"].abs() > 5)
        & (output["body_to_range"] > 0.5)
    )
    output["possible_spoofing"] = (
        output["candle_signal_eligible"]
        & output["volume_spike"]
        & (output["price_change_pct"].abs() < 0.5)
        & (output["body_to_range"] < 0.3)
    )
    output["extreme_rsi"] = (output["rsi"] > 80) | (output["rsi"] < 20)
    output["risk_signal"] = output["possible_pump_dump"] | output["possible_spoofing"]
    output["suspicious_event"] = output["risk_signal"] | output["volume_spike"]
    output["signal_confidence"] = np.where(
        output["candle_signal_eligible"],
        "standard",
        "limited",
    )

    output["manipulation_reason"] = ""
    output.loc[output["possible_pump_dump"], "manipulation_reason"] += "Possible pump/dump; "
    output.loc[output["possible_spoofing"], "manipulation_reason"] += "Possible spoofing; "
    output.loc[output["volume_spike"], "manipulation_reason"] += "Volume spike; "
    output.loc[output["rsi"] > 80, "manipulation_reason"] += "RSI very high; "
    output.loc[output["rsi"] < 20, "manipulation_reason"] += "RSI very low; "
    output["manipulation_reason"] = output["manipulation_reason"].str.strip()

    output["asset_class"] = asset_cfg.get("asset_class", "unknown")
    output["calendar_type"] = asset_cfg.get("calendar_type", "unknown")

    return output


def get_suspicious_events(df: pd.DataFrame) -> pd.DataFrame:
    """Return suspicious observations, sorted from newest to oldest."""
    if "suspicious_event" not in df.columns:
        return pd.DataFrame()

    suspicious_df = df[df["suspicious_event"]].copy()

    columns = [
        "snapped_at",
        "close",
        "price_change_pct",
        "total_volume",
        "volume_zscore",
        "rsi",
        "ohlc_source",
        "signal_confidence",
        "possible_pump_dump",
        "possible_spoofing",
        "volume_spike",
        "extreme_rsi",
        "manipulation_reason",
    ]
    existing_columns = [column for column in columns if column in suspicious_df.columns]

    return suspicious_df[existing_columns].sort_values(
        "snapped_at",
        ascending=False,
    )


def calculate_asset_kpis(df: pd.DataFrame) -> dict:
    """Calculate the headline Asset Explorer metrics."""
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
            "native_ohlc_pct": 0,
            "periods_per_year": None,
        }

    latest_price = close_series.iloc[-1]
    first_price = close_series.iloc[0]

    def latest_value(column):
        if column not in df.columns:
            return None
        values = df[column].dropna()
        return values.iloc[-1] if not values.empty else None

    native_ohlc_pct = (
        df["ohlc_source"].eq("native").mean() * 100
        if "ohlc_source" in df.columns and len(df)
        else 0
    )

    return {
        "latest_price": latest_price,
        "total_return": ((latest_price / first_price) - 1) * 100 if first_price != 0 else None,
        "latest_rsi": latest_value("rsi"),
        "latest_macd": latest_value("macd"),
        "latest_volatility": latest_value("rolling_volatility_30d"),
        "latest_drawdown": latest_value("drawdown_pct"),
        "suspicious_count": int(df["suspicious_event"].sum()) if "suspicious_event" in df.columns else 0,
        "pump_dump_count": int(df["possible_pump_dump"].sum()) if "possible_pump_dump" in df.columns else 0,
        "spoofing_count": int(df["possible_spoofing"].sum()) if "possible_spoofing" in df.columns else 0,
        "volume_spike_count": int(df["volume_spike"].sum()) if "volume_spike" in df.columns else 0,
        "native_ohlc_pct": native_ohlc_pct,
        "periods_per_year": latest_value("volatility_periods_per_year"),
    }
