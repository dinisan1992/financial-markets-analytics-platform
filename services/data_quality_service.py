from __future__ import annotations

import io
import json
import zipfile
from datetime import date
from itertools import combinations

import numpy as np
import pandas as pd

from services import data_access_service


def _safe_percentage(numerator, denominator):
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 2)


def _longest_calendar_gap(dates: pd.Series):
    unique_dates = pd.Series(pd.to_datetime(dates, errors="coerce").dropna().unique()).sort_values()
    if len(unique_dates) < 2:
        return 0
    return int(unique_dates.diff().dt.days.max())


def _expected_observations(start_date, end_date, calendar_type):
    if pd.isna(start_date) or pd.isna(end_date):
        return 0

    if calendar_type == "continuous":
        return len(pd.date_range(start_date, end_date, freq="D"))

    if calendar_type == "weekly":
        return len(pd.date_range(start_date, end_date, freq="7D"))

    if calendar_type == "monthly":
        return len(pd.period_range(start_date, end_date, freq="M"))

    return len(pd.bdate_range(start_date, end_date))


def audit_asset_frame(
    asset_key: str,
    asset_cfg: dict,
    frame: pd.DataFrame,
    as_of=None,
):
    """Calculate non-sensitive data-quality metrics for one asset frame."""
    as_of = pd.Timestamp(as_of or date.today()).normalize()
    rows_total = len(frame)
    output = frame.copy()

    date_column = "snapped_at" if "snapped_at" in output.columns else None
    price_column = "price" if "price" in output.columns else "close" if "close" in output.columns else None

    if date_column is None or price_column is None:
        return {
            "asset": asset_key,
            "table": asset_cfg.get("table_name"),
            "status": "ERROR",
            "error": "Missing date or price column",
            "rows": rows_total,
        }

    output[date_column] = pd.to_datetime(output[date_column], errors="coerce")
    output[price_column] = pd.to_numeric(output[price_column], errors="coerce")

    duplicate_dates = int(output[date_column].dropna().duplicated().sum())
    invalid_mask = ~np.isfinite(output[price_column])
    if asset_cfg.get("positive_values_expected", True):
        invalid_mask |= output[price_column] <= 0
    invalid_prices = int(invalid_mask.fillna(False).sum())
    missing_dates = int(output[date_column].isna().sum())
    missing_prices = int(output[price_column].isna().sum())

    valid = output.dropna(subset=[date_column, price_column]).copy()
    valid = valid[np.isfinite(valid[price_column])]
    if asset_cfg.get("positive_values_expected", True):
        valid = valid[valid[price_column] > 0]
    valid = valid.sort_values(date_column).drop_duplicates(date_column, keep="last")

    first_date = valid[date_column].min() if not valid.empty else pd.NaT
    last_date = valid[date_column].max() if not valid.empty else pd.NaT
    stale_days = int((as_of - last_date.normalize()).days) if pd.notna(last_date) else None

    returns = valid[price_column].pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    valid_returns = returns.dropna()
    zero_return_pct = _safe_percentage((valid_returns.abs() < 1e-12).sum(), len(valid_returns))

    volume_column = next(
        (column for column in ["total_volume", "volume"] if column in output.columns),
        None,
    )
    volume_available_pct = 0.0
    if volume_column is not None:
        volume = pd.to_numeric(output[volume_column], errors="coerce")
        volume_available_pct = _safe_percentage((volume > 0).sum(), rows_total)

    native_ohlc_rows = 0
    native_ohlc_pct = 0.0
    if all(column in output.columns for column in ["open", "high", "low", "close"]):
        ohlc = output[["open", "high", "low", "close"]].apply(pd.to_numeric, errors="coerce")
        native_mask = (
            np.isfinite(ohlc.to_numpy(dtype=float)).all(axis=1)
            & (ohlc > 0).all(axis=1)
            & (ohlc["high"] >= ohlc[["open", "close"]].max(axis=1))
            & (ohlc["low"] <= ohlc[["open", "close"]].min(axis=1))
        )
        native_ohlc_rows = int(native_mask.sum())
        native_ohlc_pct = _safe_percentage(native_ohlc_rows, rows_total)

    expected_count = _expected_observations(
        first_date,
        last_date,
        asset_cfg.get("calendar_type", "trading_days"),
    )
    coverage_pct = min(_safe_percentage(len(valid), expected_count), 100.0) if expected_count else 0.0
    longest_gap_days = _longest_calendar_gap(valid[date_column]) if not valid.empty else 0

    stale_limits = {
        "continuous": 5,
        "trading_days": 10,
        "weekly": 21,
        "monthly": 62,
    }
    stale_limit = stale_limits.get(asset_cfg.get("calendar_type"), 10)
    warnings = []
    if duplicate_dates:
        warnings.append("duplicate_dates")
    if invalid_prices:
        warnings.append("invalid_prices")
    if missing_dates or missing_prices:
        warnings.append("missing_core_values")
    if stale_days is None or stale_days > stale_limit:
        warnings.append("stale_data")
    if coverage_pct < 90:
        warnings.append("low_calendar_coverage")
    if zero_return_pct > 15:
        warnings.append("excess_zero_returns")
    if asset_cfg.get("volume_expected") and volume_available_pct < 50:
        warnings.append("volume_unavailable")

    status = "OK" if not warnings else "WARNING"
    if not len(valid):
        status = "ERROR"

    return {
        "asset": asset_key,
        "table": asset_cfg.get("table_name"),
        "asset_class": asset_cfg.get("asset_class"),
        "calendar_type": asset_cfg.get("calendar_type"),
        "periods_per_year": asset_cfg.get("periods_per_year"),
        "rows": rows_total,
        "valid_rows": len(valid),
        "first_date": first_date.date() if pd.notna(first_date) else None,
        "last_date": last_date.date() if pd.notna(last_date) else None,
        "stale_days": stale_days,
        "duplicate_dates": duplicate_dates,
        "missing_dates": missing_dates,
        "missing_prices": missing_prices,
        "invalid_prices": invalid_prices,
        "zero_return_pct": zero_return_pct,
        "calendar_coverage_pct": coverage_pct,
        "longest_gap_days": longest_gap_days,
        "volume_available_pct": volume_available_pct,
        "native_ohlc_rows": native_ohlc_rows,
        "native_ohlc_pct": native_ohlc_pct,
        "forward_fill_risk": coverage_pct < 90 or longest_gap_days > 10 or zero_return_pct > 15,
        "status": status,
        "warnings": ", ".join(warnings),
        "error": "",
    }


def _load_asset_audit_frame(engine, asset_cfg):
    table_name = asset_cfg["table_name"]
    columns = data_access_service.get_table_columns(engine, table_name)
    date_column = data_access_service.detect_column(
        columns,
        ["snapped_at", "date", "datetime", "timestamp"],
    )
    price_column = data_access_service.detect_column(
        columns,
        ["price", "close", "adj_close", "value"],
    )

    if date_column is None or price_column is None:
        raise ValueError("Missing recognized date or price column")

    selected = [date_column, price_column]
    for candidate in ["open", "high", "low", "close", "total_volume", "volume"]:
        actual = data_access_service.detect_column(columns, [candidate])
        if actual and actual not in selected:
            selected.append(actual)

    select_clause = ", ".join(f"`{column}`" for column in selected)
    query = f"SELECT {select_clause} FROM `{table_name}` ORDER BY `{date_column}`"
    frame = pd.read_sql(query, engine)

    frame = frame.rename(columns={date_column: "snapped_at"})
    if price_column != "price":
        frame["price"] = frame[price_column]
    return frame


def run_asset_audit(engine, assets_config, as_of=None):
    rows = []
    frames = {}

    for asset_key, asset_cfg in assets_config.items():
        try:
            frame = _load_asset_audit_frame(engine, asset_cfg)
            coverage_frame = frame[["snapped_at", "price"]].copy()
            coverage_frame["snapped_at"] = pd.to_datetime(
                coverage_frame["snapped_at"],
                errors="coerce",
            )
            coverage_frame["price"] = pd.to_numeric(
                coverage_frame["price"],
                errors="coerce",
            )
            coverage_frame = coverage_frame.dropna(subset=["snapped_at", "price"])
            coverage_frame = coverage_frame[np.isfinite(coverage_frame["price"])]
            if asset_cfg.get("positive_values_expected", True):
                coverage_frame = coverage_frame[coverage_frame["price"] > 0]
            frames[asset_key] = coverage_frame
            rows.append(audit_asset_frame(asset_key, asset_cfg, frame, as_of=as_of))
        except Exception as exc:
            rows.append(
                {
                    "asset": asset_key,
                    "table": asset_cfg.get("table_name"),
                    "asset_class": asset_cfg.get("asset_class"),
                    "status": "ERROR",
                    "warnings": "load_failed",
                    "error": str(exc),
                }
            )

    return pd.DataFrame(rows), frames


def build_pair_coverage_audit(asset_frames: dict[str, pd.DataFrame]):
    rows = []

    for asset_a, asset_b in combinations(sorted(asset_frames), 2):
        left = (
            asset_frames[asset_a]
            .sort_values("snapped_at")
            .drop_duplicates("snapped_at", keep="last")
            .rename(columns={"price": asset_a})
        )
        right = (
            asset_frames[asset_b]
            .sort_values("snapped_at")
            .drop_duplicates("snapped_at", keep="last")
            .rename(columns={"price": asset_b})
        )
        left["snapped_at"] = pd.to_datetime(left["snapped_at"], errors="coerce")
        right["snapped_at"] = pd.to_datetime(right["snapped_at"], errors="coerce")
        left = left.dropna(subset=["snapped_at"])
        right = right.dropna(subset=["snapped_at"])
        merged = pd.merge(left, right, on="snapped_at", how="inner")
        merged[asset_a] = pd.to_numeric(merged[asset_a], errors="coerce")
        merged[asset_b] = pd.to_numeric(merged[asset_b], errors="coerce")
        merged = merged.dropna(subset=[asset_a, asset_b]).sort_values("snapped_at")
        merged = merged[
            np.isfinite(merged[asset_a])
            & np.isfinite(merged[asset_b])
        ]

        returns = (
            merged[[asset_a, asset_b]]
            .pct_change(fill_method=None)
            .replace([np.inf, -np.inf], np.nan)
            .dropna()
        )
        observations = len(returns)
        correlation = returns[asset_a].corr(returns[asset_b]) if observations >= 2 else np.nan
        smaller_series = min(len(left), len(right))
        overlap_pct = _safe_percentage(len(merged), smaller_series)

        rows.append(
            {
                "asset_a": asset_a,
                "asset_b": asset_b,
                "same_date_prices": len(merged),
                "return_observations": observations,
                "overlap_pct_of_smaller_series": overlap_pct,
                "full_period_correlation": correlation,
                "potential_bias": observations < 90 or overlap_pct < 70,
            }
        )

    return pd.DataFrame(rows)


def audit_event_coverage(engine, asset_frames: dict[str, pd.DataFrame]):
    def exists(table_name):
        return data_access_service.table_exists(engine, table_name)

    def columns(table_name):
        return data_access_service.get_table_columns(engine, table_name)

    events = data_access_service.load_asset_events(
        load_events_from_table_func=lambda table_name, start_date=None, end_date=None: (
            data_access_service.load_events_from_table(
                engine=engine,
                table_name=table_name,
                start_date=start_date,
                end_date=end_date,
                table_exists_func=exists,
                get_table_columns_func=columns,
            )
        )
    )

    if events.empty:
        return pd.DataFrame()

    rows = []
    for _, event in events.iterrows():
        event_date = pd.to_datetime(event["event_date"], errors="coerce")
        covered = 0
        for frame in asset_frames.values():
            dates = pd.to_datetime(frame["snapped_at"], errors="coerce").dropna().sort_values()
            future = dates[dates >= event_date]
            if not future.empty and int((future.iloc[0] - event_date).days) <= 7:
                covered += 1

        rows.append(
            {
                "event_date": event_date.date() if pd.notna(event_date) else None,
                "event_title": event.get("event_title"),
                "event_source": event.get("event_source_table"),
                "date_precision": event.get("date_precision", "exact"),
                "assets_with_7d_coverage": covered,
                "assets_total": len(asset_frames),
                "coverage_pct": _safe_percentage(covered, len(asset_frames)),
                "daily_event_study_eligible": event.get("date_precision", "exact") == "exact",
            }
        )

    return pd.DataFrame(rows)


def build_audit_summary(audit_tables: dict[str, pd.DataFrame]):
    asset_audit = audit_tables.get("asset_audit", pd.DataFrame())
    pair_audit = audit_tables.get("correlation_coverage", pd.DataFrame())
    event_audit = audit_tables.get("event_coverage", pd.DataFrame())

    return {
        "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
        "scope": "Aggregated read-only data quality audit",
        "asset_count": len(asset_audit),
        "assets_ok": int(asset_audit.get("status", pd.Series(dtype=str)).eq("OK").sum()),
        "assets_warning": int(asset_audit.get("status", pd.Series(dtype=str)).eq("WARNING").sum()),
        "assets_error": int(asset_audit.get("status", pd.Series(dtype=str)).eq("ERROR").sum()),
        "correlation_pairs": len(pair_audit),
        "potentially_biased_pairs": int(
            pair_audit.get("potential_bias", pd.Series(dtype=bool)).fillna(False).sum()
        ),
        "events": len(event_audit),
        "approximate_events": int(
            event_audit.get("date_precision", pd.Series(dtype=str)).ne("exact").sum()
        ),
    }


def build_audit_zip_bytes(audit_tables: dict[str, pd.DataFrame]):
    summary = build_audit_summary(audit_tables)
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("audit_summary.json", json.dumps(summary, indent=2, default=str))
        for name, frame in audit_tables.items():
            archive.writestr(f"{name}.csv", frame.to_csv(index=False))

    return buffer.getvalue()
