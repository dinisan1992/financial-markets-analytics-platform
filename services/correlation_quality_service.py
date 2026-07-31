from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd


def calculate_pair_correlation(left: pd.Series, right: pd.Series):
    """Calculate correlation only when both samples have non-zero variance."""
    if len(left) < 2 or len(right) < 2:
        return np.nan
    if left.nunique(dropna=True) < 2 or right.nunique(dropna=True) < 2:
        return np.nan
    return left.corr(right)


def classify_correlation_confidence(observations: int, coverage_pct: float) -> str:
    """Classify whether a reported correlation has enough aligned evidence."""
    if observations < 30:
        return "INSUFFICIENT"
    if observations < 90 or coverage_pct < 70:
        return "LOW"
    if observations < 252 or coverage_pct < 90:
        return "MODERATE"
    return "HIGH"


def correlation_confidence_interval(correlation, observations: int):
    """Return a Fisher-transformed 95% confidence interval."""
    if observations <= 3 or pd.isna(correlation):
        return np.nan, np.nan

    clipped = float(np.clip(correlation, -0.999999, 0.999999))
    fisher_z = np.arctanh(clipped)
    margin = 1.96 / np.sqrt(observations - 3)
    return float(np.tanh(fisher_z - margin)), float(np.tanh(fisher_z + margin))


def build_pair_correlation_statistics(returns_df: pd.DataFrame) -> pd.DataFrame:
    """Summarize pairwise-valid return samples without forward filling."""
    columns = [
        "asset_a",
        "asset_b",
        "common_observations",
        "common_start_date",
        "common_end_date",
        "coverage_ratio",
        "coverage_pct",
        "correlation",
        "correlation_ci95_low",
        "correlation_ci95_high",
        "confidence",
        "potential_bias",
    ]
    if returns_df.empty or "snapped_at" not in returns_df.columns:
        return pd.DataFrame(columns=columns)

    data = returns_df.copy()
    data["snapped_at"] = pd.to_datetime(data["snapped_at"], errors="coerce")
    asset_columns = [column for column in data.columns if column != "snapped_at"]
    if len(asset_columns) < 2:
        return pd.DataFrame(columns=columns)

    rows = []
    for asset_a, asset_b in combinations(asset_columns, 2):
        pair = data[["snapped_at", asset_a, asset_b]].copy()
        pair[asset_a] = pd.to_numeric(pair[asset_a], errors="coerce")
        pair[asset_b] = pd.to_numeric(pair[asset_b], errors="coerce")
        pair = pair.replace([np.inf, -np.inf], np.nan)

        smaller_sample = min(pair[asset_a].notna().sum(), pair[asset_b].notna().sum())
        pair = pair.dropna(subset=["snapped_at", asset_a, asset_b]).sort_values("snapped_at")
        observations = len(pair)
        coverage_ratio = observations / smaller_sample if smaller_sample else 0.0
        coverage_pct = round(coverage_ratio * 100, 2)
        correlation = calculate_pair_correlation(pair[asset_a], pair[asset_b])
        ci_low, ci_high = correlation_confidence_interval(correlation, observations)
        confidence = (
            "INSUFFICIENT"
            if pd.isna(correlation)
            else classify_correlation_confidence(observations, coverage_pct)
        )

        rows.append(
            {
                "asset_a": asset_a,
                "asset_b": asset_b,
                "common_observations": observations,
                "common_start_date": pair["snapped_at"].min().date() if observations else None,
                "common_end_date": pair["snapped_at"].max().date() if observations else None,
                "coverage_ratio": round(coverage_ratio, 4),
                "coverage_pct": coverage_pct,
                "correlation": correlation,
                "correlation_ci95_low": ci_low,
                "correlation_ci95_high": ci_high,
                "confidence": confidence,
                "potential_bias": confidence in {"INSUFFICIENT", "LOW"},
            }
        )

    return pd.DataFrame(rows, columns=columns)
