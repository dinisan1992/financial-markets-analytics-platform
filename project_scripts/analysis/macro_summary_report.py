from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd

from macro_config import MACRO_ASSETS, MACRO_GROUPS
from macro_data_loader import (
    get_engine,
    load_macro
)


# =========================
# SETTINGS
# =========================

START_DATE = None
END_DATE = None

EXPORT_REPORT = True

OUTPUT_FILE = "macro_summary_report.csv"
GROUP_OUTPUT_FILE = "macro_group_summary_report.csv"


# =========================
# CALCULATIONS
# =========================

def calcular_zscore_252d(series):
    rolling_mean = series.rolling(252, min_periods=60).mean()
    rolling_std = series.rolling(252, min_periods=60).std()

    zscore = (series - rolling_mean) / rolling_std

    return zscore


def classificar_zscore(z):
    if pd.isna(z):
        return "insufficient_data"

    if z >= 2:
        return "very_high"

    if z >= 1:
        return "high"

    if z <= -2:
        return "very_low"

    if z <= -1:
        return "low"

    return "normal"


def classificar_tendencia(change_90d, change_252d):
    if change_90d is None or pd.isna(change_90d):
        return "unknown"

    if change_252d is None or pd.isna(change_252d):
        if change_90d > 0:
            return "rising_short_term"

        if change_90d < 0:
            return "falling_short_term"

        return "flat"

    if change_90d > 0 and change_252d > 0:
        return "rising"

    if change_90d < 0 and change_252d < 0:
        return "falling"

    if change_90d > 0 and change_252d < 0:
        return "short_term_rebound"

    if change_90d < 0 and change_252d > 0:
        return "short_term_cooling"

    return "flat"


def safe_pct_change(series, periods):
    clean_series = series.dropna()

    if len(clean_series) <= periods:
        return None

    value_now = clean_series.iloc[-1]
    value_past = clean_series.iloc[-(periods + 1)]

    if pd.isna(value_now) or pd.isna(value_past):
        return None

    if value_past == 0:
        return None

    return ((value_now / value_past) - 1) * 100


def safe_abs_change(series, periods):
    clean_series = series.dropna()

    if len(clean_series) <= periods:
        return None

    value_now = clean_series.iloc[-1]
    value_past = clean_series.iloc[-(periods + 1)]

    if pd.isna(value_now) or pd.isna(value_past):
        return None

    return value_now - value_past


# =========================
# MACRO FLAGS
# =========================

def gerar_macro_flag(
    category,
    zscore_regime,
    trend_regime,
    change_90d_abs,
    change_252d_abs
):
    category = str(category).lower()

    if zscore_regime in ["very_high", "high"]:
        if category in ["stress", "consumer_stress", "credit"]:
            return "stress_elevated"

        if category in ["rates"]:
            return "rates_elevated"

        if category in ["inflation"]:
            return "inflation_elevated"

        if category in ["liquidity"]:
            return "liquidity_above_trend"

        if category in ["banking"]:
            return "banking_above_trend"

        if category in ["consumer_credit"]:
            return "consumer_credit_above_trend"

        return "above_trend"

    if zscore_regime in ["very_low", "low"]:
        if category in ["liquidity"]:
            return "liquidity_below_trend"

        if category in ["stress", "consumer_stress"]:
            return "stress_low"

        if category in ["rates"]:
            return "rates_low"

        if category in ["banking"]:
            return "banking_below_trend"

        if category in ["consumer_credit"]:
            return "consumer_credit_below_trend"

        return "below_trend"

    if trend_regime == "rising":
        if category in ["stress", "consumer_stress"]:
            return "stress_rising"

        if category in ["rates"]:
            return "rates_rising"

        if category in ["liquidity"]:
            return "liquidity_expanding"

        if category in ["credit", "consumer_credit"]:
            return "credit_expanding"

        if category in ["banking"]:
            return "banking_expanding"

        return "rising"

    if trend_regime == "falling":
        if category in ["stress", "consumer_stress"]:
            return "stress_falling"

        if category in ["rates"]:
            return "rates_falling"

        if category in ["liquidity"]:
            return "liquidity_contracting"

        if category in ["credit", "consumer_credit"]:
            return "credit_contracting"

        if category in ["banking"]:
            return "banking_contracting"

        return "falling"

    return "normal"


# =========================
# SUMMARY INDICADOR
# =========================

def gerar_summary_macro(macro_key, engine):
    cfg = MACRO_ASSETS[macro_key]

    print("\n" + "=" * 120)
    print(f"A resumir indicador macro: {macro_key} | {cfg['display_name']}")
    print("=" * 120)

    result = {
        "macro_key": macro_key,
        "display_name": cfg.get("display_name"),
        "table_name": cfg.get("table_name"),
        "date_col": cfg.get("date_col"),
        "value_col": cfg.get("value_col"),
        "category": cfg.get("category"),
        "region": cfg.get("region"),
        "unit": cfg.get("unit"),
        "enabled": cfg.get("enabled"),
        "needs_filter": cfg.get("needs_filter"),
        "start_date": None,
        "end_date": None,
        "observations": None,
        "first_value": None,
        "latest_value": None,
        "min_value": None,
        "max_value": None,
        "mean_value": None,
        "change_30d_abs": None,
        "change_90d_abs": None,
        "change_252d_abs": None,
        "change_30d_pct": None,
        "change_90d_pct": None,
        "change_252d_pct": None,
        "latest_zscore_252d": None,
        "zscore_regime": None,
        "trend_regime": None,
        "macro_flag": None,
        "status": "OK",
        "error": None
    }

    try:
        df = load_macro(
            macro_key=macro_key,
            engine=engine,
            start_date=START_DATE,
            end_date=END_DATE
        )

        if df.empty:
            result["status"] = "ERRORR"
            result["error"] = "empty_dataframe"
            return result

        df = df.sort_values("snapped_at").reset_index(drop=True)

        series = pd.to_numeric(
            df[macro_key],
            errors="coerce"
        )

        valid_series = series.dropna()

        if valid_series.empty:
            result["status"] = "ERRORR"
            result["error"] = "no_valid_values"
            return result

        zscore = calcular_zscore_252d(series)
        clean_zscore = zscore.dropna()

        latest_zscore = (
            clean_zscore.iloc[-1]
            if not clean_zscore.empty
            else None
        )

        change_30d_abs = safe_abs_change(series, 30)
        change_90d_abs = safe_abs_change(series, 90)
        change_252d_abs = safe_abs_change(series, 252)

        change_30d_pct = safe_pct_change(series, 30)
        change_90d_pct = safe_pct_change(series, 90)
        change_252d_pct = safe_pct_change(series, 252)

        zscore_regime = classificar_zscore(latest_zscore)
        trend_regime = classificar_tendencia(change_90d_abs, change_252d_abs)

        macro_flag = gerar_macro_flag(
            category=cfg.get("category"),
            zscore_regime=zscore_regime,
            trend_regime=trend_regime,
            change_90d_abs=change_90d_abs,
            change_252d_abs=change_252d_abs
        )

        result.update({
            "start_date": df["snapped_at"].min().date(),
            "end_date": df["snapped_at"].max().date(),
            "observations": len(df),
            "first_value": round(valid_series.iloc[0], 4),
            "latest_value": round(valid_series.iloc[-1], 4),
            "min_value": round(valid_series.min(), 4),
            "max_value": round(valid_series.max(), 4),
            "mean_value": round(valid_series.mean(), 4),
            "change_30d_abs": round(change_30d_abs, 4) if change_30d_abs is not None else None,
            "change_90d_abs": round(change_90d_abs, 4) if change_90d_abs is not None else None,
            "change_252d_abs": round(change_252d_abs, 4) if change_252d_abs is not None else None,
            "change_30d_pct": round(change_30d_pct, 2) if change_30d_pct is not None else None,
            "change_90d_pct": round(change_90d_pct, 2) if change_90d_pct is not None else None,
            "change_252d_pct": round(change_252d_pct, 2) if change_252d_pct is not None else None,
            "latest_zscore_252d": round(latest_zscore, 4) if latest_zscore is not None else None,
            "zscore_regime": zscore_regime,
            "trend_regime": trend_regime,
            "macro_flag": macro_flag,
            "status": "OK",
            "error": None
        })

        print(f"Observations: {result['observations']}")
        print(f"Period: {result['start_date']} -> {result['end_date']}")
        print(f"Primeiro valor: {result['first_value']}")
        print(f"Latest value: {result['latest_value']}")
        print(f"Change 30 obs abs: {result['change_30d_abs']}")
        print(f"Change 90 obs abs: {result['change_90d_abs']}")
        print(f"Change 252 obs abs: {result['change_252d_abs']}")
        print(f"Change 30 obs %: {result['change_30d_pct']}")
        print(f"Change 90 obs %: {result['change_90d_pct']}")
        print(f"Change 252 obs %: {result['change_252d_pct']}")
        print(f"Z-score 252 obs: {result['latest_zscore_252d']} | {result['zscore_regime']}")
        print(f"Trend: {result['trend_regime']}")
        print(f"Flag: {result['macro_flag']}")

    except Exception as e:
        result["status"] = "ERRORR"
        result["error"] = str(e)

        print(f"ERROR in {macro_key}: {e}")

    return result


# =========================
# SUMMARY POR GROUP
# =========================

def gerar_summary_grupos(report_df):
    rows = []

    for group_key, group_data in MACRO_GROUPS.items():
        assets = group_data.get("assets", [])

        group_df = report_df[
            report_df["macro_key"].isin(assets)
        ].copy()

        if group_df.empty:
            rows.append({
                "group_key": group_key,
                "group_name": group_data.get("name"),
                "description": group_data.get("description"),
                "assets_count": len(assets),
                "valid_assets": 0,
                "error_assets": len(assets),
                "dominant_flags": "no_data",
                "status": "ERRORR"
            })

            continue

        valid_assets = len(group_df[group_df["status"] == "OK"])
        error_assets = len(group_df[group_df["status"] != "OK"])

        flags = (
            group_df["macro_flag"]
            .dropna()
            .value_counts()
            .head(5)
        )

        dominant_flags = (
            ", ".join([f"{idx}: {val}" for idx, val in flags.items()])
            if not flags.empty
            else "no_flags"
        )

        status = "OK" if error_assets == 0 else "WARNING"

        rows.append({
            "group_key": group_key,
            "group_name": group_data.get("name"),
            "description": group_data.get("description"),
            "assets_count": len(assets),
            "valid_assets": valid_assets,
            "error_assets": error_assets,
            "dominant_flags": dominant_flags,
            "status": status
        })

    group_summary_df = pd.DataFrame(rows)

    return group_summary_df


# =========================
# RUN REPORT
# =========================

def executar_macro_summary():
    print("\nA iniciar Macro Summary Report...")
    print(f"Indicadores macro assets configurados: {len(MACRO_ASSETS)}")
    print("Note: 30D/90D/252D here mean 30/90/252 observations, not exact calendar days.")

    engine = get_engine()

    results = []

    for idx, macro_key in enumerate(MACRO_ASSETS.keys(), start=1):
        print(f"\n[{idx}/{len(MACRO_ASSETS)}] Processar {macro_key}")

        result = gerar_summary_macro(
            macro_key=macro_key,
            engine=engine
        )

        results.append(result)

    report_df = pd.DataFrame(results)

    group_summary_df = gerar_summary_grupos(report_df)

    print("\n" + "=" * 130)
    print("SUMMARY FINAL - MACRO SUMMARY REPORT")
    print("=" * 130)

    cols_to_show = [
        "macro_key",
        "display_name",
        "category",
        "region",
        "end_date",
        "latest_value",
        "change_90d_abs",
        "change_252d_abs",
        "latest_zscore_252d",
        "zscore_regime",
        "trend_regime",
        "macro_flag",
        "status",
        "error"
    ]

    existing_cols = [
        col for col in cols_to_show
        if col in report_df.columns
    ]

    print(report_df[existing_cols])

    print("\nSummary por status:")
    if "status" in report_df.columns:
        status_summary = (
            report_df["status"]
            .value_counts(dropna=False)
            .rename_axis("status")
            .reset_index(name="count")
        )

        print(status_summary)

    print("\nSummary por macro_flag:")
    if "macro_flag" in report_df.columns:
        macro_flag_summary = (
            report_df["macro_flag"]
            .value_counts(dropna=False)
            .rename_axis("macro_flag")
            .reset_index(name="count")
        )

        print(macro_flag_summary)

    print("\nSummary por grupo:")
    print(group_summary_df)

    print("=" * 130)

    if EXPORT_REPORT:
        report_df.to_csv(
            OUTPUT_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        group_summary_df.to_csv(
            GROUP_OUTPUT_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print("\nReports guardata:")
        print(OUTPUT_FILE)
        print(GROUP_OUTPUT_FILE)

    print("\nMacro Summary Report completed.")

    return report_df, group_summary_df


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    executar_macro_summary()

