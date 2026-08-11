from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_config import ASSETS
from euro_data_loader import get_engine, load_euro_series
from euro_series_config import (
    EURO_MARKET_PAIRS,
    EURO_SERIES,
    EURO_SERIES_GROUPS,
)


SERIES_REPORT = "euro_series_validation_report.csv"
GROUP_REPORT = "euro_series_group_validation_report.csv"
PAIR_REPORT = "euro_market_pair_validation_report.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "euro_series_validation"
MIN_OBSERVATIONS_MONTHLY = 120
MIN_OBSERVATIONS_SEMIANNUAL = 4


def validate_series(series_key, config, engine):
    row = {
        "series_key": series_key,
        "display_name": config.get("display_name"),
        "category": config.get("category"),
        "region": config.get("region"),
        "frequency": config.get("frequency"),
        "table_name": config.get("table_name"),
        "key_code": config.get("key_code"),
        "unit": config.get("unit"),
        "enabled": config.get("enabled", True),
        "base100_recommended": config.get("base100_recommended"),
        "observations": None,
        "min_date": None,
        "max_date": None,
        "first_value": None,
        "last_value": None,
        "min_value": None,
        "max_value": None,
        "null_pct": None,
        "status": "UNKNOWN",
        "issues": "",
    }

    try:
        if config.get("enabled", True) is not True:
            row["status"] = "SKIPPED"
            row["issues"] = "disabled"
            return row

        frame = load_euro_series(
            series_key=series_key,
            engine=engine,
            start_date=None,
            end_date=None,
        )
        if frame.empty:
            row["status"] = "ERROR"
            row["issues"] = "empty_series"
            return row

        values = frame[series_key]
        available = values.dropna()
        observations = len(frame)
        null_pct = round(values.isna().mean() * 100, 2)
        row.update({
            "observations": observations,
            "min_date": frame["snapped_at"].min().date(),
            "max_date": frame["snapped_at"].max().date(),
            "first_value": available.iloc[0] if not available.empty else None,
            "last_value": available.iloc[-1] if not available.empty else None,
            "min_value": values.min(),
            "max_value": values.max(),
            "null_pct": null_pct,
        })

        issues = []
        frequency = config.get("frequency")
        if frequency == "monthly" and observations < MIN_OBSERVATIONS_MONTHLY:
            issues.append(f"low_observations_monthly_{observations}")
        if (
            frequency == "semiannual"
            and observations < MIN_OBSERVATIONS_SEMIANNUAL
        ):
            issues.append(f"low_observations_semiannual_{observations}")
        if null_pct > 5:
            issues.append(f"high_null_pct_{null_pct}")
        if available.empty:
            issues.append("no_non_null_values")
        elif row["min_value"] == row["max_value"]:
            issues.append("constant_series")

        row["status"] = "WARNING" if issues else "OK"
        row["issues"] = " | ".join(issues) if issues else "OK"
    except Exception as exc:
        row["status"] = "ERROR"
        row["issues"] = str(exc)
    return row


def validate_all_series(engine):
    rows = []
    for index, (series_key, config) in enumerate(EURO_SERIES.items(), start=1):
        print("\n" + "=" * 100)
        print(f"[{index}/{len(EURO_SERIES)}] Validating series: {series_key}")
        print("=" * 100)
        row = validate_series(series_key, config, engine)
        rows.append(row)
        print(
            f"{series_key} | status={row['status']} | "
            f"observations={row['observations']} | "
            f"{row['min_date']} -> {row['max_date']} | "
            f"issues={row['issues']}"
        )
    return pd.DataFrame(rows)


def validate_groups(series_report):
    rows = []
    for group_name, series_keys in EURO_SERIES_GROUPS.items():
        missing = [key for key in series_keys if key not in EURO_SERIES]
        statuses = [
            series_report.loc[
                series_report["series_key"] == key,
                "status",
            ].iloc[0]
            for key in series_keys
            if key in series_report["series_key"].values
        ]
        if missing:
            status = "ERROR"
            issues = f"missing_series: {missing}"
        elif any(value == "ERROR" for value in statuses):
            status = "ERROR"
            issues = "one_or_more_series_error"
        elif any(value == "WARNING" for value in statuses):
            status = "WARNING"
            issues = "one_or_more_series_warning"
        else:
            status = "OK"
            issues = "OK"
        rows.append({
            "group_name": group_name,
            "series_count": len(series_keys),
            "missing_series": ", ".join(missing),
            "statuses": ", ".join(statuses),
            "status": status,
            "issues": issues,
        })
    return pd.DataFrame(rows)


def validate_pairs():
    rows = []
    for pair_key, config in EURO_MARKET_PAIRS.items():
        euro_series = config.get("euro_series")
        market_asset = config.get("market_asset")
        issues = []
        if euro_series not in EURO_SERIES:
            issues.append(f"euro_series_not_found: {euro_series}")
        if market_asset not in ASSETS:
            issues.append(f"market_asset_not_found: {market_asset}")
        rows.append({
            "pair_key": pair_key,
            "label": config.get("label"),
            "euro_series": euro_series,
            "market_asset": market_asset,
            "status": "ERROR" if issues else "OK",
            "issues": " | ".join(issues) if issues else "OK",
        })
    return pd.DataFrame(rows)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Validate configured EURO series, groups and market pairs."
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Return exit code 2 when a series, group or pair has ERROR status.",
    )
    return parser


def _write_report(frame, output_dir, filename):
    path = output_dir / filename
    frame.to_csv(path, index=False, sep=";", encoding="utf-8-sig")
    return path


def main(argv=None):
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    print("Starting EURO Series Validator...")
    print(f"Configured series: {len(EURO_SERIES)}")
    print(f"Configured groups: {len(EURO_SERIES_GROUPS)}")
    print(f"Configured market pairs: {len(EURO_MARKET_PAIRS)}")
    print("Database writes: disabled")

    engine = get_engine()
    try:
        series_report = validate_all_series(engine)
    finally:
        engine.dispose()
    group_report = validate_groups(series_report)
    pair_report = validate_pairs()
    reports = (
        _write_report(series_report, output_dir, SERIES_REPORT),
        _write_report(group_report, output_dir, GROUP_REPORT),
        _write_report(pair_report, output_dir, PAIR_REPORT),
    )

    print("\nReports exported:")
    for report in reports:
        print(report)
    print("\nSeries summary:")
    print(series_report["status"].value_counts(dropna=False))
    print("\nGroup summary:")
    print(group_report["status"].value_counts(dropna=False))
    print("\nMarket-pair summary:")
    print(pair_report["status"].value_counts(dropna=False))

    has_error = any(
        "ERROR" in set(frame["status"])
        for frame in (series_report, group_report, pair_report)
    )
    print("EURO Series Validator completed.")
    return 2 if args.fail_on_error and has_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
