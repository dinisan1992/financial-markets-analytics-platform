import pandas as pd
import numpy as np


def load_asset_price_series(
    engine,
    asset_key: str,
    asset_cfg: dict,
    start_date=None,
    end_date=None
) -> pd.DataFrame:
    """
    Loads an asset price series from the table defined in asset_config.py.

    Requires:
    - snapped_at
    - price

    Returns:
    - snapped_at
    - asset_key as the price column
    """

    table_name = asset_cfg["table_name"]

    query = f"""
    SELECT
        snapped_at,
        price
    FROM `{table_name}`
    WHERE snapped_at IS NOT NULL
      AND price IS NOT NULL
    ORDER BY snapped_at;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        return pd.DataFrame(columns=["snapped_at", asset_key])

    df["snapped_at"] = pd.to_datetime(df["snapped_at"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    df = df.dropna(subset=["snapped_at", "price"]).copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    if start_date:
        df = df[df["snapped_at"] >= pd.to_datetime(start_date)]

    if end_date:
        df = df[df["snapped_at"] <= pd.to_datetime(end_date)]

    df = df[["snapped_at", "price"]].copy()
    df = df.rename(columns={"price": asset_key})

    return df


def build_multi_asset_price_frame(
    engine,
    selected_assets: list,
    assets_config: dict,
    start_date=None,
    end_date=None,
    forward_fill: bool = True
) -> pd.DataFrame:
    """
    Creates a multi-asset DataFrame with prices aligned by date.

    Result:
    snapped_at | BTC | SP500 | GOLD | ...
    """

    frames = []

    for asset_key in selected_assets:
        if asset_key not in assets_config:
            continue

        asset_cfg = assets_config[asset_key]

        try:
            asset_df = load_asset_price_series(
                engine=engine,
                asset_key=asset_key,
                asset_cfg=asset_cfg,
                start_date=start_date,
                end_date=end_date
            )

            if not asset_df.empty:
                frames.append(asset_df)

        except Exception:
            continue

    if not frames:
        return pd.DataFrame()

    merged_df = frames[0]

    for frame in frames[1:]:
        merged_df = pd.merge(
            merged_df,
            frame,
            on="snapped_at",
            how="outer"
        )

    merged_df = merged_df.sort_values("snapped_at").reset_index(drop=True)

    if forward_fill:
        asset_cols = [col for col in merged_df.columns if col != "snapped_at"]
        merged_df[asset_cols] = merged_df[asset_cols].ffill()

    return merged_df


def calculate_returns(
    price_df: pd.DataFrame,
    method: str = "pct"
) -> pd.DataFrame:
    """
    Calculates asset returns.

    method:
    - pct: simple percentage returns
    - log: logarithmic returns
    """

    if price_df.empty:
        return pd.DataFrame()

    returns_df = price_df[["snapped_at"]].copy()
    returns_df["snapped_at"] = pd.to_datetime(returns_df["snapped_at"], errors="coerce")
    asset_cols = [col for col in price_df.columns if col != "snapped_at"]

    for col in asset_cols:
        series = pd.to_numeric(price_df[col], errors="coerce")
        valid_series = series.dropna()

        if method == "log":
            positive_series = valid_series.where(valid_series > 0)
            returns = np.log(positive_series / positive_series.shift(1))
        else:
            returns = valid_series.pct_change(fill_method=None)

        returns_df[col] = returns.reindex(price_df.index)

    returns_df = returns_df.replace([np.inf, -np.inf], np.nan)
    returns_df = returns_df.dropna(how="all", subset=asset_cols).reset_index(drop=True)

    return returns_df


def calculate_correlation_matrix(
    returns_df: pd.DataFrame,
    min_periods: int = 30
) -> pd.DataFrame:
    """
    Calculates the correlation matrix based on returns.
    """

    if returns_df.empty:
        return pd.DataFrame()

    asset_cols = [col for col in returns_df.columns if col != "snapped_at"]

    if len(asset_cols) < 2:
        return pd.DataFrame()

    corr_df = returns_df[asset_cols].corr(min_periods=min_periods)

    return corr_df


def calculate_rolling_correlation(
    returns_df: pd.DataFrame,
    asset_x: str,
    asset_y: str,
    window: int = 90
) -> pd.DataFrame:
    """
    Calculates rolling correlation between two assets.
    """

    if returns_df.empty:
        return pd.DataFrame()

    if asset_x not in returns_df.columns or asset_y not in returns_df.columns:
        return pd.DataFrame()

    rolling_df = returns_df[["snapped_at", asset_x, asset_y]].copy()
    rolling_df["snapped_at"] = pd.to_datetime(rolling_df["snapped_at"], errors="coerce")
    rolling_df[asset_x] = pd.to_numeric(rolling_df[asset_x], errors="coerce")
    rolling_df[asset_y] = pd.to_numeric(rolling_df[asset_y], errors="coerce")
    rolling_df = rolling_df.dropna(subset=["snapped_at", asset_x, asset_y]).copy()
    rolling_df = rolling_df.sort_values("snapped_at").reset_index(drop=True)

    if len(rolling_df) < window:
        return pd.DataFrame()

    rolling_df["rolling_correlation"] = (
        rolling_df[asset_x]
        .rolling(window=window, min_periods=window)
        .corr(rolling_df[asset_y])
    )

    rolling_df = rolling_df.dropna(subset=["rolling_correlation"]).reset_index(drop=True)

    return rolling_df


def build_scatter_returns_frame(
    returns_df: pd.DataFrame,
    asset_x: str,
    asset_y: str
) -> pd.DataFrame:
    """
    Prepares a DataFrame for a returns scatter plot between two assets.
    """

    if returns_df.empty:
        return pd.DataFrame()

    if asset_x not in returns_df.columns or asset_y not in returns_df.columns:
        return pd.DataFrame()

    scatter_df = returns_df[["snapped_at", asset_x, asset_y]].copy()
    scatter_df = scatter_df.dropna(subset=[asset_x, asset_y]).reset_index(drop=True)

    scatter_df[f"{asset_x}_return_pct"] = scatter_df[asset_x] * 100
    scatter_df[f"{asset_y}_return_pct"] = scatter_df[asset_y] * 100

    return scatter_df


def normalize_base_100(price_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes prices to Base 100.
    """

    if price_df.empty:
        return pd.DataFrame()

    norm_df = price_df.copy()
    asset_cols = [col for col in norm_df.columns if col != "snapped_at"]

    for col in asset_cols:
        series = norm_df[col].dropna()

        if series.empty:
            continue

        base_value = series.iloc[0]

        if base_value == 0:
            continue

        norm_df[col] = (norm_df[col] / base_value) * 100

    return norm_df
