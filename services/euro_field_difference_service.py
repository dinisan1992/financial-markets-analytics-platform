from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.euro_rebuild_service import (
    BUSINESS_KEY,
    DECIMAL_COLUMNS,
    mapped_source_columns,
    normalize_numeric_for_storage,
    normalize_row,
    normalize_source_frame,
    source_chunks,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


DEFAULT_CHUNK_SIZE = 25_000
DEFAULT_QUERY_BATCH_SIZE = 100
DEFAULT_EXAMPLE_LIMIT = 3
CHANGE_TYPES = (
    "source_null_target_value",
    "source_value_target_null",
    "whitespace_only",
    "case_only",
    "whitespace_and_case",
    "numeric_representation_only",
    "storage_precision_only",
    "value_changed",
)


@dataclass(frozen=True)
class EuroColumnDifference:
    column: str
    compared_rows: int
    mismatch_rows: int
    mismatch_rate: float
    source_null_target_value: int
    source_value_target_null: int
    whitespace_only: int
    case_only: int
    whitespace_and_case: int
    numeric_representation_only: int
    storage_precision_only: int
    value_changed: int
    examples: tuple[dict, ...]


@dataclass(frozen=True)
class EuroFieldDifferenceAudit:
    import_key: str
    target_table: str
    source_file: str
    source_columns: tuple[str, ...]
    target_column_types: dict[str, str]
    requested_sample_keys: int
    source_sample_rows_found: int
    target_sample_rows_found: int
    compared_rows: int
    exact_row_matches: int
    differing_rows: int
    source_missing_key_samples: tuple[dict, ...]
    target_missing_key_samples: tuple[dict, ...]
    column_differences: tuple[EuroColumnDifference, ...]
    database_write_performed: bool = False

    def to_dict(self):
        return asdict(self)


def _normalize_sample_keys(sample_keys):
    normalized = []
    for item in sample_keys:
        if isinstance(item, dict):
            key = tuple(item.get(column) for column in BUSINESS_KEY)
        else:
            key = tuple(item)
        if len(key) != len(BUSINESS_KEY):
            raise ValueError(f"Invalid EURO business key: {item}")
        key = tuple(None if value is None else str(value).strip() for value in key)
        if any(value in {None, ""} for value in key):
            raise ValueError(f"Null EURO business key value: {item}")
        normalized.append(key)
    return tuple(dict.fromkeys(normalized))


def _source_sample_records(contract, columns, sample_keys, chunk_size):
    wanted = set(sample_keys)
    found = {}
    reader = source_chunks(contract, chunk_size)
    try:
        for raw_chunk in reader:
            chunk = normalize_source_frame(contract, raw_chunk, columns)
            key_frame = chunk.loc[:, list(BUSINESS_KEY)].copy()
            for column in BUSINESS_KEY:
                key_frame[column] = key_frame[column].astype(str).str.strip()
            sample_index = pd.MultiIndex.from_frame(key_frame)
            selected = chunk.loc[sample_index.isin(wanted)]
            for values in selected.itertuples(index=False, name=None):
                record, invalid_columns = normalize_row(columns, values)
                if invalid_columns:
                    raise ValueError(
                        "Invalid numeric values in sampled source row: "
                        + ", ".join(invalid_columns)
                    )
                key = tuple(record[column] for column in BUSINESS_KEY)
                if key in found:
                    raise ValueError(f"Duplicate sampled source business key: {key}")
                found[key] = record
            if len(found) == len(wanted):
                break
    finally:
        close = getattr(reader, "close", None)
        if close is not None:
            close()
    return found


def _target_column_names(bind, table_name, columns):
    table_name = validate_identifier(table_name)
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        raise ValueError(f"Target table not found: {table_name}")
    schema = inspector.get_columns(table_name)
    actual_columns = {
        normalize_column_name(column["name"]): column["name"]
        for column in schema
    }
    column_types = {
        normalize_column_name(column["name"]): str(column["type"])
        for column in schema
    }
    missing = sorted(set(columns) - set(actual_columns))
    if missing:
        raise ValueError(f"Target table {table_name} is missing columns: {missing}")
    return (
        {
            column: validate_identifier(actual_columns[column])
            for column in columns
        },
        {column: column_types[column] for column in columns},
    )


def _target_sample_records(engine, table_name, columns, sample_keys, batch_size):
    actual_columns, column_types = _target_column_names(
        engine,
        table_name,
        columns,
    )
    selections = []
    for column in columns:
        expression = f"`{actual_columns[column]}`"
        if (
            column in DECIMAL_COLUMNS
            and engine.dialect.name in {"mysql", "mariadb"}
            and column_types[column].upper().startswith(("FLOAT", "REAL"))
        ):
            expression = f"CAST({expression} AS DOUBLE)"
        selections.append(f"{expression} AS `{validate_identifier(column)}`")
    selections = ", ".join(selections)
    key_code_column = actual_columns["key_code"]
    time_period_column = actual_columns["time_period"]
    found = {}
    batch_size = max(1, min(int(batch_size), 250))

    with engine.connect() as connection:
        for start in range(0, len(sample_keys), batch_size):
            batch = sample_keys[start:start + batch_size]
            predicates = []
            parameters = {}
            for index, (key_code, time_period) in enumerate(batch):
                predicates.append(
                    f"(`{key_code_column}` = :key_code_{index} AND "
                    f"`{time_period_column}` = :time_period_{index})"
                )
                parameters[f"key_code_{index}"] = key_code
                parameters[f"time_period_{index}"] = time_period
            query = text(
                f"SELECT {selections} FROM `{validate_identifier(table_name)}` "
                f"WHERE {' OR '.join(predicates)}"
            )
            for row in connection.execute(query, parameters).mappings():
                values = tuple(row[column] for column in columns)
                record, invalid_columns = normalize_row(columns, values)
                if invalid_columns:
                    raise ValueError(
                        "Invalid numeric values in sampled target row: "
                        + ", ".join(invalid_columns)
                    )
                key = tuple(record[column] for column in BUSINESS_KEY)
                if key in found:
                    raise ValueError(f"Duplicate sampled target business key: {key}")
                found[key] = record
    return found, column_types


def _decimal_equivalent(source_value, target_value):
    try:
        source_decimal = Decimal(str(source_value).strip())
        target_decimal = Decimal(str(target_value).strip())
    except InvalidOperation:
        return False
    return (
        source_decimal.is_finite()
        and target_decimal.is_finite()
        and source_decimal == target_decimal
    )


def _storage_precision_equivalent(source_value, target_value, target_type):
    target_type = str(target_type).upper()
    if not target_type.startswith(("DECIMAL", "NUMERIC", "FLOAT", "REAL", "DOUBLE")):
        return False
    try:
        source_normalized = normalize_numeric_for_storage(
            source_value,
            target_type,
        )
        target_normalized = normalize_numeric_for_storage(
            target_value,
            target_type,
        )
    except (TypeError, ValueError):
        return False
    return source_normalized == target_normalized


def _change_type(source_value, target_value, target_type):
    if source_value is None:
        return "source_null_target_value"
    if target_value is None:
        return "source_value_target_null"
    if _storage_precision_equivalent(source_value, target_value, target_type):
        return "storage_precision_only"
    if isinstance(source_value, str) and isinstance(target_value, str):
        if source_value.strip() == target_value.strip():
            return "whitespace_only"
        if source_value.casefold() == target_value.casefold():
            return "case_only"
        if source_value.strip().casefold() == target_value.strip().casefold():
            return "whitespace_and_case"
        if _decimal_equivalent(source_value, target_value):
            return "numeric_representation_only"
    return "value_changed"


def _display_value(value, limit=200):
    if value is None:
        return None
    output = str(value)
    if len(output) > limit:
        return output[:limit] + "..."
    return output


def audit_euro_field_differences(
    engine,
    import_key,
    sample_keys,
    *,
    chunk_size=DEFAULT_CHUNK_SIZE,
    query_batch_size=DEFAULT_QUERY_BATCH_SIZE,
    example_limit=DEFAULT_EXAMPLE_LIMIT,
    source_path=None,
):
    """Compare sampled EURO rows field by field using SELECT-only SQL access."""
    import_key = str(import_key).upper()
    contract = get_macro_import(import_key)
    if contract.get("group") != "EURO":
        raise ValueError(f"Not a EURO import contract: {import_key}")
    if source_path is not None:
        contract = dict(contract)
        contract["csv_path"] = Path(source_path)
    source_path = Path(contract["csv_path"]).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"EURO source CSV not found: {source_path}")

    normalized_keys = _normalize_sample_keys(sample_keys)
    if not normalized_keys:
        raise ValueError("At least one EURO sample key is required")
    columns = mapped_source_columns(contract)
    table_name = validate_identifier(contract["table_name"])
    source_records = _source_sample_records(
        contract,
        columns,
        normalized_keys,
        max(1, int(chunk_size)),
    )
    target_records, target_column_types = _target_sample_records(
        engine,
        table_name,
        columns,
        normalized_keys,
        query_batch_size,
    )

    common_keys = tuple(
        key for key in normalized_keys
        if key in source_records and key in target_records
    )
    counters = {
        column: {change_type: 0 for change_type in CHANGE_TYPES}
        for column in columns
    }
    examples = {column: [] for column in columns}
    differing_rows = 0
    for key in common_keys:
        row_differs = False
        for column in columns:
            source_value = source_records[key].get(column)
            target_value = target_records[key].get(column)
            if source_value == target_value:
                continue
            row_differs = True
            change_type = _change_type(
                source_value,
                target_value,
                target_column_types[column],
            )
            counters[column][change_type] += 1
            if len(examples[column]) < max(0, int(example_limit)):
                examples[column].append({
                    "key_code": key[0],
                    "time_period": key[1],
                    "change_type": change_type,
                    "source_value": _display_value(source_value),
                    "target_value": _display_value(target_value),
                })
        differing_rows += row_differs

    column_differences = []
    for column in columns:
        mismatch_rows = sum(counters[column].values())
        if mismatch_rows == 0:
            continue
        column_differences.append(EuroColumnDifference(
            column=column,
            compared_rows=len(common_keys),
            mismatch_rows=mismatch_rows,
            mismatch_rate=round(mismatch_rows / len(common_keys), 6),
            examples=tuple(examples[column]),
            **counters[column],
        ))
    column_differences.sort(
        key=lambda item: (-item.mismatch_rows, item.column)
    )

    source_missing = tuple(
        {"key_code": key[0], "time_period": key[1]}
        for key in normalized_keys
        if key not in source_records
    )
    target_missing = tuple(
        {"key_code": key[0], "time_period": key[1]}
        for key in normalized_keys
        if key not in target_records
    )
    return EuroFieldDifferenceAudit(
        import_key=import_key,
        target_table=table_name,
        source_file=source_path.name,
        source_columns=tuple(columns),
        target_column_types=target_column_types,
        requested_sample_keys=len(normalized_keys),
        source_sample_rows_found=len(source_records),
        target_sample_rows_found=len(target_records),
        compared_rows=len(common_keys),
        exact_row_matches=len(common_keys) - differing_rows,
        differing_rows=differing_rows,
        source_missing_key_samples=source_missing,
        target_missing_key_samples=target_missing,
        column_differences=tuple(column_differences),
        database_write_performed=False,
    )
