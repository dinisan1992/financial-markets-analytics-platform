from __future__ import annotations

import io
import json
import zipfile
from datetime import date
from itertools import combinations

import numpy as np
import pandas as pd

from services import data_access_service
from services.correlation_quality_service import (
    calculate_pair_correlation,
    classify_correlation_confidence,
    correlation_confidence_interval,
)


STALE_LIMITS = {
    "continuous": 5,
    "trading_days": 10,
    "weekly": 21,
    "monthly": 62,
}


def _safe_percentage(numerator, denominator):
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 2)


def _longest_calendar_gap(dates: pd.Series):
    unique_dates = pd.Series(pd.to_datetime(dates, errors="coerce").dropna().unique()).sort_values()
    if len(unique_dates) < 2:
        return 0
    return int(unique_dates.diff().dt.days.max())


def _date_group_diagnostics(frame: pd.DataFrame, date_column: str):
    group_sizes = frame.dropna(subset=[date_column]).groupby(date_column).size()
    duplicate_groups = group_sizes[group_sizes > 1]
    if duplicate_groups.empty:
        return 0, None, None, 0
    return (
        len(duplicate_groups),
        duplicate_groups.index.min().date(),
        duplicate_groups.index.max().date(),
        int(duplicate_groups.max()),
    )


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
    (
        duplicate_date_groups,
        first_duplicate_date,
        last_duplicate_date,
        max_rows_per_date,
    ) = _date_group_diagnostics(output, date_column)

    finite_mask = pd.Series(
        np.isfinite(output[price_column].to_numpy(dtype=float)),
        index=output.index,
    )
    non_finite_mask = output[price_column].notna() & ~finite_mask
    zero_price_mask = finite_mask & output[price_column].eq(0)
    negative_price_mask = finite_mask & output[price_column].lt(0)
    negative_values_possible = asset_cfg.get("negative_values_possible", False)

    invalid_mask = non_finite_mask.copy()
    price_review_mask = pd.Series(False, index=output.index)
    if asset_cfg.get("positive_values_expected", True):
        invalid_mask |= zero_price_mask
        if negative_values_possible:
            price_review_mask = negative_price_mask
        else:
            invalid_mask |= negative_price_mask

    invalid_prices = int(invalid_mask.fillna(False).sum())
    prices_requiring_review = int(price_review_mask.fillna(False).sum())
    missing_dates = int(output[date_column].isna().sum())
    missing_prices = int(output[price_column].isna().sum())

    invalid_dates = output.loc[invalid_mask & output[date_column].notna(), date_column]
    review_dates = output.loc[price_review_mask & output[date_column].notna(), date_column]

    valid = output.dropna(subset=[date_column, price_column]).copy()
    valid = valid[np.isfinite(valid[price_column])]
    if asset_cfg.get("positive_values_expected", True):
        if negative_values_possible:
            valid = valid[valid[price_column] != 0]
        else:
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

    stale_limit = STALE_LIMITS.get(asset_cfg.get("calendar_type"), 10)
    days_overdue = max(stale_days - stale_limit, 0) if stale_days is not None else None
    warnings = []
    if duplicate_dates:
        warnings.append("duplicate_dates")
    if invalid_prices:
        warnings.append("invalid_prices")
    if prices_requiring_review:
        warnings.append("non_positive_price_review")
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
        "stale_limit_days": stale_limit,
        "days_overdue": days_overdue,
        "freshness_status": (
            "UNKNOWN" if days_overdue is None else "CURRENT" if days_overdue == 0 else "STALE"
        ),
        "duplicate_dates": duplicate_dates,
        "duplicate_date_groups": duplicate_date_groups,
        "first_duplicate_date": first_duplicate_date,
        "last_duplicate_date": last_duplicate_date,
        "max_rows_per_date": max_rows_per_date,
        "missing_dates": missing_dates,
        "missing_prices": missing_prices,
        "invalid_prices": invalid_prices,
        "first_invalid_date": invalid_dates.min().date() if not invalid_dates.empty else None,
        "last_invalid_date": invalid_dates.max().date() if not invalid_dates.empty else None,
        "prices_requiring_review": prices_requiring_review,
        "first_review_date": review_dates.min().date() if not review_dates.empty else None,
        "last_review_date": review_dates.max().date() if not review_dates.empty else None,
        "zero_return_pct": zero_return_pct,
        "calendar_coverage_pct": coverage_pct,
        "longest_gap_days": longest_gap_days,
        "volume_available_pct": volume_available_pct,
        "native_ohlc_rows": native_ohlc_rows,
        "native_ohlc_pct": native_ohlc_pct,
        "source_type": asset_cfg.get("source_type", "configured_pipeline"),
        "source_provider": asset_cfg.get("source_provider", ""),
        "source_identifier": asset_cfg.get("source_identifier", ""),
        "source_identity_status": asset_cfg.get("source_identity_status", "unknown"),
        "source_reference": asset_cfg.get("source_reference", ""),
        "updater_script": asset_cfg.get("script_name", ""),
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
                if asset_cfg.get("negative_values_possible", False):
                    coverage_frame = coverage_frame[coverage_frame["price"] != 0]
                else:
                    coverage_frame = coverage_frame[coverage_frame["price"] > 0]
            frames[asset_key] = coverage_frame
            rows.append(audit_asset_frame(asset_key, asset_cfg, frame, as_of=as_of))
        except Exception as exc:
            rows.append(
                {
                    "asset": asset_key,
                    "table": asset_cfg.get("table_name"),
                    "asset_class": asset_cfg.get("asset_class"),
                    "source_provider": asset_cfg.get("source_provider", ""),
                    "source_identifier": asset_cfg.get("source_identifier", ""),
                    "source_identity_status": asset_cfg.get(
                        "source_identity_status", "unknown"
                    ),
                    "status": "ERROR",
                    "warnings": "load_failed",
                    "error": str(exc),
                }
            )

    return pd.DataFrame(rows), frames


def _prepare_asset_return_frame(frame: pd.DataFrame, asset_key: str):
    data = frame[["snapped_at", "price"]].copy()
    data["snapped_at"] = pd.to_datetime(data["snapped_at"], errors="coerce")
    data["price"] = pd.to_numeric(data["price"], errors="coerce")
    data = data.replace([np.inf, -np.inf], np.nan).dropna()
    data = data.sort_values("snapped_at").drop_duplicates("snapped_at", keep="last")
    data[asset_key] = data["price"].pct_change(fill_method=None)
    return data[["snapped_at", asset_key]].dropna(subset=[asset_key])


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
        price_overlap = pd.merge(left, right, on="snapped_at", how="inner")
        left_returns = _prepare_asset_return_frame(asset_frames[asset_a], asset_a)
        right_returns = _prepare_asset_return_frame(asset_frames[asset_b], asset_b)
        returns = pd.merge(left_returns, right_returns, on="snapped_at", how="inner")
        returns = returns.replace([np.inf, -np.inf], np.nan).dropna()

        observations = len(returns)
        correlation = calculate_pair_correlation(returns[asset_a], returns[asset_b])
        smaller_return_sample = min(len(left_returns), len(right_returns))
        overlap_ratio = observations / smaller_return_sample if smaller_return_sample else 0.0
        overlap_pct = round(overlap_ratio * 100, 2)
        confidence = (
            "INSUFFICIENT"
            if pd.isna(correlation)
            else classify_correlation_confidence(observations, overlap_pct)
        )
        ci_low, ci_high = correlation_confidence_interval(correlation, observations)

        rows.append(
            {
                "asset_a": asset_a,
                "asset_b": asset_b,
                "same_date_prices": len(price_overlap),
                "return_observations": observations,
                "common_start_date": returns["snapped_at"].min().date() if observations else None,
                "common_end_date": returns["snapped_at"].max().date() if observations else None,
                "coverage_ratio": round(overlap_ratio, 4),
                "overlap_pct_of_smaller_series": overlap_pct,
                "full_period_correlation": correlation,
                "correlation_ci95_low": ci_low,
                "correlation_ci95_high": ci_high,
                "correlation_confidence": confidence,
                "potential_bias": confidence in {"INSUFFICIENT", "LOW"},
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


def build_freshness_report(asset_audit: pd.DataFrame):
    """Build an operational view of when and how each asset should be refreshed."""
    columns = [
        "asset",
        "table",
        "last_date",
        "stale_days",
        "stale_limit_days",
        "days_overdue",
        "freshness_status",
        "source_type",
        "source_provider",
        "source_identifier",
        "source_identity_status",
        "source_reference",
        "updater_script",
    ]
    if asset_audit.empty:
        return pd.DataFrame(columns=columns)

    report = asset_audit.reindex(columns=columns).copy()
    report["days_overdue"] = pd.to_numeric(report["days_overdue"], errors="coerce")
    return report.sort_values(
        ["days_overdue", "asset"],
        ascending=[False, True],
        na_position="first",
    ).reset_index(drop=True)


def build_remediation_report(asset_audit: pd.DataFrame):
    """Translate audit flags into explicit, non-destructive remediation tasks."""
    columns = [
        "priority",
        "asset",
        "table",
        "issue",
        "evidence",
        "recommended_action",
        "updater_script",
    ]
    if asset_audit.empty:
        return pd.DataFrame(columns=columns)

    issue_config = {
        "load_failed": (
            "P0",
            lambda row: row.get("error", "Asset could not be loaded"),
            "Repair the loader or table mapping, then rerun the read-only audit.",
        ),
        "duplicate_dates": (
            "P1",
            lambda row: (
                f"{int(row.get('duplicate_dates', 0) or 0)} extra rows across "
                f"{int(row.get('duplicate_date_groups', 0) or 0)} dates"
            ),
            "Inspect duplicate groups and define a keep rule after backup and dry-run.",
        ),
        "invalid_prices": (
            "P1",
            lambda row: f"{int(row.get('invalid_prices', 0) or 0)} invalid values",
            "Validate source, units and parsing before changing any stored value.",
        ),
        "non_positive_price_review": (
            "P1",
            lambda row: (
                f"{int(row.get('prices_requiring_review', 0) or 0)} non-positive values; "
                f"first date {row.get('first_review_date') or '-'}"
            ),
            "Validate against the upstream source; WTI can legitimately be negative.",
        ),
        "stale_data": (
            "P2",
            lambda row: f"{int(row.get('days_overdue', 0) or 0)} days beyond freshness limit",
            "Run the configured updater asset-by-asset and verify row count and max date.",
        ),
        "missing_core_values": (
            "P2",
            lambda row: (
                f"{int(row.get('missing_dates', 0) or 0)} missing dates; "
                f"{int(row.get('missing_prices', 0) or 0)} missing prices"
            ),
            "Trace missing core values to the source and importer before remediation.",
        ),
        "low_calendar_coverage": (
            "P3",
            lambda row: f"{float(row.get('calendar_coverage_pct', 0) or 0):.2f}% coverage",
            "Validate the configured calendar and source frequency; avoid blanket forward-fill.",
        ),
        "excess_zero_returns": (
            "P3",
            lambda row: f"{float(row.get('zero_return_pct', 0) or 0):.2f}% zero returns",
            "Confirm native frequency and repeated source values before modifying the series.",
        ),
        "volume_unavailable": (
            "P3",
            lambda row: f"{float(row.get('volume_available_pct', 0) or 0):.2f}% volume coverage",
            "Confirm whether the upstream instrument exposes meaningful volume.",
        ),
    }

    rows = []
    for _, row in asset_audit.iterrows():
        warnings = [item.strip() for item in str(row.get("warnings", "")).split(",")]
        for issue in filter(None, warnings):
            if issue not in issue_config:
                continue
            priority, evidence_builder, action = issue_config[issue]
            rows.append(
                {
                    "priority": priority,
                    "asset": row.get("asset"),
                    "table": row.get("table"),
                    "issue": issue,
                    "evidence": evidence_builder(row),
                    "recommended_action": action,
                    "updater_script": row.get("updater_script", ""),
                }
            )

    return pd.DataFrame(rows, columns=columns).sort_values(
        ["priority", "asset", "issue"]
    ).reset_index(drop=True)


def build_audit_summary(audit_tables: dict[str, pd.DataFrame]):
    asset_audit = audit_tables.get("asset_audit", pd.DataFrame())
    pair_audit = audit_tables.get("correlation_coverage", pd.DataFrame())
    event_audit = audit_tables.get("event_coverage", pd.DataFrame())
    euro_sync_status = audit_tables.get("euro_sync_status", pd.DataFrame())
    euro_statuses = euro_sync_status.get("status", pd.Series(dtype=str))

    return {
        "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
        "scope": "Aggregated read-only data quality audit",
        "asset_count": len(asset_audit),
        "assets_ok": int(asset_audit.get("status", pd.Series(dtype=str)).eq("OK").sum()),
        "assets_warning": int(asset_audit.get("status", pd.Series(dtype=str)).eq("WARNING").sum()),
        "assets_error": int(asset_audit.get("status", pd.Series(dtype=str)).eq("ERROR").sum()),
        "stale_assets": int(
            asset_audit.get("freshness_status", pd.Series(dtype=str)).eq("STALE").sum()
        ),
        "assets_with_duplicates": int(
            pd.to_numeric(
                asset_audit.get("duplicate_dates", pd.Series(dtype=float)),
                errors="coerce",
            ).fillna(0).gt(0).sum()
        ),
        "assets_with_invalid_prices": int(
            pd.to_numeric(
                asset_audit.get("invalid_prices", pd.Series(dtype=float)),
                errors="coerce",
            ).fillna(0).gt(0).sum()
        ),
        "assets_requiring_price_review": int(
            pd.to_numeric(
                asset_audit.get("prices_requiring_review", pd.Series(dtype=float)),
                errors="coerce",
            ).fillna(0).gt(0).sum()
        ),
        "correlation_pairs": len(pair_audit),
        "potentially_biased_pairs": int(
            pair_audit.get("potential_bias", pd.Series(dtype=bool)).fillna(False).sum()
        ),
        "events": len(event_audit),
        "approximate_events": int(
            event_audit.get("date_precision", pd.Series(dtype=str)).ne("exact").sum()
        ),
        "euro_contracts": len(euro_sync_status),
        "euro_exact": int(euro_statuses.eq("EXACT").sum()),
        "euro_changes": int(euro_statuses.eq("CHANGES").sum()),
        "euro_blocked": int(euro_statuses.eq("BLOCKED").sum()),
        "euro_not_audited": int(euro_statuses.eq("NOT_AUDITED").sum()),
        "euro_plan_database_writes": int(
            euro_sync_status.get(
                "database_write_performed",
                pd.Series(dtype=bool),
            ).fillna(False).sum()
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
