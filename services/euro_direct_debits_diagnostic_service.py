from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.euro_schema_audit_service import classify_period
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


IMPORT_KEY = "EURO_DIRECT_DEBITS"
KEY_COLUMNS = ("key_code", "time_period")
REQUIRED_COLUMNS = ("key_code", "freq", "time_period")


def _normalize_period_frame(frame):
    frame = frame.copy()
    frame.columns = [normalize_column_name(column) for column in frame.columns]
    frame = frame.rename(columns={"key": "key_code"})
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise ValueError(f"Direct Debits diagnostic columns are missing: {missing}")

    frame = frame.loc[:, REQUIRED_COLUMNS].fillna("")
    for column in REQUIRED_COLUMNS:
        frame[column] = frame[column].astype(str).str.strip()
    if frame[list(KEY_COLUMNS)].eq("").any(axis=None):
        raise ValueError("Direct Debits diagnostic found a null business key")
    if frame.duplicated(list(KEY_COLUMNS)).any():
        raise ValueError("Direct Debits diagnostic found duplicate business keys")

    frame["year"] = frame["time_period"].str.extract(r"^(\d{4})", expand=False).fillna("")
    frame["period_format"] = frame["time_period"].map(classify_period)
    return frame


def classify_direct_debits_period_alignment(source_frame, target_frame, target_period_type):
    source = _normalize_period_frame(source_frame)
    target = _normalize_period_frame(target_frame)
    source_index = pd.MultiIndex.from_frame(source[list(KEY_COLUMNS)])
    target_index = pd.MultiIndex.from_frame(target[list(KEY_COLUMNS)])
    source_only = source.loc[~source_index.isin(target_index)].copy()
    target_only = target.loc[~target_index.isin(source_index)].copy()

    target_annual = target[target["period_format"] == "year"]
    target_annual_series_year = set(
        zip(target_annual["key_code"], target_annual["year"])
    )
    source_detailed = source[source["period_format"] != "year"]
    source_detailed_series_year = set(
        zip(source_detailed["key_code"], source_detailed["year"])
    )
    source_only["collapsed_target_year_exists"] = [
        (key_code, year) in target_annual_series_year
        for key_code, year in zip(source_only["key_code"], source_only["year"])
    ]
    target_only["detailed_source_period_exists"] = [
        (key_code, year) in source_detailed_series_year
        for key_code, year in zip(target_only["key_code"], target_only["year"])
    ]

    frequencies = sorted(set(source["freq"]) | set(target["freq"]))
    frequency_rows = []
    for frequency in frequencies:
        source_frequency = source[source["freq"] == frequency]
        target_frequency = target[target["freq"] == frequency]
        source_only_frequency = source_only[source_only["freq"] == frequency]
        target_only_frequency = target_only[target_only["freq"] == frequency]
        source_frequency_index = pd.MultiIndex.from_frame(
            source_frequency[list(KEY_COLUMNS)]
        )
        frequency_rows.append(
            {
                "freq": frequency,
                "source_rows": len(source_frequency),
                "target_rows": len(target_frequency),
                "common_business_keys": int(source_frequency_index.isin(target_index).sum()),
                "source_only_rows": len(source_only_frequency),
                "source_only_explained_by_year_collapse": int(
                    source_only_frequency["collapsed_target_year_exists"].sum()
                ),
                "target_only_rows": len(target_only_frequency),
                "target_only_explained_by_detailed_source": int(
                    target_only_frequency["detailed_source_period_exists"].sum()
                ),
            }
        )
    frequency_alignment = pd.DataFrame(frequency_rows)

    period_formats = (
        pd.concat(
            [
                source.assign(dataset="source"),
                target.assign(dataset="target"),
            ],
            ignore_index=True,
        )
        .groupby(["dataset", "freq", "period_format"], as_index=False)
        .size()
        .rename(columns={"size": "rows"})
    )
    source_explained = int(source_only["collapsed_target_year_exists"].sum())
    target_explained = int(target_only["detailed_source_period_exists"].sum())
    all_differences_explained = (
        source_explained == len(source_only)
        and target_explained == len(target_only)
    )
    target_type = str(target_period_type or "")
    lossy_type = target_type.upper().startswith("YEAR") or "INT" in target_type.upper()
    conclusion = (
        "lossy_target_time_period_storage_confirmed"
        if all_differences_explained and lossy_type
        else "mixed_period_differences_require_review"
    )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "import_key": IMPORT_KEY,
        "target_period_type": target_type,
        "source_rows": len(source),
        "target_rows": len(target),
        "common_business_keys": int(source_index.isin(target_index).sum()),
        "source_only_rows": len(source_only),
        "source_only_explained_by_year_collapse": source_explained,
        "unexplained_source_only_rows": len(source_only) - source_explained,
        "target_only_rows": len(target_only),
        "target_only_explained_by_detailed_source": target_explained,
        "unexplained_target_only_rows": len(target_only) - target_explained,
        "conclusion": conclusion,
        "recommended_action": "controlled_shadow_rebuild_required",
        "database_write_performed": False,
    }
    samples = {
        "source_only": source_only.head(10).to_dict(orient="records"),
        "target_only": target_only.head(10).to_dict(orient="records"),
    }
    return {
        "summary": summary,
        "frequency_alignment": frequency_alignment,
        "period_formats": period_formats,
        "samples": samples,
    }


def diagnose_euro_direct_debits(engine, source_path=None):
    contract = get_macro_import(IMPORT_KEY)
    source_path = Path(source_path or contract["csv_path"]).expanduser().resolve()
    source = pd.read_csv(
        source_path,
        usecols=["KEY", "FREQ", "TIME_PERIOD"],
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
        low_memory=False,
    )

    table_name = validate_identifier(contract["table_name"])
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        raise ValueError(f"Target table not found: {table_name}")
    target_schema = {
        normalize_column_name(column["name"]): str(column["type"])
        for column in inspector.get_columns(table_name)
    }
    target = pd.read_sql(
        text(
            f"SELECT `key_code`, `freq`, "
            f"CAST(`time_period` AS CHAR) AS `time_period` FROM `{table_name}`"
        ),
        engine,
        dtype=str,
    )
    result = classify_direct_debits_period_alignment(
        source,
        target,
        target_schema.get("time_period"),
    )
    result["summary"]["source_file"] = source_path.name
    result["summary"]["target_table"] = table_name
    return result


def write_direct_debits_diagnostic(output_dir, diagnostic):
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    prefix = output_dir / f"euro_direct_debits_period_diagnostic_{timestamp}"
    json_path = prefix.with_suffix(".json")
    frequency_path = prefix.with_name(prefix.name + "_frequency.csv")
    period_path = prefix.with_name(prefix.name + "_period_formats.csv")

    payload = {
        "summary": diagnostic["summary"],
        "samples": diagnostic["samples"],
        "frequency_alignment": diagnostic["frequency_alignment"].to_dict(orient="records"),
        "period_formats": diagnostic["period_formats"].to_dict(orient="records"),
    }
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, default=str),
        encoding="utf-8",
    )
    diagnostic["frequency_alignment"].to_csv(frequency_path, index=False)
    diagnostic["period_formats"].to_csv(period_path, index=False)
    return {
        "json": json_path,
        "frequency_csv": frequency_path,
        "period_formats_csv": period_path,
    }
