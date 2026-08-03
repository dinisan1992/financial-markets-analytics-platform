from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import requests

from market_source_manifest import FEDERAL_RESERVE_H15_URL


H15_HEADER_ROW = 5
H15_DATE_COLUMN = "Time Period"
H15_US2Y_SERIES = "RIFLGFCY02_N.B"
H15_US2Y_SOURCE_LABEL = (
    "Federal Reserve H.15 RIFLGFCY02_N.B (FRED alias DGS2)"
)
STANDARD_MARKET_COLUMNS = (
    "snapped_at",
    "price",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "total_volume",
    "source_file",
)


def download_h15_package(destination, timeout=120):
    """Download the official Federal Reserve H.15 CSV package."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".download")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; FinancialAnalyticsPortfolio/0.5; "
            "+https://www.federalreserve.gov/)"
        )
    }

    try:
        with requests.get(
            FEDERAL_RESERVE_H15_URL,
            headers=headers,
            timeout=timeout,
            stream=True,
        ) as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
        if not temporary.exists() or temporary.stat().st_size == 0:
            raise RuntimeError("Federal Reserve H.15 download was empty")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    return destination


def prepare_h15_market_frame(source, series_id=H15_US2Y_SERIES):
    """Convert one H.15 package series to the standard market CSV contract."""
    frame = pd.read_csv(source, skiprows=H15_HEADER_ROW, dtype=str)
    if H15_DATE_COLUMN not in frame.columns:
        raise ValueError(f"H.15 date column not found: {H15_DATE_COLUMN}")
    if series_id not in frame.columns:
        raise ValueError(f"H.15 series not found: {series_id}")

    output = pd.DataFrame(
        {
            "snapped_at": pd.to_datetime(
                frame[H15_DATE_COLUMN], format="%Y-%m-%d", errors="coerce"
            ),
            "price": pd.to_numeric(
                frame[series_id].replace({"ND": np.nan, "": np.nan}),
                errors="coerce",
            ),
        }
    )
    output = output.dropna(subset=["snapped_at", "price"])
    output = (
        output.sort_values("snapped_at", kind="mergesort")
        .drop_duplicates("snapped_at", keep="last")
        .reset_index(drop=True)
    )
    if output.empty:
        raise ValueError(f"H.15 series has no valid observations: {series_id}")

    for column in ("open", "high", "low", "close", "adj_close", "total_volume"):
        output[column] = np.nan
    output["source_file"] = H15_US2Y_SOURCE_LABEL
    return output[list(STANDARD_MARKET_COLUMNS)]


def validate_h15_market_frame(frame):
    """Validate the canonical date/value identity before any persistent write."""
    required = set(STANDARD_MARKET_COLUMNS)
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing standard market columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("Official market frame is empty")
    if frame["snapped_at"].isna().any() or frame["price"].isna().any():
        raise ValueError("Official market frame contains invalid dates or prices")
    if frame["snapped_at"].duplicated().any():
        raise ValueError("Official market frame contains duplicate dates")
    if not frame["snapped_at"].is_monotonic_increasing:
        raise ValueError("Official market frame is not ordered by date")
    return {
        "rows": int(len(frame)),
        "unique_dates": int(frame["snapped_at"].nunique()),
        "first_date": frame["snapped_at"].min().date(),
        "last_date": frame["snapped_at"].max().date(),
        "native_ohlc_rows": int(
            frame[["open", "high", "low", "close"]].notna().all(axis=1).sum()
        ),
    }


def write_standard_market_csv(frame, destination):
    """Atomically write a validated frame using the existing semicolon format."""
    validate_h15_market_frame(frame)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".candidate")
    output = frame.copy()
    output["snapped_at"] = pd.to_datetime(output["snapped_at"]).dt.strftime(
        "%Y-%m-%d"
    )
    try:
        output.to_csv(
            temporary,
            sep=";",
            index=False,
            encoding="utf-8-sig",
            lineterminator="\n",
        )
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return destination
