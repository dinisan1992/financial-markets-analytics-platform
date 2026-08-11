from __future__ import annotations

from contextlib import nullcontext
from dataclasses import asdict, dataclass
from pathlib import Path
import shutil
from time import perf_counter

from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.euro_rebuild_service import (
    BUSINESS_KEY,
    canonical_row_hash,
    mapped_source_columns,
    normalize_row,
    normalize_source_frame,
    source_chunks,
)
from services.euro_fingerprint_store import (
    SOURCE_DATASET,
    TARGET_DATASET,
    temporary_fingerprint_store,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


TARGET_IMPORT_KEYS = (
    "EURO_CONSUMER_PRICES",
    "EURO_NATIONAL_ACCOUNTS",
    "EURO_MFI_INTEREST_RATES",
)
DEFAULT_CHUNK_SIZE = 25_000
DEFAULT_SAMPLE_LIMIT = 10
MIN_WORKSPACE_FREE_BYTES = 2 * 1024**3
MAX_TARGET_FETCH_ROWS = 5_000


@dataclass(frozen=True)
class EuroStreamingValidation:
    import_key: str
    target_table: str
    source_path: str
    source_columns: tuple[str, ...]
    source_rows: int
    target_rows: int
    source_unique_business_keys: int
    target_unique_business_keys: int
    source_non_null_values: int
    target_non_null_values: int
    source_null_business_keys: int
    target_null_business_keys: int
    source_invalid_numeric_rows: int
    target_invalid_numeric_rows: int
    source_duplicate_business_key_groups: int
    target_duplicate_business_key_groups: int
    source_duplicate_rows: int
    target_duplicate_rows: int
    source_duplicate_hash_conflicts: int
    target_duplicate_hash_conflicts: int
    source_rows_missing_from_target: int
    target_rows_missing_from_source: int
    row_hash_mismatches: int
    source_first_period: str | None
    source_last_period: str | None
    target_first_period: str | None
    target_last_period: str | None
    chunk_size: int
    max_source_chunk_rows: int
    max_target_chunk_rows: int
    comparison_store_bytes: int
    free_disk_bytes_before: int
    free_disk_bytes_after: int
    elapsed_seconds: float
    missing_source_key_samples: tuple[dict, ...]
    extra_target_key_samples: tuple[dict, ...]
    mismatch_key_samples: tuple[dict, ...]
    source_duplicate_key_samples: tuple[dict, ...]
    target_duplicate_key_samples: tuple[dict, ...]
    database_write_performed: bool = False

    @property
    def valid(self):
        return (
            self.source_rows == self.target_rows
            and self.source_rows == self.source_unique_business_keys
            and self.target_rows == self.target_unique_business_keys
            and self.source_non_null_values == self.target_non_null_values
            and self.source_null_business_keys == 0
            and self.target_null_business_keys == 0
            and self.source_invalid_numeric_rows == 0
            and self.target_invalid_numeric_rows == 0
            and self.source_duplicate_business_key_groups == 0
            and self.target_duplicate_business_key_groups == 0
            and self.source_duplicate_rows == 0
            and self.target_duplicate_rows == 0
            and self.source_duplicate_hash_conflicts == 0
            and self.target_duplicate_hash_conflicts == 0
            and self.source_rows_missing_from_target == 0
            and self.target_rows_missing_from_source == 0
            and self.row_hash_mismatches == 0
        )

    def to_dict(self):
        output = asdict(self)
        output["valid"] = self.valid
        return output


def _target_query(engine, table_name, columns):
    table_name = validate_identifier(table_name)
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        raise ValueError(f"Target table not found: {table_name}")

    actual_columns = {
        normalize_column_name(column["name"]): column["name"]
        for column in inspector.get_columns(table_name)
    }
    missing = sorted(set(columns) - set(actual_columns))
    if missing:
        raise ValueError(
            f"Target table {table_name} is missing source columns: {missing}"
        )
    selections = []
    for column in columns:
        actual = validate_identifier(actual_columns[column])
        alias = validate_identifier(column)
        selections.append(f"`{actual}` AS `{alias}`")
    return text(f"SELECT {', '.join(selections)} FROM `{table_name}`")


def _target_value_batches(connection, query, columns, chunk_size):
    """Yield bounded target tuples, including with buffered mysqlconnector."""
    fetch_size = min(max(1, int(chunk_size)), MAX_TARGET_FETCH_ROWS)
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
            yield [tuple(row[column] for column in columns) for row in rows]
    finally:
        result.close()


def audit_euro_source_against_target(
    engine,
    import_key,
    *,
    chunk_size=DEFAULT_CHUNK_SIZE,
    workspace_dir=None,
    sample_limit=DEFAULT_SAMPLE_LIMIT,
    minimum_free_bytes=MIN_WORKSPACE_FREE_BYTES,
    progress_callback=None,
    fingerprint_store=None,
    sql_connection=None,
    source_path=None,
):
    """Compare one EURO CSV with its SQL table without writing to SQL."""
    started = perf_counter()
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
    chunk_size = max(1, int(chunk_size))
    sample_limit = max(0, int(sample_limit))
    columns = mapped_source_columns(contract)
    target_table = validate_identifier(contract["table_name"])
    target_query = _target_query(sql_connection or engine, target_table, columns)

    source_rows = 0
    target_rows = 0
    source_non_null = 0
    target_non_null = 0
    source_null_keys = 0
    target_null_keys = 0
    source_invalid_numeric = 0
    target_invalid_numeric = 0
    max_source_chunk_rows = 0
    max_target_chunk_rows = 0

    store_context = (
        nullcontext(fingerprint_store)
        if fingerprint_store is not None
        else temporary_fingerprint_store(
            import_key,
            workspace_dir=workspace_dir,
            minimum_free_bytes=minimum_free_bytes,
        )
    )
    with store_context as store:
        if store is None:
            raise TypeError("fingerprint_store cannot be None")
        store.clear(SOURCE_DATASET)
        store.clear(TARGET_DATASET)
        free_before = store.free_disk_bytes_before
        workspace_root = store.workspace_root
        with store.connection:
            for raw_chunk in source_chunks(contract, chunk_size):
                chunk = normalize_source_frame(contract, raw_chunk, columns)
                max_source_chunk_rows = max(max_source_chunk_rows, len(chunk))
                records = []
                for values in chunk.itertuples(index=False, name=None):
                    source_rows += 1
                    record, invalid_columns = normalize_row(columns, values)
                    if invalid_columns:
                        source_invalid_numeric += 1
                        continue
                    source_non_null += record.get("obs_value") is not None
                    key = tuple(record[column] for column in BUSINESS_KEY)
                    if any(value is None for value in key):
                        source_null_keys += 1
                        continue
                    records.append(
                        (
                            key[0],
                            key[1],
                            bytes.fromhex(canonical_row_hash(columns, record)),
                        )
                    )
                store.insert_records(SOURCE_DATASET, records)
                if progress_callback:
                    progress_callback("source", import_key, source_rows)

            connection_context = (
                nullcontext(sql_connection)
                if sql_connection is not None
                else engine.connect()
            )
            with connection_context as target_connection:
                for rows in _target_value_batches(
                    target_connection,
                    target_query,
                    columns,
                    chunk_size,
                ):
                    max_target_chunk_rows = max(max_target_chunk_rows, len(rows))
                    records = []
                    for values in rows:
                        target_rows += 1
                        record, invalid_columns = normalize_row(columns, values)
                        if invalid_columns:
                            target_invalid_numeric += 1
                            continue
                        target_non_null += record.get("obs_value") is not None
                        key = tuple(record[column] for column in BUSINESS_KEY)
                        if any(value is None for value in key):
                            target_null_keys += 1
                            continue
                        records.append(
                            (
                                key[0],
                                key[1],
                                bytes.fromhex(canonical_row_hash(columns, record)),
                            )
                        )
                    store.insert_records(TARGET_DATASET, records)
                    if progress_callback:
                        progress_callback("target", import_key, target_rows)

            source_summary = store.summary(SOURCE_DATASET)
            target_summary = store.summary(TARGET_DATASET)
            comparison = store.comparison()
            source_missing = comparison["source_rows_missing_from_target"]
            target_extra = comparison["target_rows_missing_from_source"]
            mismatches = comparison["row_hash_mismatches"]
            store_bytes = store.size_bytes

            missing_samples = store.key_samples("missing", sample_limit)
            extra_samples = store.key_samples("extra", sample_limit)
            mismatch_samples = store.key_samples("mismatch", sample_limit)
            source_duplicate_samples = store.key_samples(
                "source_duplicate",
                sample_limit,
            )
            target_duplicate_samples = store.key_samples(
                "target_duplicate",
                sample_limit,
            )

    free_after = shutil.disk_usage(workspace_root).free
    return EuroStreamingValidation(
        import_key=import_key,
        target_table=target_table,
        source_path=str(source_path),
        source_columns=tuple(columns),
        source_rows=source_rows,
        target_rows=target_rows,
        source_unique_business_keys=source_summary["unique_keys"],
        target_unique_business_keys=target_summary["unique_keys"],
        source_non_null_values=source_non_null,
        target_non_null_values=target_non_null,
        source_null_business_keys=source_null_keys,
        target_null_business_keys=target_null_keys,
        source_invalid_numeric_rows=source_invalid_numeric,
        target_invalid_numeric_rows=target_invalid_numeric,
        source_duplicate_business_key_groups=source_summary["duplicate_groups"],
        target_duplicate_business_key_groups=target_summary["duplicate_groups"],
        source_duplicate_rows=source_summary["duplicate_rows"],
        target_duplicate_rows=target_summary["duplicate_rows"],
        source_duplicate_hash_conflicts=source_summary["hash_conflicts"],
        target_duplicate_hash_conflicts=target_summary["hash_conflicts"],
        source_rows_missing_from_target=source_missing,
        target_rows_missing_from_source=target_extra,
        row_hash_mismatches=mismatches,
        source_first_period=source_summary["first_period"],
        source_last_period=source_summary["last_period"],
        target_first_period=target_summary["first_period"],
        target_last_period=target_summary["last_period"],
        chunk_size=chunk_size,
        max_source_chunk_rows=max_source_chunk_rows,
        max_target_chunk_rows=max_target_chunk_rows,
        comparison_store_bytes=store_bytes,
        free_disk_bytes_before=free_before,
        free_disk_bytes_after=free_after,
        elapsed_seconds=round(perf_counter() - started, 3),
        missing_source_key_samples=missing_samples,
        extra_target_key_samples=extra_samples,
        mismatch_key_samples=mismatch_samples,
        source_duplicate_key_samples=source_duplicate_samples,
        target_duplicate_key_samples=target_duplicate_samples,
        database_write_performed=False,
    )
