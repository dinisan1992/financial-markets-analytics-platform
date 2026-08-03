from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
import re

import pandas as pd
from sqlalchemy import inspect, text

from euro_series_config import EURO_SERIES
from macro_import_manifest import get_macro_import, get_macro_import_keys
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


BUSINESS_KEY = ("key_code", "time_period")
AUTO_TARGET_COLUMNS = {"id", "created_at", "updated_at"}
SOURCE_ROW_BASELINE = {
    "EURO_CONSUMER_PRICES": 6_548_663,
    "EURO_FRAUD_LOSSES": 198,
    "EURO_NATIONAL_ACCOUNTS": 2_721_359,
    "EURO_MFI_INTEREST_RATES": 1_594_491,
    "EURO_RETAIL_INTEREST_RATES": 8_798,
    "EURO_PAYMENT_SYSTEM_TRANSACTIONS": 103_563,
}


@dataclass(frozen=True)
class EuroSchemaAudit:
    import_key: str
    table_name: str
    source_path: str
    source_bytes: int
    source_columns: tuple[str, ...]
    target_columns: tuple[str, ...]
    source_only_columns: tuple[str, ...]
    target_only_columns: tuple[str, ...]
    target_rows: int
    audited_source_rows: int | None
    source_rows_missing_from_target: int | None
    sample_rows: int
    invalid_sample_rows: int
    period_patterns: tuple[str, ...]
    target_period_type: str | None
    period_type_safe: bool
    primary_key: tuple[str, ...]
    unique_business_key: bool
    unique_key_code_only: bool
    null_business_key_rows: int | None
    duplicate_business_key_groups: int | None
    configured_series: int
    remediation_class: str
    blockers: tuple[str, ...]
    database_write_performed: bool = False

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class EuroSeriesAudit:
    series_key: str
    table_name: str
    key_code: str
    enabled: bool
    observations: int
    first_period: object | None
    last_period: object | None
    non_null_values: int
    status: str

    def to_dict(self):
        return asdict(self)


def map_source_columns(columns, aliases=None):
    normalized_aliases = {
        normalize_column_name(source): normalize_column_name(target)
        for source, target in (aliases or {}).items()
    }
    return tuple(
        normalized_aliases.get(normalize_column_name(column), normalize_column_name(column))
        for column in columns
    )


def classify_period(value):
    text_value = str(value).strip()
    if re.fullmatch(r"\d{4}", text_value):
        return "year"
    if re.fullmatch(r"\d{4}-\d{2}", text_value):
        return "month"
    if re.fullmatch(r"\d{4}-Q[1-4]", text_value, flags=re.IGNORECASE):
        return "quarter"
    if re.fullmatch(r"\d{4}-S[12]", text_value, flags=re.IGNORECASE):
        return "semester"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text_value):
        return "date"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T].+", text_value):
        return "datetime"
    return "other"


def period_type_is_safe(target_type, patterns):
    normalized_type = str(target_type or "").upper()
    pattern_set = set(patterns)
    if not pattern_set:
        return False
    if any(token in normalized_type for token in ("CHAR", "TEXT")):
        return True
    if normalized_type.startswith("DATE"):
        return pattern_set <= {"date", "datetime"}
    if normalized_type.startswith("YEAR") or "INT" in normalized_type:
        return pattern_set <= {"year"}
    return False


def classify_euro_remediation(blockers):
    blockers = tuple(dict.fromkeys(blockers))
    rebuild_reasons = {
        "unsafe_time_period_type",
        "key_code_only_overwrite_risk",
        "duplicate_business_keys",
        "target_history_incomplete",
    }
    if rebuild_reasons.intersection(blockers):
        return "rebuild_required"
    if blockers == ("unique_business_key_missing",):
        return "key_addition_candidate"
    if not blockers:
        return "write_contract_ready"
    return "mapping_review_required"


def _unique_key_sets(inspector, table_name):
    key_sets = []
    primary = inspector.get_pk_constraint(table_name).get("constrained_columns") or []
    if primary:
        key_sets.append(tuple(normalize_column_name(column) for column in primary))
    for item in inspector.get_unique_constraints(table_name):
        columns = item.get("column_names") or []
        if columns:
            key_sets.append(tuple(normalize_column_name(column) for column in columns))
    for item in inspector.get_indexes(table_name):
        columns = item.get("column_names") or []
        if item.get("unique") and columns:
            key_sets.append(tuple(normalize_column_name(column) for column in columns))
    return tuple(dict.fromkeys(key_sets))


def _sample_source(contract, sample_rows):
    frame = pd.read_csv(
        contract["csv_path"],
        nrows=max(1, int(sample_rows)),
        dtype=str,
        encoding="utf-8-sig",
        low_memory=False,
    )
    frame.columns = [normalize_column_name(column) for column in frame.columns]
    aliases = {
        normalize_column_name(source): normalize_column_name(target)
        for source, target in contract.get("column_aliases", {}).items()
    }
    frame = frame.rename(columns=aliases)
    required = list(contract["required_columns"])
    if not set(required).issubset(frame.columns):
        return frame, len(frame), ()
    required_values = frame[required].replace(r"^\s*$", pd.NA, regex=True)
    valid = required_values.notna().all(axis=1)
    valid &= pd.to_numeric(frame["obs_value"], errors="coerce").notna()
    patterns = tuple(
        sorted(
            {
                classify_period(value)
                for value in frame.loc[frame["time_period"].notna(), "time_period"]
            }
        )
    )
    return frame, int((~valid).sum()), patterns


def _configured_series_by_table():
    output = {}
    for series_key, config in EURO_SERIES.items():
        output.setdefault(config["table_name"], []).append((series_key, config))
    return output


def audit_euro_schema_contract(
    engine,
    import_key,
    sample_rows=1000,
    deep=False,
):
    contract = get_macro_import(import_key)
    if contract["group"] != "EURO":
        raise ValueError(f"Not a EURO import contract: {import_key}")

    table_name = validate_identifier(contract["table_name"])
    inspector = inspect(engine)
    source_path = Path(contract["csv_path"])
    header = pd.read_csv(source_path, nrows=0, encoding="utf-8-sig")
    source_columns = map_source_columns(
        header.columns,
        aliases=contract.get("column_aliases"),
    )
    sample, invalid_rows, period_patterns = _sample_source(contract, sample_rows)

    if not inspector.has_table(table_name):
        return EuroSchemaAudit(
            import_key=str(import_key).upper(),
            table_name=table_name,
            source_path=str(source_path),
            source_bytes=source_path.stat().st_size,
            source_columns=source_columns,
            target_columns=(),
            source_only_columns=source_columns,
            target_only_columns=(),
            target_rows=0,
            audited_source_rows=SOURCE_ROW_BASELINE.get(str(import_key).upper()),
            source_rows_missing_from_target=None,
            sample_rows=len(sample),
            invalid_sample_rows=invalid_rows,
            period_patterns=period_patterns,
            target_period_type=None,
            period_type_safe=False,
            primary_key=(),
            unique_business_key=False,
            unique_key_code_only=False,
            null_business_key_rows=None,
            duplicate_business_key_groups=None,
            configured_series=0,
            remediation_class="mapping_review_required",
            blockers=("target_table_missing",),
        )

    target_schema = inspector.get_columns(table_name)
    target_columns = tuple(normalize_column_name(column["name"]) for column in target_schema)
    target_types = {
        normalize_column_name(column["name"]): str(column["type"])
        for column in target_schema
    }
    source_only = tuple(sorted(set(source_columns) - set(target_columns)))
    target_only = tuple(
        sorted(set(target_columns) - set(source_columns) - AUTO_TARGET_COLUMNS)
    )
    key_sets = _unique_key_sets(inspector, table_name)
    unique_business_key = BUSINESS_KEY in key_sets
    unique_key_code_only = ("key_code",) in key_sets
    primary_key = tuple(
        normalize_column_name(column)
        for column in (
            inspector.get_pk_constraint(table_name).get("constrained_columns") or []
        )
    )
    required_target_missing = tuple(
        column for column in BUSINESS_KEY + ("obs_value",) if column not in target_columns
    )
    period_safe = period_type_is_safe(
        target_types.get("time_period"),
        period_patterns,
    )

    with engine.connect() as connection:
        target_rows = int(
            connection.execute(
                text(f"SELECT COUNT(1) FROM `{table_name}`")
            ).scalar_one()
        )
        null_key_rows = None
        duplicate_groups = None
        if set(BUSINESS_KEY).issubset(target_columns):
            null_key_rows = int(
                connection.execute(
                    text(
                        f"SELECT COUNT(1) FROM `{table_name}` "
                        "WHERE key_code IS NULL OR time_period IS NULL"
                    )
                ).scalar_one()
            )
            if deep:
                duplicate_groups = int(
                    connection.execute(
                        text(
                            "SELECT COUNT(1) FROM ("
                            "SELECT key_code, time_period "
                            f"FROM `{table_name}` "
                            "WHERE key_code IS NOT NULL AND time_period IS NOT NULL "
                            "GROUP BY key_code, time_period HAVING COUNT(1) > 1"
                            ") AS duplicate_keys"
                        )
                    ).scalar_one()
                )

    audited_source_rows = SOURCE_ROW_BASELINE.get(str(import_key).upper())
    source_rows_missing = (
        max(audited_source_rows - target_rows, 0)
        if audited_source_rows is not None
        else None
    )
    blockers = []
    if required_target_missing:
        blockers.append("target_contract_columns_missing")
    if source_only:
        blockers.append("source_columns_unmapped")
    if target_only:
        blockers.append("target_columns_unmapped")
    if not period_safe:
        blockers.append("unsafe_time_period_type")
    if unique_key_code_only and not unique_business_key:
        blockers.append("key_code_only_overwrite_risk")
    if null_key_rows:
        blockers.append("null_business_key_rows")
    if duplicate_groups:
        blockers.append("duplicate_business_keys")
    if source_rows_missing:
        blockers.append("target_history_incomplete")
    if not unique_business_key:
        blockers.append("unique_business_key_missing")

    remediation_class = classify_euro_remediation(blockers)

    configured = _configured_series_by_table().get(table_name, [])
    return EuroSchemaAudit(
        import_key=str(import_key).upper(),
        table_name=table_name,
        source_path=str(source_path),
        source_bytes=source_path.stat().st_size,
        source_columns=source_columns,
        target_columns=target_columns,
        source_only_columns=source_only,
        target_only_columns=target_only,
        target_rows=target_rows,
        audited_source_rows=audited_source_rows,
        source_rows_missing_from_target=source_rows_missing,
        sample_rows=len(sample),
        invalid_sample_rows=invalid_rows,
        period_patterns=period_patterns,
        target_period_type=target_types.get("time_period"),
        period_type_safe=period_safe,
        primary_key=primary_key,
        unique_business_key=unique_business_key,
        unique_key_code_only=unique_key_code_only,
        null_business_key_rows=null_key_rows,
        duplicate_business_key_groups=duplicate_groups,
        configured_series=len(configured),
        remediation_class=remediation_class,
        blockers=tuple(dict.fromkeys(blockers)),
    )


def audit_all_euro_schema_contracts(engine, sample_rows=1000, deep=False):
    return [
        audit_euro_schema_contract(
            engine,
            import_key,
            sample_rows=sample_rows,
            deep=deep,
        )
        for import_key in get_macro_import_keys("EURO")
    ]


def audit_configured_euro_series(engine):
    results = []
    for table_name, items in _configured_series_by_table().items():
        table_name = validate_identifier(table_name)
        first_config = items[0][1]
        key_column = validate_identifier(first_config["key_col"])
        date_column = validate_identifier(first_config["date_col"])
        value_column = validate_identifier(first_config["value_col"])
        parameters = {
            f"key_{index}": config["key_code"]
            for index, (_, config) in enumerate(items)
        }
        placeholders = ", ".join(f":key_{index}" for index in range(len(items)))
        query = text(
            f"""
            SELECT
                `{key_column}` AS key_code,
                COUNT(1) AS observations,
                MIN(`{date_column}`) AS first_period,
                MAX(`{date_column}`) AS last_period,
                COUNT(`{value_column}`) AS non_null_values
            FROM `{table_name}`
            WHERE `{key_column}` IN ({placeholders})
            GROUP BY `{key_column}`
            """
        )
        with engine.connect() as connection:
            available = {
                row["key_code"]: dict(row)
                for row in connection.execute(query, parameters).mappings()
            }
        for series_key, config in items:
            row = available.get(config["key_code"], {})
            observations = int(row.get("observations", 0) or 0)
            results.append(
                EuroSeriesAudit(
                    series_key=series_key,
                    table_name=table_name,
                    key_code=config["key_code"],
                    enabled=bool(config.get("enabled", True)),
                    observations=observations,
                    first_period=row.get("first_period"),
                    last_period=row.get("last_period"),
                    non_null_values=int(row.get("non_null_values", 0) or 0),
                    status="available" if observations else "missing",
                )
            )
    return results


def _audit_frame(audits):
    rows = []
    for audit in audits:
        row = audit.to_dict()
        for column in (
            "source_columns",
            "target_columns",
            "source_only_columns",
            "target_only_columns",
            "period_patterns",
            "primary_key",
            "blockers",
        ):
            row[column] = " | ".join(str(value) for value in row[column])
        rows.append(row)
    return pd.DataFrame(rows)


def write_euro_audit_report(output_dir, audits, series_audits):
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = output_dir / f"euro_schema_audit_{timestamp}"
    schema_csv = prefix.with_name(prefix.name + "_tables.csv")
    series_csv = prefix.with_name(prefix.name + "_series.csv")
    json_path = prefix.with_suffix(".json")

    _audit_frame(audits).to_csv(schema_csv, index=False, encoding="utf-8-sig")
    pd.DataFrame([audit.to_dict() for audit in series_audits]).to_csv(
        series_csv,
        index=False,
        encoding="utf-8-sig",
    )
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "database_write_performed": False,
        "tables": [audit.to_dict() for audit in audits],
        "configured_series": [audit.to_dict() for audit in series_audits],
    }
    json_path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    digest = sha256(json_path.read_bytes()).hexdigest().upper()
    return {
        "json": json_path,
        "tables_csv": schema_csv,
        "series_csv": series_csv,
        "json_sha256": digest,
    }
