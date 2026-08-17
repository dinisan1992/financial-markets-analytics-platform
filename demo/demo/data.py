from __future__ import annotations

from datetime import date
import hashlib

import numpy as np
import pandas as pd


DEMO_START_DATE = "2000-01-01"
DEMO_END_DATE = str(date.today())

_ASSET_START_DATES = {
    "BTC": "2010-07-18",
}

_YIELD_TIGHTENING_SHIFTS = {
    "US3M": 4.8,
    "US2Y": 4.0,
    "US10Y": 2.2,
    "US30Y": 1.6,
    "GERMANY10Y": 2.4,
    "UK10Y": 2.2,
    "JAPAN10Y": 0.7,
}

_MACRO_PROFILES = {
    "FED_FUNDS_RATE": {
        "frequency": "ME", "kind": "policy_rate", "start": 5.5, "noise": 0.030,
    },
    "FED_M2": {
        "frequency": "ME", "kind": "level", "start": 4_700.0, "growth": 0.060,
    },
    "FED_TOTAL_ASSETS": {
        "frequency": "ME", "kind": "level", "start": 600.0, "growth": 0.082,
    },
    "FED_RESERVE_BANK_CREDIT": {
        "frequency": "ME", "kind": "level", "start": 560.0, "growth": 0.083,
    },
    "FED_DEPOSITS": {
        "frequency": "ME", "kind": "level", "start": 3_500.0, "growth": 0.064,
    },
    "FED_BANK_CREDIT": {
        "frequency": "ME", "kind": "level", "start": 4_900.0, "growth": 0.055,
    },
    "FED_LOANS_LEASES": {
        "frequency": "ME", "kind": "level", "start": 3_400.0, "growth": 0.056,
    },
    "FED_SECURITIES_BANK_CREDIT": {
        "frequency": "ME", "kind": "level", "start": 1_100.0, "growth": 0.052,
    },
    "FED_CONSUMER_LOANS_CREDIT_CARDS": {
        "frequency": "ME", "kind": "level", "start": 680.0, "growth": 0.044,
    },
    "FED_CREDIT_CARD_DELINQUENCY": {
        "frequency": "QE", "kind": "stress_rate", "start": 4.7,
    },
    "FED_CHARGE_OFF_RATE_CREDIT_CARDS": {
        "frequency": "QE", "kind": "stress_rate", "start": 6.0,
    },
}

EVENT_COLUMNS = [
    "event_date",
    "date_precision",
    "event_title",
    "event_category",
    "event_description",
    "event_source_table",
]

_DEMO_EVENTS = [
    ("2016-07-09", "exact", "Second Bitcoin halving", "Bitcoin Halving",
     "Synthetic demo context anchored to the real Bitcoin halving date.",
     "bitcoin_historical_events"),
    ("2018-12-24", "exact", "2018 equity selloff", "Markets",
     "Synthetic demo event used to exercise cross-asset event analysis.",
     "world_historical_events"),
    ("2020-03-11", "exact", "COVID-19 pandemic shock", "Macro / Geopolitical",
     "Synthetic demo context anchored to a major global market-stress date.",
     "world_historical_events"),
    ("2020-03-23", "exact", "Emergency monetary support", "Monetary Policy",
     "Synthetic demo event used to demonstrate recovery analysis.",
     "world_historical_events"),
    ("2020-05-11", "exact", "Third Bitcoin halving", "Bitcoin Halving",
     "Synthetic demo context anchored to the real Bitcoin halving date.",
     "bitcoin_historical_events"),
    ("2022-02-24", "exact", "Russia invasion of Ukraine", "Geopolitical",
     "Synthetic demo event used to exercise commodity and risk-off analytics.",
     "world_historical_events"),
    ("2022-03-16", "exact", "Federal Reserve tightening cycle", "Monetary Policy",
     "Synthetic demo event used to demonstrate rate-sensitive market analysis.",
     "world_historical_events"),
    ("2023-03-10", "exact", "US regional banking stress", "Financial Stress",
     "Synthetic demo event used to demonstrate stress and recovery analytics.",
     "world_historical_events"),
    ("2024-04-20", "exact", "Fourth Bitcoin halving", "Bitcoin Halving",
     "Synthetic demo context anchored to the real Bitcoin halving date.",
     "bitcoin_historical_events"),
    ("2024-01-01", "year", "2024 global election cycle", "World / Geopolitical",
     "Year-only demo event used to demonstrate approximate-date exclusion.",
     "world_historical_events"),
]


def _stable_seed(text: str) -> int:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % (2**32 - 1)


def _coerce_date(value, fallback: str) -> pd.Timestamp:
    timestamp = pd.to_datetime(value if value is not None else fallback, errors="coerce")
    if pd.isna(timestamp):
        return pd.Timestamp(fallback)
    return pd.Timestamp(timestamp).normalize()


def _calendar(asset_cfg: dict, start_date=None, end_date=None) -> pd.DatetimeIndex:
    start = _coerce_date(start_date, DEMO_START_DATE)
    end = _coerce_date(end_date, DEMO_END_DATE)
    if end < start:
        return pd.DatetimeIndex([])

    calendar_type = str(asset_cfg.get("calendar_type", "trading_days")).lower()
    if calendar_type == "continuous":
        return pd.date_range(start, end, freq="D")
    if calendar_type == "weekly":
        return pd.date_range(start, end, freq="W-FRI")
    if calendar_type == "monthly":
        return pd.date_range(start, end, freq="ME")
    return pd.bdate_range(start, end)


_START_LEVELS = {
    "BTC": 430.0,
    "SP500": 2000.0,
    "NASDAQ100": 4500.0,
    "DOWJONES": 17500.0,
    "RUSSELL2000": 1100.0,
    "STOXX600": 350.0,
    "EUROSTOXX50": 3000.0,
    "FTSE100": 6200.0,
    "DAX": 10000.0,
    "CAC40": 4400.0,
    "NIKKEI225": 18000.0,
    "SSECOMPOSITE": 3200.0,
    "EMERGING_MARKETS": 800.0,
    "GOLD": 1100.0,
    "SILVER": 14.0,
    "COPPER": 2.2,
    "BRENT_OIL": 38.0,
    "WTI_OIL": 36.0,
    "NATURAL_GAS": 2.3,
    "WHEAT": 470.0,
    "CORN": 360.0,
    "DXY": 98.0,
    "EURO": 1.08,
    "YUAN": 6.5,
    "LIBRA": 1.45,
    "YEN": 118.0,
    "SWISS_FRANC": 1.0,
    "US3M": 0.3,
    "US2Y": 0.9,
    "US10Y": 2.2,
    "US30Y": 3.0,
    "GERMANY10Y": 0.5,
    "UK10Y": 1.8,
    "JAPAN10Y": 0.25,
    "VIX": 18.0,
    "MOVE_INDEX": 75.0,
    "FINANCIAL_CONDITIONS": 100.0,
    "TED_SPREAD": 0.35,
}

_SIGMAS = {
    "BTC": 0.030,
    "VIX": 0.055,
    "MOVE_INDEX": 0.030,
    "NATURAL_GAS": 0.030,
    "WTI_OIL": 0.025,
    "BRENT_OIL": 0.022,
    "SILVER": 0.018,
    "COPPER": 0.015,
    "GOLD": 0.010,
    "DXY": 0.004,
    "EURO": 0.004,
    "YUAN": 0.002,
    "LIBRA": 0.005,
    "YEN": 0.004,
    "SWISS_FRANC": 0.004,
    "US3M": 0.006,
    "US2Y": 0.008,
    "US10Y": 0.007,
    "US30Y": 0.006,
    "GERMANY10Y": 0.008,
    "UK10Y": 0.008,
    "JAPAN10Y": 0.007,
    "FINANCIAL_CONDITIONS": 0.012,
    "TED_SPREAD": 0.015,
}

_DRIFTS = {
    "BTC": 0.00045,
    "VIX": 0.0,
    "MOVE_INDEX": 0.0,
    "FINANCIAL_CONDITIONS": 100.0,
    "TED_SPREAD": 0.0,
}

_RISK_BETAS = {
    "BTC": 1.6,
    "SP500": 1.0,
    "NASDAQ100": 1.2,
    "DOWJONES": 0.9,
    "RUSSELL2000": 1.15,
    "STOXX600": 0.9,
    "EUROSTOXX50": 1.0,
    "FTSE100": 0.8,
    "DAX": 1.0,
    "CAC40": 0.95,
    "NIKKEI225": 0.9,
    "SSECOMPOSITE": 0.7,
    "EMERGING_MARKETS": 1.0,
    "COPPER": 0.7,
    "BRENT_OIL": 0.6,
    "WTI_OIL": 0.6,
    "NATURAL_GAS": 0.35,
    "WHEAT": 0.2,
    "CORN": 0.2,
    "EURO": 0.15,
    "LIBRA": 0.15,
    "YUAN": 0.10,
    "YEN": -0.20,
    "SWISS_FRANC": -0.25,
    "DXY": -0.35,
    "GOLD": -0.15,
    "SILVER": 0.15,
    "VIX": -1.8,
    "MOVE_INDEX": -0.8,
    "FINANCIAL_CONDITIONS": -0.5,
    "TED_SPREAD": -0.5,
}


def _date_factor(dates: pd.DatetimeIndex) -> np.ndarray:
    if len(dates) == 0:
        return np.array([], dtype=float)
    ordinal = dates.view("int64") / 86_400_000_000_000
    factor = (
        0.0065 * np.sin(ordinal * 0.017)
        + 0.0040 * np.sin(ordinal * 0.071)
        + 0.0020 * np.cos(ordinal * 0.131)
    )
    return np.asarray(factor, dtype=float)


def _event_stress(dates: pd.DatetimeIndex) -> np.ndarray:
    stress = np.zeros(len(dates), dtype=float)
    if not len(dates):
        return stress
    d = pd.Series(dates)

    covid = (d >= pd.Timestamp("2020-02-20")) & (d <= pd.Timestamp("2020-03-23"))
    covid_recovery = (d > pd.Timestamp("2020-03-23")) & (d <= pd.Timestamp("2020-06-30"))
    tightening = (d >= pd.Timestamp("2022-01-03")) & (d <= pd.Timestamp("2022-10-31"))
    banking = (d >= pd.Timestamp("2023-03-08")) & (d <= pd.Timestamp("2023-03-20"))

    stress[covid.to_numpy()] = -0.011
    stress[covid_recovery.to_numpy()] = 0.0045
    stress[tightening.to_numpy()] = -0.0015
    stress[banking.to_numpy()] = -0.004
    return stress


def _btc_demo_close(dates: pd.DatetimeIndex) -> pd.Series:
    anchors = [
        ("2010-07-18", 0.08),
        ("2011-06-08", 30.0),
        ("2013-12-04", 1_100.0),
        ("2015-01-14", 200.0),
        ("2016-01-01", 430.0),
        ("2016-07-09", 650.0),
        ("2017-12-17", 19_000.0),
        ("2018-12-15", 3_200.0),
        ("2020-03-16", 5_000.0),
        ("2021-11-10", 69_000.0),
        ("2022-11-21", 16_000.0),
        ("2024-03-14", 73_000.0),
        ("2024-04-20", 64_000.0),
        ("2025-10-01", 105_000.0),
        ("2026-01-01", 96_000.0),
    ]
    anchor_dates = pd.to_datetime([item[0] for item in anchors])
    anchor_values = np.log(np.array([item[1] for item in anchors], dtype=float))
    x = dates.view("int64").astype(float)
    xa = anchor_dates.view("int64").astype(float)
    interpolated = np.interp(x, xa, anchor_values)

    rng = np.random.default_rng(_stable_seed("BTC_DEMO_PATH"))
    noise = rng.normal(0, 0.018, len(dates))
    noise = pd.Series(noise).rolling(7, min_periods=1).mean().to_numpy()
    return pd.Series(np.exp(interpolated + noise), index=dates, dtype=float)


def _policy_cycle(dates: pd.DatetimeIndex) -> np.ndarray:
    start = pd.Timestamp("2022-03-01")
    peak = pd.Timestamp("2023-07-01")
    normalization = pd.Timestamp("2026-12-31")
    date_values = dates.view("int64").astype(float)
    rise = np.clip(
        (date_values - start.value) / (peak.value - start.value),
        0.0,
        1.0,
    )
    decline = np.clip(
        (date_values - peak.value) / (normalization.value - peak.value),
        0.0,
        1.0,
    )
    return rise * (1.0 - 0.35 * decline)


def _mean_reverting_level(
    targets: np.ndarray,
    rng: np.random.Generator,
    start_level: float,
    speed: float,
    noise_scale: float,
    lower: float,
    upper: float,
) -> np.ndarray:
    levels = np.empty(len(targets), dtype=float)
    if not len(targets):
        return levels

    levels[0] = float(np.clip(start_level, lower, upper))
    innovations = rng.normal(0.0, noise_scale, len(targets))
    for index in range(1, len(targets)):
        previous = levels[index - 1]
        candidate = previous + speed * (targets[index] - previous) + innovations[index]
        levels[index] = float(np.clip(candidate, lower, upper))
    return levels


def _stress_proxy_close(
    asset_key: str,
    dates: pd.DatetimeIndex,
    rng: np.random.Generator,
) -> pd.Series:
    is_vix = asset_key == "VIX"
    base = 18.0 if is_vix else 85.0
    lower = 9.0 if is_vix else 45.0
    upper = 85.0 if is_vix else 200.0
    factor_scale = 800.0 if is_vix else 1_800.0
    event_scale = 4_500.0 if is_vix else 8_000.0
    noise_scale = 0.85 if is_vix else 1.8
    targets = (
        base
        + np.clip(-_date_factor(dates), 0.0, None) * factor_scale
        + np.clip(-_event_stress(dates), 0.0, None) * event_scale
    )
    levels = _mean_reverting_level(
        targets=targets,
        rng=rng,
        start_level=base,
        speed=0.12,
        noise_scale=noise_scale,
        lower=lower,
        upper=upper,
    )
    return pd.Series(levels, index=dates, dtype=float)


def _yield_close(
    asset_key: str,
    dates: pd.DatetimeIndex,
    rng: np.random.Generator,
) -> pd.Series:
    start_level = float(_START_LEVELS[asset_key])
    targets = start_level + _YIELD_TIGHTENING_SHIFTS[asset_key] * _policy_cycle(dates)
    levels = _mean_reverting_level(
        targets=targets,
        rng=rng,
        start_level=start_level,
        speed=0.035,
        noise_scale=0.018,
        lower=0.01,
        upper=8.0,
    )
    return pd.Series(levels, index=dates, dtype=float)


def _stress_level_close(
    asset_key: str,
    dates: pd.DatetimeIndex,
    rng: np.random.Generator,
) -> pd.Series:
    event_pressure = np.clip(-_event_stress(dates), 0.0, None)
    factor_pressure = np.clip(-_date_factor(dates), 0.0, None)
    if asset_key == "FINANCIAL_CONDITIONS":
        targets = 100.0 + event_pressure * 500.0 + factor_pressure * 80.0
        levels = _mean_reverting_level(
            targets, rng, 100.0, 0.08, 0.08, 96.0, 106.0,
        )
    else:
        targets = 0.35 + event_pressure * 35.0 + factor_pressure * 4.0
        levels = _mean_reverting_level(
            targets, rng, 0.35, 0.10, 0.012, 0.05, 2.5,
        )
    return pd.Series(levels, index=dates, dtype=float)


def _currency_close(
    asset_key: str,
    dates: pd.DatetimeIndex,
    rng: np.random.Generator,
) -> pd.Series:
    start_level = float(_START_LEVELS[asset_key])
    beta = float(_RISK_BETAS.get(asset_key, 0.0))
    log_anchor = np.log(start_level)
    targets = log_anchor + beta * _date_factor(dates) * 4.0
    log_levels = _mean_reverting_level(
        targets=targets,
        rng=rng,
        start_level=log_anchor,
        speed=0.025,
        noise_scale=float(_SIGMAS.get(asset_key, 0.0035)),
        lower=log_anchor - 0.35,
        upper=log_anchor + 0.35,
    )
    return pd.Series(np.exp(log_levels), index=dates, dtype=float)


def _generic_close(asset_key: str, asset_cfg: dict, dates: pd.DatetimeIndex) -> pd.Series:
    start_level = float(_START_LEVELS.get(asset_key, 100.0))
    market_type = str(asset_cfg.get("market_type", "")).lower()
    beta = float(_RISK_BETAS.get(asset_key, 0.8))
    rng = np.random.default_rng(_stable_seed(f"asset::{asset_key}"))

    if asset_key in {"VIX", "MOVE_INDEX"}:
        return _stress_proxy_close(asset_key, dates, rng)
    if asset_key in _YIELD_TIGHTENING_SHIFTS:
        return _yield_close(asset_key, dates, rng)
    if asset_key in {"FINANCIAL_CONDITIONS", "TED_SPREAD"}:
        return _stress_level_close(asset_key, dates, rng)
    if market_type in {"currency", "currency_index", "fx"}:
        return _currency_close(asset_key, dates, rng)

    default_sigma = 0.0065 if market_type == "equity_index" else 0.0080
    sigma = float(_SIGMAS.get(asset_key, default_sigma))
    default_drift = 0.00022 if market_type == "equity_index" else 0.00008
    drift = float(_DRIFTS.get(asset_key, default_drift))
    idiosyncratic = rng.normal(drift, sigma, len(dates))
    returns = (
        idiosyncratic
        + beta * _date_factor(dates)
        + beta * _event_stress(dates)
    )
    log_level = np.log(max(start_level, 1e-8)) + np.cumsum(returns)
    return pd.Series(np.exp(log_level), index=dates, dtype=float)


def load_demo_asset_data(
    assets_config: dict,
    asset_key: str,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    """Create a deterministic synthetic OHLCV frame for one configured asset."""
    if asset_key not in assets_config:
        raise KeyError(f"Asset is not configured: {asset_key}")

    cfg = assets_config[asset_key]
    requested_start = _coerce_date(start_date, DEMO_START_DATE)
    requested_end = _coerce_date(end_date, DEMO_END_DATE)
    generation_start = max(
        pd.Timestamp(DEMO_START_DATE),
        pd.Timestamp(_ASSET_START_DATES.get(asset_key, DEMO_START_DATE)),
    )
    dates = _calendar(
        cfg,
        start_date=generation_start,
        end_date=requested_end,
    )
    if len(dates) == 0:
        return pd.DataFrame(
            columns=[
                "snapped_at",
                "price",
                "open",
                "high",
                "low",
                "close",
                "total_volume",
                "volume",
            ]
        )

    close = _btc_demo_close(dates) if asset_key == "BTC" else _generic_close(asset_key, cfg, dates)
    sigma = float(_SIGMAS.get(asset_key, 0.011))
    rng = np.random.default_rng(_stable_seed(f"ohlcv::{asset_key}"))

    positive_expected = bool(cfg.get("positive_values_expected", True))
    if positive_expected and (close > 0).all():
        open_ = close.shift(1).fillna(close.iloc[0]) * (
            1 + rng.normal(0, max(sigma / 6, 0.0005), len(close))
        )
        upper = pd.concat([open_, close], axis=1).max(axis=1)
        lower = pd.concat([open_, close], axis=1).min(axis=1)
        wick = np.abs(
            rng.normal(max(sigma / 4, 0.001), max(sigma / 8, 0.0002), len(close))
        )
        high = upper * (1 + wick)
        low = (lower * (1 - wick)).clip(lower=1e-8)
    else:
        level_scale = max(float(close.abs().median()), 1.0)
        open_ = close.shift(1).fillna(close.iloc[0]) + rng.normal(
            0, max(level_scale * sigma / 6, 0.001), len(close)
        )
        upper = pd.concat([open_, close], axis=1).max(axis=1)
        lower = pd.concat([open_, close], axis=1).min(axis=1)
        wick_abs = np.abs(
            rng.normal(
                max(level_scale * sigma / 4, 0.002),
                max(level_scale * sigma / 8, 0.001),
                len(close),
            )
        )
        high = upper + wick_abs
        low = lower - wick_abs

    volume_expected = cfg.get("volume_expected")
    if volume_expected is None:
        volume_expected = asset_key not in {
            "DXY",
            "US3M",
            "US2Y",
            "US10Y",
            "US30Y",
            "GERMANY10Y",
            "UK10Y",
            "JAPAN10Y",
            "FINANCIAL_CONDITIONS",
            "TED_SPREAD",
        }

    if volume_expected:
        volume = rng.lognormal(mean=16.0, sigma=0.55, size=len(close))
        stress_mask = _event_stress(dates) < 0
        volume[stress_mask] *= 2.2
    else:
        volume = np.full(len(close), np.nan)

    frame = pd.DataFrame(
        {
            "snapped_at": dates,
            "price": close.to_numpy(dtype=float),
            "open": open_.to_numpy(dtype=float),
            "high": high.to_numpy(dtype=float),
            "low": low.to_numpy(dtype=float),
            "close": close.to_numpy(dtype=float),
            "total_volume": volume,
            "volume": volume,
        }
    )

    # When the real contract does not expect native OHLC, keep price/close but
    # leave O/H/L unavailable so the existing analytical engine exercises its
    # documented synthetic-OHLC fallback and provenance flags.
    if cfg.get("ohlc_expected") is False:
        frame[["open", "high", "low"]] = np.nan

    frame = frame.loc[
        frame["snapped_at"].between(requested_start, requested_end, inclusive="both")
    ]
    return frame.reset_index(drop=True)


def load_demo_events(start_date=None, end_date=None) -> pd.DataFrame:
    frame = pd.DataFrame(_DEMO_EVENTS, columns=EVENT_COLUMNS)
    frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce")
    frame = frame.dropna(subset=["event_date"])

    if start_date is not None:
        frame = frame[frame["event_date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        frame = frame[frame["event_date"] <= pd.to_datetime(end_date)]

    return frame.sort_values("event_date").reset_index(drop=True)


def load_demo_events_from_table(
    table_name: str,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    frame = load_demo_events(start_date=start_date, end_date=end_date)
    if table_name not in {"bitcoin_historical_events", "world_historical_events"}:
        return pd.DataFrame(columns=EVENT_COLUMNS)
    return frame.loc[frame["event_source_table"].eq(table_name), EVENT_COLUMNS].reset_index(drop=True)


def build_demo_multi_asset_price_frame(
    assets_config: dict,
    selected_assets: list,
    start_date=None,
    end_date=None,
    forward_fill: bool = False,
    return_load_report: bool = False,
):
    frames = []
    load_rows = []

    for asset_key in selected_assets:
        if asset_key not in assets_config:
            load_rows.append(
                {
                    "asset": asset_key,
                    "status": "failed",
                    "rows": 0,
                    "reason": "Asset is not configured",
                }
            )
            continue

        try:
            frame = load_demo_asset_data(
                assets_config=assets_config,
                asset_key=asset_key,
                start_date=start_date,
                end_date=end_date,
            )
            if frame.empty:
                load_rows.append(
                    {"asset": asset_key, "status": "empty", "rows": 0, "reason": "No demo rows"}
                )
                continue

            frames.append(
                frame[["snapped_at", "price"]].rename(columns={"price": asset_key})
            )
            load_rows.append(
                {"asset": asset_key, "status": "loaded", "rows": len(frame), "reason": ""}
            )
        except Exception as exc:
            load_rows.append(
                {
                    "asset": asset_key,
                    "status": "failed",
                    "rows": 0,
                    "reason": str(exc),
                }
            )

    report = pd.DataFrame(load_rows)
    if not frames:
        empty = pd.DataFrame()
        return (empty, report) if return_load_report else empty

    merged = frames[0]
    for frame in frames[1:]:
        merged = pd.merge(merged, frame, on="snapped_at", how="outer")

    merged = merged.sort_values("snapped_at").reset_index(drop=True)
    if forward_fill:
        columns = [column for column in merged.columns if column != "snapped_at"]
        merged[columns] = merged[columns].ffill()

    return (merged, report) if return_load_report else merged


def _macro_profile(macro_key: str) -> dict:
    key = macro_key.upper()
    if key in _MACRO_PROFILES:
        return dict(_MACRO_PROFILES[key])

    if "HICP" in key:
        start_levels = {
            "EURO_HICP_PROCESSED_FOOD": 76.0,
            "EURO_HICP_EX_TOBACCO": 78.0,
            "EURO_HICP_SERVICES": 80.0,
            "EURO_HICP_INDUSTRIAL_GOODS": 82.0,
            "EURO_HICP_ADMINISTERED_ENERGY_FOOD": 74.0,
        }
        return {
            "frequency": "ME",
            "kind": "level",
            "start": start_levels.get(key, 78.0),
            "growth": 0.022,
            "noise": 0.003,
        }

    if key.startswith("EURO_MFI_"):
        if "DEPOSIT" in key:
            start = 2.2
        elif "REVOLVING" in key:
            start = 6.5
        elif "HOUSE_PURCHASE" in key:
            start = 4.5
        else:
            start = 5.0
        return {
            "frequency": "ME",
            "kind": "policy_rate",
            "start": start,
            "noise": 0.035,
        }

    if "FRAUD_LOSSES" in key:
        return {
            "frequency": "2QE-DEC",
            "kind": "level",
            "start": 100.0,
            "growth": 0.040,
            "noise": 0.025,
        }

    return {
        "frequency": "ME",
        "kind": "level",
        "start": 100.0,
        "growth": 0.025,
        "noise": 0.008,
    }


def _macro_frequency(macro_key: str) -> str:
    return str(_macro_profile(macro_key)["frequency"])


def _macro_start_level(macro_key: str) -> float:
    return float(_macro_profile(macro_key)["start"])


def _interpolate_anchors(
    dates: pd.DatetimeIndex,
    anchors: list[tuple[str, float]],
) -> np.ndarray:
    anchor_dates = pd.to_datetime([item[0] for item in anchors])
    anchor_values = np.array([item[1] for item in anchors], dtype=float)
    return np.interp(
        dates.view("int64").astype(float),
        anchor_dates.view("int64").astype(float),
        anchor_values,
    )


def _macro_rate_path(
    macro_key: str,
    dates: pd.DatetimeIndex,
    start_level: float,
) -> np.ndarray:
    key = macro_key.upper()
    if key == "FED_FUNDS_RATE":
        anchors = [
            ("2000-01-31", 5.5),
            ("2004-01-31", 1.0),
            ("2007-07-31", 5.25),
            ("2009-01-31", 0.20),
            ("2016-01-31", 0.40),
            ("2019-01-31", 2.40),
            ("2020-05-31", 0.10),
            ("2023-08-31", 5.30),
            ("2026-12-31", 4.20),
        ]
    elif key == "FED_CREDIT_CARD_DELINQUENCY":
        anchors = [
            ("2000-03-31", 4.7),
            ("2006-12-31", 3.5),
            ("2009-12-31", 6.5),
            ("2021-03-31", 2.1),
            ("2026-12-31", 3.2),
        ]
    elif key == "FED_CHARGE_OFF_RATE_CREDIT_CARDS":
        anchors = [
            ("2000-03-31", 6.0),
            ("2006-12-31", 4.0),
            ("2010-03-31", 10.5),
            ("2021-03-31", 2.0),
            ("2026-12-31", 3.8),
        ]
    else:
        floor = max(0.10, start_level - 3.2)
        anchors = [
            ("2000-01-31", start_level),
            ("2005-01-31", max(floor, start_level - 1.5)),
            ("2008-09-30", start_level),
            ("2016-01-31", floor),
            ("2021-01-31", floor),
            ("2024-01-31", start_level + 0.8),
            ("2026-12-31", start_level),
        ]
    return _interpolate_anchors(dates, anchors)


def build_demo_macro_series(
    macro_key: str,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    requested_start = _coerce_date(start_date, DEMO_START_DATE)
    requested_end = _coerce_date(end_date, DEMO_END_DATE)
    dates = pd.date_range(
        pd.Timestamp(DEMO_START_DATE),
        requested_end,
        freq=_macro_frequency(macro_key),
    )
    if len(dates) == 0:
        return pd.DataFrame(columns=["snapped_at", macro_key])

    profile = _macro_profile(macro_key)
    rng = np.random.default_rng(_stable_seed(f"macro::{macro_key}"))
    level = _macro_start_level(macro_key)
    noise_scale = float(profile.get("noise", 0.008))
    smooth_noise = (
        pd.Series(rng.normal(0.0, noise_scale, len(dates)))
        .rolling(3, min_periods=1)
        .mean()
        .to_numpy()
    )

    if profile["kind"] in {"policy_rate", "stress_rate"}:
        values = _macro_rate_path(macro_key, dates, level) + smooth_noise
        values = np.clip(values, 0.0, None)
    else:
        elapsed_years = (
            dates - pd.Timestamp(DEMO_START_DATE)
        ).days.to_numpy(dtype=float) / 365.2425
        growth = float(profile.get("growth", 0.025))
        seasonal = 0.004 * np.sin(2.0 * np.pi * elapsed_years)
        values = level * np.exp(growth * elapsed_years + seasonal + smooth_noise)

    frame = pd.DataFrame({"snapped_at": dates, macro_key: values})
    return frame.loc[
        frame["snapped_at"].between(
            requested_start,
            requested_end,
            inclusive="both",
        )
    ].reset_index(drop=True)


def align_demo_macro_to_market(
    macro_df: pd.DataFrame,
    market_df: pd.DataFrame,
    macro_key: str,
    market_asset: str,
) -> pd.DataFrame:
    macro = macro_df[["snapped_at", macro_key]].copy()
    market = market_df[["snapped_at", market_asset]].copy()
    macro["snapped_at"] = pd.to_datetime(macro["snapped_at"], errors="coerce")
    market["snapped_at"] = pd.to_datetime(market["snapped_at"], errors="coerce")
    macro = macro.dropna().sort_values("snapped_at").drop_duplicates("snapped_at", keep="last")
    market = market.dropna().sort_values("snapped_at").drop_duplicates("snapped_at", keep="last")

    if macro.empty or market.empty:
        return pd.DataFrame(
            columns=[
                "snapped_at",
                macro_key,
                market_asset,
                "macro_observation_date",
                "macro_age_days",
            ]
        )

    renamed_macro = macro.rename(columns={"snapped_at": "macro_observation_date"})
    aligned = pd.merge_asof(
        market,
        renamed_macro,
        left_on="snapped_at",
        right_on="macro_observation_date",
        direction="backward",
        tolerance=pd.Timedelta(days=120),
    )
    aligned["macro_age_days"] = (
        aligned["snapped_at"] - aligned["macro_observation_date"]
    ).dt.days
    return aligned.dropna(subset=[macro_key, market_asset]).reset_index(drop=True)


def load_demo_macro_pair(
    assets_config: dict,
    macro_key: str,
    market_asset: str,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    macro = build_demo_macro_series(macro_key, start_date=start_date, end_date=end_date)
    market_raw = load_demo_asset_data(
        assets_config=assets_config,
        asset_key=market_asset,
        start_date=start_date,
        end_date=end_date,
    )
    market = market_raw[["snapped_at", "price"]].rename(columns={"price": market_asset})
    return align_demo_macro_to_market(
        macro_df=macro,
        market_df=market,
        macro_key=macro_key,
        market_asset=market_asset,
    )


def demo_table_columns(table_name: str, assets_config: dict) -> list[str]:
    if table_name == "world_historical_events":
        return ["year", "event", "macro_impact", "affected_markets"]
    if table_name == "bitcoin_historical_events":
        return ["event_date", "event_title", "description", "category"]
    if any(cfg.get("table_name") == table_name for cfg in assets_config.values()):
        return [
            "snapped_at",
            "price",
            "open",
            "high",
            "low",
            "close",
            "total_volume",
            "volume",
        ]
    return []


def demo_table_exists(table_name: str, assets_config: dict) -> bool:
    if table_name in {"world_historical_events", "bitcoin_historical_events"}:
        return True
    return any(cfg.get("table_name") == table_name for cfg in assets_config.values())
