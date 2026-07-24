from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd

from euro_series_config import EURO_SERIES, EURO_SERIES_GROUPS, EURO_MARKET_PAIRS
from euro_data_loader import get_engine, load_euro_series
from asset_config import ASSETS


# =========================
# SETTINGS
# =========================

OUTPUT_SERIES_VALIDATION = "euro_series_validation_report.csv"
OUTPUT_GROUP_VALIDATION = "euro_series_group_validation_report.csv"
OUTPUT_PAIR_VALIDATION = "euro_market_pair_validation_report.csv"

MIN_OBSERVATIONS_MONTHLY = 120
MIN_OBSERVATIONS_SEMIANNUAL = 4


# =========================
# SERIES VALIDATION
# =========================

def validar_serie(series_key, cfg, engine):
    row = {
        "series_key": series_key,
        "display_name": cfg.get("display_name"),
        "category": cfg.get("category"),
        "region": cfg.get("region"),
        "frequency": cfg.get("frequency"),
        "table_name": cfg.get("table_name"),
        "key_code": cfg.get("key_code"),
        "unit": cfg.get("unit"),
        "enabled": cfg.get("enabled", True),
        "base100_recommended": cfg.get("base100_recommended"),
        "observations": None,
        "min_date": None,
        "max_date": None,
        "first_value": None,
        "last_value": None,
        "min_value": None,
        "max_value": None,
        "null_pct": None,
        "status": "UNKNOWN",
        "issues": ""
    }

    try:
        if cfg.get("enabled", True) is not True:
            row["status"] = "SKIPPED"
            row["issues"] = "disabled"
            return row

        df = load_euro_series(
            series_key=series_key,
            engine=engine,
            start_date=None,
            end_date=None
        )

        if df.empty:
            row["status"] = "ERRORR"
            row["issues"] = "empty_series"
            return row

        value_col = series_key

        observations = len(df)
        null_pct = round(df[value_col].isna().mean() * 100, 2)

        row["observations"] = observations
        row["min_date"] = df["snapped_at"].min().date()
        row["max_date"] = df["snapped_at"].max().date()
        row["first_value"] = df[value_col].dropna().iloc[0]
        row["last_value"] = df[value_col].dropna().iloc[-1]
        row["min_value"] = df[value_col].min()
        row["max_value"] = df[value_col].max()
        row["null_pct"] = null_pct

        issues = []

        frequency = cfg.get("frequency")

        if frequency == "monthly" and observations < MIN_OBSERVATIONS_MONTHLY:
            issues.append(f"low_observations_monthly_{observations}")

        if frequency == "semiannual" and observations < MIN_OBSERVATIONS_SEMIANNUAL:
            issues.append(f"low_observations_semiannual_{observations}")

        if null_pct > 5:
            issues.append(f"high_null_pct_{null_pct}")

        if row["min_value"] == row["max_value"]:
            issues.append("constant_series")

        if issues:
            row["status"] = "WARNING"
            row["issues"] = " | ".join(issues)
        else:
            row["status"] = "OK"
            row["issues"] = "OK"

    except Exception as e:
        row["status"] = "ERRORR"
        row["issues"] = str(e)

    return row


def validar_todas_series(engine):
    rows = []

    for idx, (series_key, cfg) in enumerate(EURO_SERIES.items(), start=1):
        print("\n" + "=" * 120)
        print(f"[{idx}/{len(EURO_SERIES)}] Validar series: {series_key}")
        print("=" * 120)

        row = validar_serie(
            series_key=series_key,
            cfg=cfg,
            engine=engine
        )

        rows.append(row)

        print(
            f"{series_key} | status={row['status']} | "
            f"obs={row['observations']} | "
            f"{row['min_date']} -> {row['max_date']} | "
            f"issues={row['issues']}"
        )

    return pd.DataFrame(rows)


# =========================
# GROUP VALIDATION
# =========================

def validar_grupos(series_report_df):
    rows = []

    for group_name, series_keys in EURO_SERIES_GROUPS.items():
        missing = [
            key for key in series_keys
            if key not in EURO_SERIES
        ]

        statuses = []

        for key in series_keys:
            if key in series_report_df["series_key"].values:
                status = series_report_df.loc[
                    series_report_df["series_key"] == key,
                    "status"
                ].iloc[0]

                statuses.append(status)

        if missing:
            status = "ERRORR"
            issues = f"missing_series: {missing}"
        elif any(s == "ERRORR" for s in statuses):
            status = "ERRORR"
            issues = "one_or_more_series_error"
        elif any(s == "WARNING" for s in statuses):
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
            "issues": issues
        })

    return pd.DataFrame(rows)


# =========================
# PAIR VALIDATION
# =========================

def validar_pares():
    rows = []

    for pair_key, cfg in EURO_MARKET_PAIRS.items():
        euro_series = cfg.get("euro_series")
        market_asset = cfg.get("market_asset")

        issues = []

        if euro_series not in EURO_SERIES:
            issues.append(f"euro_series_not_found: {euro_series}")

        if market_asset not in ASSETS:
            issues.append(f"market_asset_not_found: {market_asset}")

        if issues:
            status = "ERRORR"
        else:
            status = "OK"
            issues = ["OK"]

        rows.append({
            "pair_key": pair_key,
            "label": cfg.get("label"),
            "euro_series": euro_series,
            "market_asset": market_asset,
            "status": status,
            "issues": " | ".join(issues)
        })

    return pd.DataFrame(rows)


# =========================
# MAIN
# =========================

def main():
    print("\nA iniciar Euro Series Validator...")
    print(f"Series configuradas: {len(EURO_SERIES)}")
    print(f"Groups configurados: {len(EURO_SERIES_GROUPS)}")
    print(f"Pares market configurados: {len(EURO_MARKET_PAIRS)}")

    engine = get_engine()

    series_report_df = validar_todas_series(engine)

    group_report_df = validar_grupos(series_report_df)

    pair_report_df = validar_pares()

    series_report_df.to_csv(
        OUTPUT_SERIES_VALIDATION,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    group_report_df.to_csv(
        OUTPUT_GROUP_VALIDATION,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    pair_report_df.to_csv(
        OUTPUT_PAIR_VALIDATION,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nReports exported:")
    print(OUTPUT_SERIES_VALIDATION)
    print(OUTPUT_GROUP_VALIDATION)
    print(OUTPUT_PAIR_VALIDATION)

    print("\n" + "=" * 120)
    print("SERIES SUMMARY")
    print("=" * 120)
    print(
        series_report_df["status"]
        .value_counts(dropna=False)
        .rename_axis("status")
        .reset_index(name="count")
    )

    print("\n" + "=" * 120)
    print("SUMMARY GROUPS")
    print("=" * 120)
    print(group_report_df)

    print("\n" + "=" * 120)
    print("SUMMARY PARES")
    print("=" * 120)
    print(
        pair_report_df["status"]
        .value_counts(dropna=False)
        .rename_axis("status")
        .reset_index(name="count")
    )

    print("\nEuro Series Validator completed.")


if __name__ == "__main__":
    main()

