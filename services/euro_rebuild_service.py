from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from hashlib import sha256
from pathlib import Path
import json
import re
import struct

import pandas as pd
from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.euro_fingerprint_store import (
    EuroFingerprintStore,
    SOURCE_DATASET,
    TARGET_DATASET,
    temporary_fingerprint_store,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


TARGET_IMPORT_KEYS = (
    "EURO_ATM_POS_TRANSACTIONS",
    "EURO_CARD_PAYMENTS_MERCHANT_CATEGORY",
    "EURO_COMPOSITE_SYSTEMIC_STRESS",
    "EURO_COUNTRY_FINANCIAL_STRESS",
    "EURO_CREDIT_TRANSFERS",
    "EURO_EMONEY_PAYMENTS",
)
BUILD_CONFIRMATION = "BUILD_EURO_REBUILD_SHADOWS"
SWAP_CONFIRMATION = "SWAP_EURO_REBUILD_SHADOWS"
HASH_COLUMN = "_source_row_sha256"
BUSINESS_KEY = ("key_code", "time_period")
DECIMAL_COLUMNS = {"obs_value"}
INTEGER_COLUMNS = {"decimals", "unit_mult"}
LONG_TEXT_COLUMNS = {
    "comment_obs",
    "comment_ts",
    "compilation",
    "title",
    "title_compl",
}
TEXT_TYPE_MARKERS = ("CHAR", "TEXT", "CLOB", "ENUM", "SET")
RAW_NUMERIC_MISSING = {"", ".", "na", "n/a", "nan", "null"}
DECIMAL_QUANTUM = Decimal("0.000000000001")
MAX_SHADOW_FETCH_ROWS = 5_000


@dataclass(frozen=True)
class EuroRebuildValidation:
    import_key: str
    active_table: str
    shadow_table: str
    source_rows: int
    shadow_rows: int
    source_unique_business_keys: int
    shadow_unique_business_keys: int
    source_non_null_values: int
    shadow_non_null_values: int
    null_business_keys: int
    duplicate_business_key_groups: int
    row_hash_mismatches: int
    source_hash_mismatches: int
    missing_source_rows: int
    first_period: object | None
    last_period: object | None
    source_columns: tuple[str, ...]
    database_write_performed: bool
    memory_bounded_validation: bool = False
    comparison_store_bytes: int = 0
    row_hash_mismatch_samples: tuple[dict, ...] = ()

    @property
    def valid(self):
        return (
            self.source_rows == self.shadow_rows
            and self.source_rows == self.source_unique_business_keys
            and self.source_unique_business_keys
            == self.shadow_unique_business_keys
            and self.source_non_null_values == self.shadow_non_null_values
            and self.null_business_keys == 0
            and self.duplicate_business_key_groups == 0
            and self.row_hash_mismatches == 0
            and self.source_hash_mismatches == 0
            and self.missing_source_rows == 0
        )

    def to_dict(self):
        output = asdict(self)
        output["valid"] = self.valid
        return output


def versioned_table_name(table_name, marker, suffix):
    table_name = validate_identifier(table_name)
    marker = validate_identifier(marker)
    validate_identifier(f"suffix_{suffix}")
    tail = f"__{marker}_{suffix}"
    return f"{table_name[:64 - len(tail)]}{tail}"


def shadow_table_name(table_name, suffix, version="v055"):
    return versioned_table_name(table_name, f"shadow_{version}", suffix)


def retained_table_name(table_name, suffix, version="v055"):
    return versioned_table_name(table_name, f"pre_{version}", suffix)


def failed_table_name(table_name, suffix, version="v055"):
    return versioned_table_name(table_name, f"failed_{version}", suffix)


def validate_scoped_backup(backup_file, tables):
    path = Path(backup_file).expanduser().resolve()
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"A non-empty SQL backup is required: {path}")

    create_markers = {
        table_name: f"CREATE TABLE `{table_name}`".encode()
        for table_name in tables
    }
    insert_markers = {
        table_name: f"INSERT INTO `{table_name}`".encode()
        for table_name in tables
    }
    found_create = {table_name: False for table_name in tables}
    found_insert = {table_name: False for table_name in tables}
    digest = sha256()
    overlap = b""

    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            searchable = overlap + chunk
            for table_name in tables:
                found_create[table_name] |= create_markers[table_name] in searchable
                found_insert[table_name] |= insert_markers[table_name] in searchable
            overlap = searchable[-512:]

    missing = [
        table_name
        for table_name in tables
        if not found_create[table_name] or not found_insert[table_name]
    ]
    if missing:
        raise ValueError(
            "SQL backup is missing structure or data markers for: "
            + ", ".join(missing)
        )
    return {
        "path": path,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest().upper(),
        "tables": tuple(tables),
    }


def _mapped_source_columns(contract):
    header = pd.read_csv(
        contract["csv_path"],
        nrows=0,
        encoding="utf-8-sig",
    )
    aliases = {
        normalize_column_name(source): normalize_column_name(target)
        for source, target in contract.get("column_aliases", {}).items()
    }
    columns = tuple(
        aliases.get(normalize_column_name(column), normalize_column_name(column))
        for column in header.columns
    )
    if len(columns) != len(set(columns)):
        raise ValueError(f"Mapped source columns are not unique: {columns}")
    required = set(contract["required_columns"])
    if not required.issubset(columns):
        missing = sorted(required - set(columns))
        raise ValueError(f"Source contract columns are missing: {missing}")
    return columns


def _normalize_source_frame(contract, frame, expected_columns):
    aliases = {
        normalize_column_name(source): normalize_column_name(target)
        for source, target in contract.get("column_aliases", {}).items()
    }
    frame = frame.copy()
    frame.columns = [normalize_column_name(column) for column in frame.columns]
    frame = frame.rename(columns=aliases)
    columns = tuple(frame.columns)
    if columns != tuple(expected_columns):
        raise ValueError(
            f"Source columns changed while reading {contract['csv_path']}: {columns}"
        )
    return frame


def _decimal_value(value):
    text_value = str(value).strip()
    if text_value.lower() in RAW_NUMERIC_MISSING:
        return None, False
    try:
        decimal_value = Decimal(text_value)
    except InvalidOperation:
        return None, True
    if not decimal_value.is_finite():
        return None, True
    return decimal_value.quantize(
        DECIMAL_QUANTUM,
        rounding=ROUND_HALF_UP,
    ), False


def _integer_value(value):
    text_value = str(value).strip()
    if text_value.lower() in RAW_NUMERIC_MISSING:
        return None, False
    try:
        decimal_value = Decimal(text_value)
    except InvalidOperation:
        return None, True
    if not decimal_value.is_finite() or decimal_value != decimal_value.to_integral_value():
        return None, True
    return int(decimal_value), False


def normalize_row(columns, values):
    record = {}
    invalid_numeric = []
    for column, value in zip(columns, values):
        if value is None:
            normalized = None
        elif column in DECIMAL_COLUMNS:
            normalized, invalid = _decimal_value(value)
            if invalid:
                invalid_numeric.append(column)
        elif column in INTEGER_COLUMNS:
            normalized, invalid = _integer_value(value)
            if invalid:
                invalid_numeric.append(column)
        else:
            normalized = str(value)
            if normalized == "":
                normalized = None
            elif column in BUSINESS_KEY:
                normalized = normalized.strip()
        record[column] = normalized
    return record, tuple(invalid_numeric)


def normalize_numeric_for_storage(value, target_type):
    decimal_value, invalid = _decimal_value(value)
    if invalid:
        raise ValueError(f"Invalid decimal value: {value}")
    if decimal_value is None:
        return decimal_value
    if not target_type:
        return decimal_value.copy_abs() if decimal_value == 0 else decimal_value
    target_type = str(target_type).upper()
    decimal_match = re.search(
        r"(?:DECIMAL|NUMERIC)\(\d+\s*,\s*(\d+)\)",
        target_type,
    )
    if decimal_match:
        scale = int(decimal_match.group(1))
        normalized = decimal_value.quantize(
            Decimal(10) ** -scale,
            rounding=ROUND_HALF_UP,
        )
    elif target_type.startswith(("FLOAT", "REAL")):
        try:
            float32_value = struct.unpack(
                "!f",
                struct.pack("!f", float(decimal_value)),
            )[0]
        except (OverflowError, struct.error) as exc:
            raise ValueError(f"Value exceeds FLOAT storage: {value}") from exc
        normalized = Decimal.from_float(float32_value)
    elif target_type.startswith("DOUBLE"):
        normalized = Decimal(format(float(decimal_value), ".15g"))
    else:
        normalized = decimal_value
    return normalized.copy_abs() if normalized == 0 else normalized


def canonical_row_hash(columns, record, column_types=None):
    column_types = column_types or {}
    values = []
    for column in columns:
        value = record.get(column)
        if value is None:
            values.append(None)
        elif column in DECIMAL_COLUMNS:
            decimal_value = normalize_numeric_for_storage(
                value,
                column_types.get(column),
            )
            values.append(format(decimal_value, "f") if decimal_value is not None else None)
        elif column in INTEGER_COLUMNS:
            integer_value, invalid = _integer_value(value)
            if invalid:
                raise ValueError(f"Invalid integer value in {column}: {value}")
            values.append(integer_value)
        else:
            text_value = str(value).strip()
            values.append(text_value or None)
    payload = json.dumps(
        values,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(payload).hexdigest().upper()


def _source_chunks(contract, chunk_size, source_path=None):
    path = Path(source_path or contract["csv_path"]).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"EURO source CSV not found: {path}")
    return pd.read_csv(
        path,
        chunksize=max(1, int(chunk_size)),
        dtype=str,
        keep_default_na=False,
        na_filter=False,
        encoding="utf-8-sig",
        low_memory=False,
    )


def mapped_source_columns(contract):
    """Return the canonical source columns used by every exact EURO check."""
    return _mapped_source_columns(contract)


def normalize_source_frame(contract, frame, expected_columns):
    """Apply the shared EURO aliases and verify a stable chunk schema."""
    return _normalize_source_frame(contract, frame, expected_columns)


def source_chunks(contract, chunk_size, source_path=None):
    """Read a EURO CSV in bounded string-preserving chunks."""
    return _source_chunks(contract, chunk_size, source_path=source_path)


def record_batches(records, batch_size):
    batch_size = max(1, int(batch_size))
    for start in range(0, len(records), batch_size):
        yield records[start:start + batch_size]


def source_fingerprints(import_key, chunk_size=5000, source_path=None):
    contract = get_macro_import(import_key)
    columns = _mapped_source_columns(contract)
    fingerprints = {}
    non_null_values = 0
    invalid_numeric_rows = 0

    for raw_chunk in _source_chunks(
        contract,
        chunk_size,
        source_path=source_path,
    ):
        chunk = _normalize_source_frame(contract, raw_chunk, columns)
        for values in chunk.itertuples(index=False, name=None):
            record, invalid_columns = normalize_row(columns, values)
            if invalid_columns:
                invalid_numeric_rows += 1
                continue
            key = tuple(record[column] for column in BUSINESS_KEY)
            if any(value is None for value in key):
                raise ValueError(f"Null source business key in {import_key}: {key}")
            if key in fingerprints:
                raise ValueError(f"Duplicate source business key in {import_key}: {key}")
            row_hash = canonical_row_hash(columns, record)
            fingerprints[key] = row_hash
            non_null_values += record.get("obs_value") is not None

    if invalid_numeric_rows:
        raise ValueError(
            f"Invalid non-empty numeric rows in {import_key}: {invalid_numeric_rows}"
        )
    return columns, fingerprints, non_null_values


def source_fingerprints_to_store(
    import_key,
    fingerprint_store,
    chunk_size=5000,
    source_path=None,
):
    contract = get_macro_import(import_key)
    columns = _mapped_source_columns(contract)
    fingerprint_store.clear(SOURCE_DATASET)
    fingerprint_store.clear(TARGET_DATASET)
    source_rows = 0
    non_null_values = 0
    invalid_numeric_rows = 0

    for raw_chunk in _source_chunks(
        contract,
        chunk_size,
        source_path=source_path,
    ):
        chunk = _normalize_source_frame(contract, raw_chunk, columns)
        fingerprints = []
        chunk_keys = set()
        for values in chunk.itertuples(index=False, name=None):
            record, invalid_columns = normalize_row(columns, values)
            if invalid_columns:
                invalid_numeric_rows += 1
                continue
            key = tuple(record[column] for column in BUSINESS_KEY)
            if any(value is None for value in key):
                raise ValueError(
                    f"Null source business key in {import_key}: {key}"
                )
            if key in chunk_keys:
                raise ValueError(
                    f"Duplicate source business key in {import_key}: {key}"
                )
            chunk_keys.add(key)
            fingerprints.append(
                (
                    key[0],
                    key[1],
                    bytes.fromhex(canonical_row_hash(columns, record)),
                )
            )
            source_rows += 1
            non_null_values += record.get("obs_value") is not None
        fingerprint_store.insert_records(SOURCE_DATASET, fingerprints)

    if invalid_numeric_rows:
        raise ValueError(
            f"Invalid non-empty numeric rows in {import_key}: "
            f"{invalid_numeric_rows}"
        )
    summary = fingerprint_store.summary(SOURCE_DATASET)
    if summary["duplicate_groups"]:
        samples = fingerprint_store.key_samples("source_duplicate", 1)
        raise ValueError(
            f"Duplicate source business key in {import_key}: {samples[0]}"
        )
    if summary["unique_keys"] != source_rows:
        raise RuntimeError(f"Source fingerprint count mismatch: {import_key}")
    return columns, source_rows, non_null_values


def _table_exists(engine, table_name):
    return inspect(engine).has_table(validate_identifier(table_name))


def _business_key_is_unique(engine, table_name):
    table_name = validate_identifier(table_name)
    inspector = inspect(engine)
    candidates = []
    primary = inspector.get_pk_constraint(table_name).get("constrained_columns") or []
    if primary:
        candidates.append(tuple(normalize_column_name(value) for value in primary))
    for constraint in inspector.get_unique_constraints(table_name):
        columns = constraint.get("column_names") or []
        if columns:
            candidates.append(tuple(normalize_column_name(value) for value in columns))
    for index in inspector.get_indexes(table_name):
        columns = index.get("column_names") or []
        if index.get("unique") and columns:
            candidates.append(tuple(normalize_column_name(value) for value in columns))
    return BUSINESS_KEY in candidates


def build_shadow_schema_statements(engine, import_key, suffix, version="v055"):
    contract = get_macro_import(import_key)
    active = validate_identifier(contract["table_name"])
    shadow = shadow_table_name(active, suffix, version=version)
    inspector = inspect(engine)
    active_schema = {
        normalize_column_name(column["name"]): column
        for column in inspector.get_columns(active)
    }
    source_columns = _mapped_source_columns(contract)
    missing = sorted(set(source_columns) - set(active_schema))
    if missing:
        raise ValueError(f"Active table is missing source columns: {missing}")

    statements = [f"CREATE TABLE `{shadow}` LIKE `{active}`"]
    clauses = []
    if "id" in active_schema and "id" not in source_columns:
        id_type = str(active_schema["id"]["type"]).upper()
        statements.append(
            f"ALTER TABLE `{shadow}` MODIFY `id` {id_type} NOT NULL"
        )
    if import_key != "EURO_ATM_POS_TRANSACTIONS":
        clauses.append("DROP PRIMARY KEY")
    if "id" in active_schema and "id" not in source_columns:
        clauses.append("DROP COLUMN `id`")
    if import_key == "EURO_COMPOSITE_SYSTEMIC_STRESS" and "key" in active_schema:
        clauses.append("DROP COLUMN `KEY`")

    for column in source_columns:
        quoted = f"`{validate_identifier(column)}`"
        if column == "key_code":
            clauses.append(f"MODIFY {quoted} VARCHAR(255) NOT NULL")
        elif column == "time_period":
            clauses.append(f"MODIFY {quoted} VARCHAR(20) NOT NULL")
        elif column == "obs_value":
            clauses.append(f"MODIFY {quoted} DECIMAL(38,12) NULL")
        elif column in LONG_TEXT_COLUMNS:
            clauses.append(f"MODIFY {quoted} TEXT NULL")
        elif column in {"pre_break_value", "obs_pre_break", "reported_transaction"}:
            clauses.append(f"MODIFY {quoted} TEXT NULL")
        else:
            type_name = str(active_schema[column]["type"]).upper()
            if any(marker in type_name for marker in TEXT_TYPE_MARKERS):
                clauses.append(f"MODIFY {quoted} TEXT NULL")

    if import_key == "EURO_ATM_POS_TRANSACTIONS":
        clauses.append(
            "ADD UNIQUE KEY `uq_key_code_time_period` "
            "(`key_code`, `time_period`)"
        )
    else:
        clauses.append("ADD PRIMARY KEY (`key_code`, `time_period`)")
    clauses.append(f"ADD COLUMN `{HASH_COLUMN}` CHAR(64) NOT NULL")

    statements.append(f"ALTER TABLE `{shadow}` " + ", ".join(clauses))
    return tuple(statements)


def create_shadow_schema(engine, import_key, suffix, version="v055"):
    contract = get_macro_import(import_key)
    active = validate_identifier(contract["table_name"])
    shadow = shadow_table_name(active, suffix, version=version)
    if not _table_exists(engine, active):
        raise ValueError(f"Active table not found: {active}")
    if _table_exists(engine, shadow):
        raise ValueError(f"Shadow table already exists: {shadow}")
    statements = build_shadow_schema_statements(
        engine,
        import_key,
        suffix,
        version=version,
    )
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
    return shadow


def load_source_into_shadow(
    engine,
    import_key,
    shadow_table,
    chunk_size=5000,
    insert_batch_size=250,
    source_path=None,
):
    contract = get_macro_import(import_key)
    shadow_table = validate_identifier(shadow_table)
    columns = _mapped_source_columns(contract)
    insert_columns = columns + (HASH_COLUMN,)
    quoted_columns = ", ".join(f"`{column}`" for column in insert_columns)
    placeholders = ", ".join(f":{column}" for column in insert_columns)
    statement = text(
        f"INSERT INTO `{shadow_table}` ({quoted_columns}) VALUES ({placeholders})"
    )
    fingerprints = {}
    source_rows = 0
    non_null_values = 0
    invalid_numeric_rows = 0

    for raw_chunk in _source_chunks(
        contract,
        chunk_size,
        source_path=source_path,
    ):
        chunk = _normalize_source_frame(contract, raw_chunk, columns)
        records = []
        for values in chunk.itertuples(index=False, name=None):
            record, invalid_columns = normalize_row(columns, values)
            if invalid_columns:
                invalid_numeric_rows += 1
                continue
            key = tuple(record[column] for column in BUSINESS_KEY)
            if any(value is None for value in key):
                raise ValueError(f"Null source business key in {import_key}: {key}")
            if key in fingerprints:
                raise ValueError(f"Duplicate source business key in {import_key}: {key}")
            row_hash = canonical_row_hash(columns, record)
            record[HASH_COLUMN] = row_hash
            records.append(record)
            fingerprints[key] = row_hash
            source_rows += 1
            non_null_values += record.get("obs_value") is not None

        for batch in record_batches(records, insert_batch_size):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "SET SESSION sql_mode = "
                        "CONCAT_WS(',', @@sql_mode, 'STRICT_ALL_TABLES')"
                    )
                )
                connection.execute(statement, batch)

        if source_rows and source_rows % 50000 < len(records):
            print(f"  {import_key}: loaded {source_rows} source rows")

    if invalid_numeric_rows:
        raise ValueError(
            f"Invalid non-empty numeric rows in {import_key}: {invalid_numeric_rows}"
        )
    return columns, fingerprints, source_rows, non_null_values


def load_source_into_shadow_disk_backed(
    engine,
    import_key,
    shadow_table,
    fingerprint_store,
    chunk_size=5000,
    insert_batch_size=250,
    source_path=None,
):
    contract = get_macro_import(import_key)
    shadow_table = validate_identifier(shadow_table)
    columns = _mapped_source_columns(contract)
    insert_columns = columns + (HASH_COLUMN,)
    quoted_columns = ", ".join(f"`{column}`" for column in insert_columns)
    placeholders = ", ".join(f":{column}" for column in insert_columns)
    statement = text(
        f"INSERT INTO `{shadow_table}` ({quoted_columns}) VALUES ({placeholders})"
    )
    fingerprint_store.clear(SOURCE_DATASET)
    fingerprint_store.clear(TARGET_DATASET)
    source_rows = 0
    non_null_values = 0
    invalid_numeric_rows = 0

    for raw_chunk in _source_chunks(
        contract,
        chunk_size,
        source_path=source_path,
    ):
        chunk = _normalize_source_frame(contract, raw_chunk, columns)
        records = []
        fingerprints = []
        chunk_keys = set()
        for values in chunk.itertuples(index=False, name=None):
            record, invalid_columns = normalize_row(columns, values)
            if invalid_columns:
                invalid_numeric_rows += 1
                continue
            key = tuple(record[column] for column in BUSINESS_KEY)
            if any(value is None for value in key):
                raise ValueError(
                    f"Null source business key in {import_key}: {key}"
                )
            if key in chunk_keys:
                raise ValueError(
                    f"Duplicate source business key in {import_key}: {key}"
                )
            chunk_keys.add(key)
            row_hash = canonical_row_hash(columns, record)
            record[HASH_COLUMN] = row_hash
            records.append(record)
            fingerprints.append((key[0], key[1], bytes.fromhex(row_hash)))
            source_rows += 1
            non_null_values += record.get("obs_value") is not None

        fingerprint_store.insert_records(SOURCE_DATASET, fingerprints)
        for batch in record_batches(records, insert_batch_size):
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "SET SESSION sql_mode = "
                        "CONCAT_WS(',', @@sql_mode, 'STRICT_ALL_TABLES')"
                    )
                )
                connection.execute(statement, batch)

        if source_rows and source_rows % 50000 < len(records):
            print(f"  {import_key}: loaded {source_rows} source rows")

    if invalid_numeric_rows:
        raise ValueError(
            f"Invalid non-empty numeric rows in {import_key}: "
            f"{invalid_numeric_rows}"
        )
    source_summary = fingerprint_store.summary(SOURCE_DATASET)
    if source_summary["duplicate_groups"]:
        samples = fingerprint_store.key_samples("source_duplicate", 1)
        raise ValueError(
            f"Duplicate source business key in {import_key}: {samples[0]}"
        )
    if source_summary["unique_keys"] != source_rows:
        raise RuntimeError(f"Source fingerprint count mismatch: {import_key}")
    return columns, source_rows, non_null_values


def validate_shadow(
    engine,
    import_key,
    shadow_table,
    columns,
    fingerprints,
    source_non_null_values,
    database_write_performed=True,
):
    contract = get_macro_import(import_key)
    active = validate_identifier(contract["table_name"])
    shadow_table = validate_identifier(shadow_table)
    quoted_columns = ", ".join(f"`{column}`" for column in columns)
    summary_query = text(
        f"""
        SELECT
            COUNT(*) AS rows_count,
            COUNT(DISTINCT key_code, time_period) AS unique_business_keys,
            COUNT(obs_value) AS non_null_values,
            SUM(key_code IS NULL OR time_period IS NULL) AS null_business_keys,
            MIN(time_period) AS first_period,
            MAX(time_period) AS last_period
        FROM `{shadow_table}`
        """
    )
    duplicate_query = text(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT key_code, time_period
            FROM `{shadow_table}`
            GROUP BY key_code, time_period
            HAVING COUNT(*) > 1
        ) AS duplicate_keys
        """
    )
    data_query = text(
        f"SELECT {quoted_columns}, `{HASH_COLUMN}` "
        f"FROM `{shadow_table}` ORDER BY key_code, time_period"
    )

    expected = dict(fingerprints)
    row_hash_mismatches = 0
    source_hash_mismatches = 0
    with engine.connect() as connection:
        summary = connection.execute(summary_query).mappings().one()
        duplicate_groups = int(connection.execute(duplicate_query).scalar_one() or 0)
        result = connection.execution_options(stream_results=True).execute(data_query)
        for row in result.mappings():
            record = {column: row[column] for column in columns}
            actual_hash = canonical_row_hash(columns, record)
            stored_hash = row[HASH_COLUMN]
            if actual_hash != stored_hash:
                row_hash_mismatches += 1
            key = tuple(record[column] for column in BUSINESS_KEY)
            source_hash = expected.pop(key, None)
            if source_hash != stored_hash:
                source_hash_mismatches += 1

    validation = EuroRebuildValidation(
        import_key=import_key,
        active_table=active,
        shadow_table=shadow_table,
        source_rows=len(fingerprints),
        shadow_rows=int(summary["rows_count"] or 0),
        source_unique_business_keys=len(fingerprints),
        shadow_unique_business_keys=int(summary["unique_business_keys"] or 0),
        source_non_null_values=int(source_non_null_values),
        shadow_non_null_values=int(summary["non_null_values"] or 0),
        null_business_keys=int(summary["null_business_keys"] or 0),
        duplicate_business_key_groups=duplicate_groups,
        row_hash_mismatches=row_hash_mismatches,
        source_hash_mismatches=source_hash_mismatches,
        missing_source_rows=len(expected),
        first_period=summary["first_period"],
        last_period=summary["last_period"],
        source_columns=tuple(columns),
        database_write_performed=bool(database_write_performed),
    )
    if not _business_key_is_unique(engine, shadow_table):
        raise RuntimeError(f"Shadow business key is not unique: {shadow_table}")
    if not validation.valid:
        raise RuntimeError(
            "EURO shadow validation failed: "
            + json.dumps(validation.to_dict(), default=str)
        )
    return validation


def _shadow_value_batches(connection, query, output_columns, chunk_size):
    """Yield bounded shadow rows without mysqlconnector result buffering."""
    fetch_size = min(max(1, int(chunk_size)), MAX_SHADOW_FETCH_ROWS)
    dialect = connection.engine.dialect
    if dialect.name in {"mysql", "mariadb"} and dialect.driver == "mysqlconnector":
        driver_connection = connection.connection.driver_connection
        cursor = driver_connection.cursor(buffered=False)
        try:
            cursor.execute(query.text)
            while rows := cursor.fetchmany(fetch_size):
                yield rows
        finally:
            cursor.close()
        return

    result = connection.execution_options(
        stream_results=True,
        max_row_buffer=fetch_size,
    ).execute(query).mappings()
    try:
        while rows := result.fetchmany(fetch_size):
            yield [tuple(row[column] for column in output_columns) for row in rows]
    finally:
        result.close()


def validate_shadow_disk_backed(
    engine,
    import_key,
    shadow_table,
    columns,
    fingerprint_store,
    source_rows,
    source_non_null_values,
    chunk_size=5000,
    database_write_performed=True,
):
    if not isinstance(fingerprint_store, EuroFingerprintStore):
        raise TypeError("fingerprint_store must be EuroFingerprintStore")
    contract = get_macro_import(import_key)
    active = validate_identifier(contract["table_name"])
    shadow_table = validate_identifier(shadow_table)
    quoted_columns = ", ".join(f"`{column}`" for column in columns)
    summary_query = text(
        f"""
        SELECT
            COUNT(*) AS rows_count,
            COUNT(DISTINCT key_code, time_period) AS unique_business_keys,
            COUNT(obs_value) AS non_null_values,
            SUM(key_code IS NULL OR time_period IS NULL) AS null_business_keys,
            MIN(time_period) AS first_period,
            MAX(time_period) AS last_period
        FROM `{shadow_table}`
        """
    )
    duplicate_query = text(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT key_code, time_period
            FROM `{shadow_table}`
            GROUP BY key_code, time_period
            HAVING COUNT(*) > 1
        ) AS duplicate_keys
        """
    )
    data_query = text(
        f"SELECT {quoted_columns}, `{HASH_COLUMN}` FROM `{shadow_table}`"
    )
    output_columns = tuple(columns) + (HASH_COLUMN,)

    fingerprint_store.clear(TARGET_DATASET)
    row_hash_mismatches = 0
    row_hash_mismatch_samples = []
    streamed_shadow_rows = 0
    chunk_size = max(1, int(chunk_size))
    with engine.connect() as connection:
        summary = connection.execute(summary_query).mappings().one()
        duplicate_groups = int(
            connection.execute(duplicate_query).scalar_one() or 0
        )
        for rows in _shadow_value_batches(
            connection,
            data_query,
            output_columns,
            chunk_size,
        ):
            target_fingerprints = []
            for row in rows:
                record = dict(zip(columns, row[: len(columns)]))
                actual_hash = canonical_row_hash(columns, record)
                stored_hash = str(row[-1]).strip().upper()
                key = tuple(record[column] for column in BUSINESS_KEY)
                if actual_hash != stored_hash:
                    row_hash_mismatches += 1
                    if len(row_hash_mismatch_samples) < 10:
                        row_hash_mismatch_samples.append(
                            {
                                "key_code": key[0],
                                "time_period": key[1],
                                "stored_hash": stored_hash,
                                "actual_hash": actual_hash,
                            }
                        )
                if len(stored_hash) != 64:
                    raise ValueError(
                        f"Invalid stored row hash in {shadow_table}: {stored_hash}"
                    )
                try:
                    stored_hash_bytes = bytes.fromhex(stored_hash)
                except ValueError as exc:
                    raise ValueError(
                        f"Invalid stored row hash in {shadow_table}: {stored_hash}"
                    ) from exc
                if any(value is None for value in key):
                    raise ValueError(
                        f"Null shadow business key in {import_key}: {key}"
                    )
                target_fingerprints.append(
                    (key[0], key[1], stored_hash_bytes)
                )
                streamed_shadow_rows += 1
            fingerprint_store.insert_records(
                TARGET_DATASET,
                target_fingerprints,
            )

    source_summary = fingerprint_store.summary(SOURCE_DATASET)
    target_summary = fingerprint_store.summary(TARGET_DATASET)
    comparison = fingerprint_store.comparison()
    if source_summary["unique_keys"] != int(source_rows):
        raise RuntimeError(f"Source fingerprint count mismatch: {import_key}")
    if streamed_shadow_rows != int(summary["rows_count"] or 0):
        raise RuntimeError(f"Streamed shadow row mismatch: {shadow_table}")

    validation = EuroRebuildValidation(
        import_key=import_key,
        active_table=active,
        shadow_table=shadow_table,
        source_rows=int(source_rows),
        shadow_rows=int(summary["rows_count"] or 0),
        source_unique_business_keys=source_summary["unique_keys"],
        shadow_unique_business_keys=int(summary["unique_business_keys"] or 0),
        source_non_null_values=int(source_non_null_values),
        shadow_non_null_values=int(summary["non_null_values"] or 0),
        null_business_keys=int(summary["null_business_keys"] or 0),
        duplicate_business_key_groups=duplicate_groups,
        row_hash_mismatches=row_hash_mismatches,
        source_hash_mismatches=(
            comparison["row_hash_mismatches"]
            + comparison["target_rows_missing_from_source"]
        ),
        missing_source_rows=comparison["source_rows_missing_from_target"],
        first_period=summary["first_period"],
        last_period=summary["last_period"],
        source_columns=tuple(columns),
        database_write_performed=bool(database_write_performed),
        memory_bounded_validation=True,
        comparison_store_bytes=fingerprint_store.size_bytes,
        row_hash_mismatch_samples=tuple(row_hash_mismatch_samples),
    )
    if target_summary["duplicate_groups"] != duplicate_groups:
        raise RuntimeError(f"Shadow duplicate count mismatch: {shadow_table}")
    if target_summary["unique_keys"] != int(summary["unique_business_keys"] or 0):
        raise RuntimeError(f"Shadow fingerprint count mismatch: {shadow_table}")
    if not _business_key_is_unique(engine, shadow_table):
        raise RuntimeError(f"Shadow business key is not unique: {shadow_table}")
    if not validation.valid:
        raise RuntimeError(
            "EURO shadow validation failed: "
            + json.dumps(validation.to_dict(), default=str)
        )
    return validation


def build_and_validate_shadows(
    engine,
    backup_file,
    confirmation,
    suffix,
    chunk_size=5000,
    insert_batch_size=250,
    import_keys=TARGET_IMPORT_KEYS,
    version="v055",
    memory_bounded=False,
    workspace_dir=None,
    source_path_overrides=None,
):
    if confirmation != BUILD_CONFIRMATION:
        raise ValueError(f"--confirm must exactly match {BUILD_CONFIRMATION}")
    tables = tuple(get_macro_import(key)["table_name"] for key in import_keys)
    backup = validate_scoped_backup(backup_file, tables)
    validations = []
    source_path_overrides = {
        str(key).upper(): value
        for key, value in (source_path_overrides or {}).items()
    }
    unexpected_overrides = sorted(set(source_path_overrides) - set(import_keys))
    if unexpected_overrides:
        raise ValueError(
            f"Source overrides outside build scope: {unexpected_overrides}"
        )

    for import_key in import_keys:
        source_path = source_path_overrides.get(import_key)
        print(f"Building shadow: {import_key}")
        shadow = create_shadow_schema(
            engine,
            import_key,
            suffix,
            version=version,
        )
        if memory_bounded:
            with temporary_fingerprint_store(
                import_key,
                workspace_dir=workspace_dir,
            ) as fingerprint_store:
                columns, source_rows, non_null_values = (
                    load_source_into_shadow_disk_backed(
                        engine,
                        import_key,
                        shadow,
                        fingerprint_store,
                        chunk_size=chunk_size,
                        insert_batch_size=insert_batch_size,
                        source_path=source_path,
                    )
                )
                validation = validate_shadow_disk_backed(
                    engine,
                    import_key,
                    shadow,
                    columns,
                    fingerprint_store,
                    source_rows,
                    non_null_values,
                    chunk_size=chunk_size,
                )
        else:
            columns, fingerprints, _, non_null_values = (
                load_source_into_shadow(
                    engine,
                    import_key,
                    shadow,
                    chunk_size=chunk_size,
                    insert_batch_size=insert_batch_size,
                    source_path=source_path,
                )
            )
            validation = validate_shadow(
                engine,
                import_key,
                shadow,
                columns,
                fingerprints,
                non_null_values,
            )
        validations.append(validation)
        print(
            f"Validated shadow: {import_key} | "
            f"rows={validation.shadow_rows} | valid={validation.valid}"
        )

    return {
        "backup": backup,
        "validations": tuple(validations),
        "database_write_performed": True,
        "active_tables_changed": False,
        "memory_bounded_validation": bool(memory_bounded),
    }


def build_swap_statement(import_keys, suffix, version="v055"):
    pairs = []
    for import_key in import_keys:
        active = get_macro_import(import_key)["table_name"]
        shadow = shadow_table_name(active, suffix, version=version)
        retained = retained_table_name(active, suffix, version=version)
        pairs.extend(
            [
                f"`{active}` TO `{retained}`",
                f"`{shadow}` TO `{active}`",
            ]
        )
    return "RENAME TABLE " + ", ".join(pairs)


def build_rollback_statement(import_keys, suffix, version="v055"):
    pairs = []
    for import_key in import_keys:
        active = get_macro_import(import_key)["table_name"]
        retained = retained_table_name(active, suffix, version=version)
        failed = failed_table_name(active, suffix, version=version)
        pairs.extend(
            [
                f"`{active}` TO `{failed}`",
                f"`{retained}` TO `{active}`",
            ]
        )
    return "RENAME TABLE " + ", ".join(pairs)


def _post_swap_summary(engine, table_name):
    table_name = validate_identifier(table_name)
    query = text(
        f"""
        SELECT
            COUNT(*) AS rows_count,
            COUNT(DISTINCT key_code, time_period) AS unique_business_keys,
            SUM(key_code IS NULL OR time_period IS NULL) AS null_business_keys,
            MIN(time_period) AS first_period,
            MAX(time_period) AS last_period
        FROM `{table_name}`
        """
    )
    with engine.connect() as connection:
        return dict(connection.execute(query).mappings().one())


def validate_existing_shadows(
    engine,
    suffix,
    chunk_size,
    import_keys,
    version="v055",
    memory_bounded=False,
    workspace_dir=None,
    source_path_overrides=None,
):
    validations = []
    source_path_overrides = {
        str(key).upper(): value
        for key, value in (source_path_overrides or {}).items()
    }
    unexpected_overrides = sorted(set(source_path_overrides) - set(import_keys))
    if unexpected_overrides:
        raise ValueError(
            f"Source overrides outside validation scope: {unexpected_overrides}"
        )
    for import_key in import_keys:
        source_path = source_path_overrides.get(import_key)
        active = get_macro_import(import_key)["table_name"]
        shadow = shadow_table_name(active, suffix, version=version)
        if not _table_exists(engine, shadow):
            raise ValueError(f"Validated shadow table not found: {shadow}")
        if memory_bounded:
            with temporary_fingerprint_store(
                import_key,
                workspace_dir=workspace_dir,
            ) as fingerprint_store:
                columns, source_rows, non_null_values = (
                    source_fingerprints_to_store(
                        import_key,
                        fingerprint_store,
                        chunk_size=chunk_size,
                        source_path=source_path,
                    )
                )
                validations.append(
                    validate_shadow_disk_backed(
                        engine,
                        import_key,
                        shadow,
                        columns,
                        fingerprint_store,
                        source_rows,
                        non_null_values,
                        chunk_size=chunk_size,
                        database_write_performed=False,
                    )
                )
        else:
            columns, fingerprints, non_null_values = source_fingerprints(
                import_key,
                chunk_size=chunk_size,
                source_path=source_path,
            )
            validations.append(
                validate_shadow(
                    engine,
                    import_key,
                    shadow,
                    columns,
                    fingerprints,
                    non_null_values,
                    database_write_performed=False,
                )
            )
    return tuple(validations)


def swap_validated_shadows(
    engine,
    backup_file,
    confirmation,
    suffix,
    chunk_size=5000,
    import_keys=TARGET_IMPORT_KEYS,
    version="v055",
    memory_bounded=False,
    workspace_dir=None,
    drop_hash_before_swap=True,
    post_swap_validator=None,
    post_hash_drop_validator=None,
    source_path_overrides=None,
):
    if confirmation != SWAP_CONFIRMATION:
        raise ValueError(f"--confirm must exactly match {SWAP_CONFIRMATION}")
    tables = tuple(get_macro_import(key)["table_name"] for key in import_keys)
    backup = validate_scoped_backup(backup_file, tables)

    for import_key in import_keys:
        active = get_macro_import(import_key)["table_name"]
        retained = retained_table_name(active, suffix, version=version)
        failed = failed_table_name(active, suffix, version=version)
        if not _table_exists(engine, active):
            raise ValueError(f"Active table not found: {active}")
        if _table_exists(engine, retained):
            raise ValueError(f"Retained table already exists: {retained}")
        if _table_exists(engine, failed):
            raise ValueError(f"Failed-table name already exists: {failed}")

    validations = validate_existing_shadows(
        engine,
        suffix,
        chunk_size,
        import_keys,
        version=version,
        memory_bounded=memory_bounded,
        workspace_dir=workspace_dir,
        source_path_overrides=source_path_overrides,
    )
    expected_rows = {
        validation.active_table: validation.source_rows
        for validation in validations
    }

    if drop_hash_before_swap:
        for validation in validations:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        f"ALTER TABLE `{validation.shadow_table}` "
                        f"DROP COLUMN `{HASH_COLUMN}`"
                    )
                )

    swap_statement = build_swap_statement(
        import_keys,
        suffix,
        version=version,
    )
    rollback_statement = build_rollback_statement(
        import_keys,
        suffix,
        version=version,
    )
    retained_tables = tuple(
        retained_table_name(table_name, suffix, version=version)
        for table_name in tables
    )
    with engine.begin() as connection:
        connection.execute(text(swap_statement))

    try:
        final_summaries = {}
        for table_name in tables:
            summary = _post_swap_summary(engine, table_name)
            final_summaries[table_name] = summary
            if int(summary["rows_count"] or 0) != expected_rows[table_name]:
                raise RuntimeError(f"Post-swap row mismatch: {table_name}")
            if int(summary["unique_business_keys"] or 0) != expected_rows[table_name]:
                raise RuntimeError(f"Post-swap unique-key mismatch: {table_name}")
            if int(summary["null_business_keys"] or 0) != 0:
                raise RuntimeError(f"Post-swap null business keys: {table_name}")
            if not _business_key_is_unique(engine, table_name):
                raise RuntimeError(f"Post-swap unique key missing: {table_name}")
            time_column = next(
                column
                for column in inspect(engine).get_columns(table_name)
                if normalize_column_name(column["name"]) == "time_period"
            )
            if "CHAR" not in str(time_column["type"]).upper():
                raise RuntimeError(f"Post-swap period type is lossy: {table_name}")
        if post_swap_validator is not None:
            post_swap_validator(
                engine=engine,
                validations=validations,
                retained_tables=retained_tables,
            )
        if not drop_hash_before_swap:
            for validation in validations:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            f"ALTER TABLE `{validation.active_table}` "
                            f"DROP COLUMN `{HASH_COLUMN}`"
                        )
                    )
                active_columns = {
                    normalize_column_name(column["name"])
                    for column in inspect(engine).get_columns(
                        validation.active_table
                    )
                }
                if HASH_COLUMN in active_columns:
                    raise RuntimeError(
                        f"Post-swap hash column remains: {validation.active_table}"
                    )
        if post_hash_drop_validator is not None:
            post_hash_drop_validator(
                engine=engine,
                validations=validations,
                retained_tables=retained_tables,
            )
    except Exception:
        with engine.begin() as connection:
            connection.execute(text(rollback_statement))
        raise

    return {
        "backup": backup,
        "validations": validations,
        "final_summaries": final_summaries,
        "swap_statement": swap_statement,
        "rollback_statement": rollback_statement,
        "database_write_performed": True,
        "active_tables_changed": True,
        "memory_bounded_validation": bool(memory_bounded),
        "retained_tables": retained_tables,
        "hash_column_drop_stage": (
            "before_swap" if drop_hash_before_swap else "after_validation"
        ),
    }
