from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.euro_fingerprint_store import temporary_fingerprint_store
from services.euro_rebuild_service import (
    BUSINESS_KEY,
    mapped_source_columns,
    normalize_row,
    normalize_source_frame,
    record_batches,
    source_chunks,
)
from services.euro_streaming_validation_service import (
    DEFAULT_CHUNK_SIZE,
    MIN_WORKSPACE_FREE_BYTES,
    audit_euro_source_against_target,
)
from services.macro_import_service import validate_sql_backup_for_table
from services.market_data_sync_service import validate_identifier


SYNC_VERSION = "v064"
TARGET_ONLY_POLICY = "reject"
SOURCE_NULL_POLICY = "authoritative_overwrite"
DELETION_POLICY = "disabled"


@dataclass(frozen=True)
class EuroSyncPlan:
    import_key: str
    table_name: str
    source_path: str
    source_bytes: int
    source_modified_ns: int
    source_columns: tuple[str, ...]
    source_rows: int
    target_rows: int
    source_unique_business_keys: int
    target_unique_business_keys: int
    planned_inserts: int
    planned_updates: int
    unchanged_rows: int
    target_only_rows: int
    planned_deletes: int
    expected_rows_after_apply: int
    unique_business_key_available: bool
    source_null_business_keys: int
    source_invalid_numeric_rows: int
    source_duplicate_business_key_groups: int
    target_null_business_keys: int
    target_invalid_numeric_rows: int
    target_duplicate_business_key_groups: int
    target_only_policy: str
    source_null_policy: str
    deletion_policy: str
    blockers: tuple[str, ...]
    missing_source_key_samples: tuple[dict, ...]
    mismatch_key_samples: tuple[dict, ...]
    extra_target_key_samples: tuple[dict, ...]
    database_write_performed: bool = False

    @property
    def write_ready(self):
        return not self.blockers

    @property
    def idempotent(self):
        return (
            self.write_ready
            and self.planned_inserts == 0
            and self.planned_updates == 0
            and self.target_only_rows == 0
        )

    def to_dict(self):
        output = asdict(self)
        output["write_ready"] = self.write_ready
        output["idempotent"] = self.idempotent
        return output


def sync_confirmation(import_key):
    key = str(import_key).upper()
    contract = get_macro_import(key)
    if contract.get("group") != "EURO":
        raise ValueError(f"Not a EURO import contract: {key}")
    return f"APPLY_{key}_{SYNC_VERSION.upper()}_TRANSACTIONAL_SYNC"


def _has_unique_business_key(engine, table_name):
    table_name = validate_identifier(table_name)
    inspector = inspect(engine)
    candidates = []
    primary = inspector.get_pk_constraint(table_name).get("constrained_columns") or []
    if primary:
        candidates.append(tuple(str(column).lower() for column in primary))
    for constraint in inspector.get_unique_constraints(table_name):
        columns = constraint.get("column_names") or []
        if columns:
            candidates.append(tuple(str(column).lower() for column in columns))
    for index in inspector.get_indexes(table_name):
        columns = index.get("column_names") or []
        if index.get("unique") and columns:
            candidates.append(tuple(str(column).lower() for column in columns))
    return BUSINESS_KEY in candidates


def _source_metadata(path):
    stat = Path(path).stat()
    return int(stat.st_size), int(stat.st_mtime_ns)


def _plan_from_validation(validation, unique_business_key, source_metadata):
    blockers = []
    quality_checks = (
        (validation.source_null_business_keys, "source_null_business_keys"),
        (validation.source_invalid_numeric_rows, "source_invalid_numeric_rows"),
        (
            validation.source_duplicate_business_key_groups,
            "source_duplicate_business_keys",
        ),
        (validation.target_null_business_keys, "target_null_business_keys"),
        (validation.target_invalid_numeric_rows, "target_invalid_numeric_rows"),
        (
            validation.target_duplicate_business_key_groups,
            "target_duplicate_business_keys",
        ),
    )
    blockers.extend(reason for count, reason in quality_checks if count)
    if not unique_business_key:
        blockers.append("unique_business_key_missing")
    if validation.target_rows_missing_from_source:
        blockers.append("target_only_rows_require_review")

    planned_inserts = validation.source_rows_missing_from_target
    planned_updates = validation.row_hash_mismatches
    unchanged_rows = max(
        0,
        validation.source_unique_business_keys
        - planned_inserts
        - planned_updates,
    )
    source_bytes, source_modified_ns = source_metadata
    return EuroSyncPlan(
        import_key=validation.import_key,
        table_name=validation.target_table,
        source_path=validation.source_path,
        source_bytes=source_bytes,
        source_modified_ns=source_modified_ns,
        source_columns=validation.source_columns,
        source_rows=validation.source_rows,
        target_rows=validation.target_rows,
        source_unique_business_keys=validation.source_unique_business_keys,
        target_unique_business_keys=validation.target_unique_business_keys,
        planned_inserts=planned_inserts,
        planned_updates=planned_updates,
        unchanged_rows=unchanged_rows,
        target_only_rows=validation.target_rows_missing_from_source,
        planned_deletes=0,
        expected_rows_after_apply=validation.target_rows + planned_inserts,
        unique_business_key_available=bool(unique_business_key),
        source_null_business_keys=validation.source_null_business_keys,
        source_invalid_numeric_rows=validation.source_invalid_numeric_rows,
        source_duplicate_business_key_groups=(
            validation.source_duplicate_business_key_groups
        ),
        target_null_business_keys=validation.target_null_business_keys,
        target_invalid_numeric_rows=validation.target_invalid_numeric_rows,
        target_duplicate_business_key_groups=(
            validation.target_duplicate_business_key_groups
        ),
        target_only_policy=TARGET_ONLY_POLICY,
        source_null_policy=SOURCE_NULL_POLICY,
        deletion_policy=DELETION_POLICY,
        blockers=tuple(blockers),
        missing_source_key_samples=validation.missing_source_key_samples,
        mismatch_key_samples=validation.mismatch_key_samples,
        extra_target_key_samples=validation.extra_target_key_samples,
    )


def build_euro_sync_plan(
    engine,
    import_key,
    *,
    chunk_size=DEFAULT_CHUNK_SIZE,
    workspace_dir=None,
    sample_limit=10,
    minimum_free_bytes=MIN_WORKSPACE_FREE_BYTES,
    source_path=None,
    progress_callback=None,
):
    key = str(import_key).upper()
    contract = get_macro_import(key)
    if contract.get("group") != "EURO":
        raise ValueError(f"Not a EURO import contract: {key}")
    path = Path(source_path or contract["csv_path"]).expanduser().resolve()
    metadata_before = _source_metadata(path)
    validation = audit_euro_source_against_target(
        engine,
        key,
        chunk_size=chunk_size,
        workspace_dir=workspace_dir,
        sample_limit=sample_limit,
        minimum_free_bytes=minimum_free_bytes,
        progress_callback=progress_callback,
        source_path=path,
    )
    plan = _plan_from_validation(
        validation,
        _has_unique_business_key(engine, contract["table_name"]),
        metadata_before,
    )
    if _source_metadata(path) != metadata_before:
        plan = EuroSyncPlan(
            **{
                **asdict(plan),
                "blockers": (*plan.blockers, "source_changed_during_preflight"),
            }
        )
    return plan


def _sql_value(value, dialect_name):
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Decimal) and dialect_name == "sqlite":
        return format(value, "f")
    return value


def _upsert_statement(engine, table_name, columns):
    table_name = validate_identifier(table_name)
    columns = tuple(validate_identifier(column) for column in columns)
    update_columns = [column for column in columns if column not in BUSINESS_KEY]
    if not update_columns:
        raise ValueError("EURO synchronization requires non-key columns")
    column_sql = ", ".join(f"`{column}`" for column in columns)
    values_sql = ", ".join(f":{column}" for column in columns)
    dialect = engine.dialect.name
    if dialect in {"mysql", "mariadb"}:
        update_sql = ", ".join(
            f"`{column}` = VALUES(`{column}`)" for column in update_columns
        )
        suffix = f"ON DUPLICATE KEY UPDATE {update_sql}"
    elif dialect == "sqlite":
        key_sql = ", ".join(f"`{column}`" for column in BUSINESS_KEY)
        update_sql = ", ".join(
            f"`{column}` = excluded.`{column}`" for column in update_columns
        )
        suffix = f"ON CONFLICT ({key_sql}) DO UPDATE SET {update_sql}"
    else:
        raise ValueError(f"Unsupported EURO sync SQL dialect: {dialect}")
    return text(
        f"INSERT INTO `{table_name}` ({column_sql}) VALUES ({values_sql}) {suffix}"
    )


def apply_euro_sync(
    engine,
    import_key,
    *,
    backup_file,
    confirmation,
    chunk_size=DEFAULT_CHUNK_SIZE,
    insert_batch_size=250,
    workspace_dir=None,
    minimum_free_bytes=MIN_WORKSPACE_FREE_BYTES,
    source_path=None,
    progress_callback=None,
):
    key = str(import_key).upper()
    contract = get_macro_import(key)
    if contract.get("group") != "EURO":
        raise ValueError(f"Not a EURO import contract: {key}")
    expected_confirmation = sync_confirmation(key)
    if confirmation != expected_confirmation:
        raise ValueError(f"Confirmation must exactly match {expected_confirmation}")

    table_name = validate_identifier(contract["table_name"])
    backup = validate_sql_backup_for_table(backup_file, table_name)
    path = Path(source_path or contract["csv_path"]).expanduser().resolve()
    metadata_before = _source_metadata(path)
    columns = mapped_source_columns({**contract, "csv_path": path})
    statement = _upsert_statement(engine, table_name, columns)
    dialect_name = engine.dialect.name

    with temporary_fingerprint_store(
        key,
        workspace_dir=workspace_dir,
        minimum_free_bytes=minimum_free_bytes,
    ) as store:
        validation = audit_euro_source_against_target(
            engine,
            key,
            chunk_size=chunk_size,
            sample_limit=10,
            minimum_free_bytes=minimum_free_bytes,
            progress_callback=progress_callback,
            fingerprint_store=store,
            source_path=path,
        )
        plan = _plan_from_validation(
            validation,
            _has_unique_business_key(engine, table_name),
            metadata_before,
        )
        if _source_metadata(path) != metadata_before:
            raise RuntimeError("EURO source changed during synchronization preflight")
        if not plan.write_ready:
            raise RuntimeError(
                "EURO synchronization is blocked: " + ", ".join(plan.blockers)
            )
        planned_writes = plan.planned_inserts + plan.planned_updates
        if planned_writes == 0:
            return {
                "plan": plan.to_dict(),
                "written_rows": 0,
                "post_validation_valid": True,
                "backup_sha256": backup["sha256"],
                "database_write_performed": False,
            }

        written_rows = 0
        with engine.begin() as connection:
            for raw_chunk in source_chunks(
                {**contract, "csv_path": path},
                chunk_size,
            ):
                chunk = normalize_source_frame(contract, raw_chunk, columns)
                records = []
                keys = []
                for values in chunk.itertuples(index=False, name=None):
                    record, invalid_columns = normalize_row(columns, values)
                    if invalid_columns:
                        raise RuntimeError(
                            "Source changed after preflight; invalid numeric values found"
                        )
                    key_values = tuple(record[column] for column in BUSINESS_KEY)
                    if any(value is None for value in key_values):
                        raise RuntimeError(
                            "Source changed after preflight; null business key found"
                        )
                    keys.append(key_values)
                    records.append(record)
                actions = store.actions_for_keys(keys)
                actionable = [
                    {
                        column: _sql_value(record[column], dialect_name)
                        for column in columns
                    }
                    for record, key_values in zip(records, keys)
                    if actions.get(key_values) in {"insert", "update"}
                ]
                for batch in record_batches(actionable, insert_batch_size):
                    connection.execute(statement, batch)
                    written_rows += len(batch)
                if progress_callback:
                    progress_callback("write", key, written_rows)

            if written_rows != planned_writes:
                raise RuntimeError(
                    "Planned and written EURO row counts differ: "
                    f"planned={planned_writes}, written={written_rows}"
                )
            if _source_metadata(path) != metadata_before:
                raise RuntimeError("EURO source changed during transaction")
            post_validation = audit_euro_source_against_target(
                engine,
                key,
                chunk_size=chunk_size,
                sample_limit=10,
                minimum_free_bytes=minimum_free_bytes,
                progress_callback=progress_callback,
                fingerprint_store=store,
                sql_connection=connection,
                source_path=path,
            )
            if _source_metadata(path) != metadata_before:
                raise RuntimeError("EURO source changed during post-write validation")
            if not post_validation.valid:
                raise RuntimeError(
                    "Post-write EURO validation failed; transaction rolled back"
                )

    return {
        "plan": plan.to_dict(),
        "written_rows": written_rows,
        "post_validation_valid": True,
        "backup_sha256": backup["sha256"],
        "database_write_performed": True,
    }
