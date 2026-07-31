import numpy as np
import pandas as pd


def _clean_series(frame, date_column, value_column):
    if frame is None or frame.empty:
        return pd.DataFrame(columns=[date_column, value_column])

    output = frame[[date_column, value_column]].copy()
    output[date_column] = pd.to_datetime(output[date_column], errors="coerce")
    output[value_column] = pd.to_numeric(output[value_column], errors="coerce")
    output = output.dropna(subset=[date_column, value_column])
    return output.sort_values(date_column).drop_duplicates(date_column, keep="last")


def infer_macro_tolerance_days(macro_dates, minimum=7, maximum=400):
    """Infer a conservative maximum carry-forward age from the source cadence."""
    dates = pd.Series(pd.to_datetime(macro_dates, errors="coerce")).dropna().sort_values()
    median_gap = dates.diff().dt.days.dropna().median()
    if pd.isna(median_gap):
        return maximum
    return int(np.clip(np.ceil(float(median_gap) * 3), minimum, maximum))


def align_macro_to_market_calendar(
    macro_df,
    market_df,
    macro_column,
    market_column,
    max_macro_age_days=None,
):
    """Align the latest known macro value to real market observations only."""
    macro = _clean_series(macro_df, "snapped_at", macro_column)
    market = _clean_series(market_df, "snapped_at", market_column)

    if macro.empty or market.empty:
        return pd.DataFrame(
            columns=[
                "snapped_at",
                macro_column,
                market_column,
                "macro_observation_date",
                "macro_age_days",
            ]
        )

    tolerance_days = max_macro_age_days
    if tolerance_days is None:
        tolerance_days = infer_macro_tolerance_days(macro["snapped_at"])
    if int(tolerance_days) <= 0:
        raise ValueError("max_macro_age_days must be positive")

    macro = macro.rename(columns={"snapped_at": "macro_observation_date"})
    aligned = pd.merge_asof(
        market,
        macro,
        left_on="snapped_at",
        right_on="macro_observation_date",
        direction="backward",
        tolerance=pd.Timedelta(days=int(tolerance_days)),
    )
    aligned["macro_age_days"] = (
        aligned["snapped_at"] - aligned["macro_observation_date"]
    ).dt.days
    aligned = aligned.dropna(subset=[macro_column, market_column]).reset_index(drop=True)
    aligned.attrs["calendar_policy"] = "market_observations"
    aligned.attrs["macro_tolerance_days"] = int(tolerance_days)
    return aligned


def prepare_macro_market_features(
    aligned_df,
    macro_column,
    market_column,
    windows=(30, 90),
):
    """Create observation-based macro/market changes without annualizing macro data."""
    if aligned_df is None or aligned_df.empty:
        return pd.DataFrame()

    frame = aligned_df.copy().sort_values("snapped_at").reset_index(drop=True)
    frame[macro_column] = pd.to_numeric(frame[macro_column], errors="coerce")
    frame[market_column] = pd.to_numeric(frame[market_column], errors="coerce")
    frame[f"{macro_column}_change_1obs"] = frame[macro_column].pct_change(fill_method=None)
    frame[f"{market_column}_return_1obs"] = frame[market_column].pct_change(fill_method=None)

    for window in windows:
        window = int(window)
        if window < 2:
            raise ValueError("Macro analytics windows must be at least two observations")

        macro_change = frame[macro_column].pct_change(window, fill_method=None)
        market_return = frame[market_column].pct_change(window, fill_method=None)
        rolling_mean = frame[macro_column].rolling(window, min_periods=window).mean()
        rolling_std = frame[macro_column].rolling(window, min_periods=window).std()

        frame[f"{macro_column}_change_{window}obs"] = macro_change
        frame[f"{market_column}_return_{window}obs"] = market_return
        frame[f"{macro_column}_zscore_{window}obs"] = (
            (frame[macro_column] - rolling_mean) / rolling_std.replace(0, np.nan)
        )
        frame[f"rolling_correlation_{window}obs"] = (
            frame[f"{macro_column}_change_1obs"]
            .rolling(window, min_periods=max(5, window // 2))
            .corr(frame[f"{market_column}_return_1obs"])
        )

    return frame
