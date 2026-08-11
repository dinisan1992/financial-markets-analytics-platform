from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory, gettempdir
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


def _create_comparison_store(path):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute("PRAGMA cache_size=-65536")
    for name in ("source_rows", "target_rows"):
        connection.execute(
            f"""
            CREATE TABLE {name} (
                key_code TEXT NOT NULL,
                time_period TEXT NOT NULL,
                row_hash BLOB NOT NULL,
                occurrences INTEGER NOT NULL DEFAULT 1,
                hash_conflicts INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (key_code, time_period)
            ) WITHOUT ROWID
            """
        )
    connection.commit()
    return connection


def _insert_records(connection, table_name, records):
    if not records:
        return
    connection.executemany(
        f"""
        INSERT INTO {table_name} (key_code, time_period, row_hash)
        VALUES (?, ?, ?)
        ON CONFLICT(key_code, time_period) DO UPDATE SET
            occurrences = occurrences + 1,
            hash_conflicts = hash_conflicts +
                CASE WHEN row_hash <> excluded.row_hash THEN 1 ELSE 0 END
        """,
        records,
    )
    connection.commit()


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


def _store_summary(connection, table_name):
    row = connection.execute(
        f"""
        SELECT
            COUNT(*) AS unique_keys,
            COALESCE(SUM(occurrences - 1), 0) AS duplicate_rows,
            COALESCE(SUM(occurrences > 1), 0) AS duplicate_groups,
            COALESCE(SUM(hash_conflicts), 0) AS hash_conflicts,
            MIN(time_period) AS first_period,
            MAX(time_period) AS last_period
        FROM {table_name}
        """
    ).fetchone()
    return {
        "unique_keys": int(row[0] or 0),
        "duplicate_rows": int(row[1] or 0),
        "duplicate_groups": int(row[2] or 0),
        "hash_conflicts": int(row[3] or 0),
        "first_period": row[4],
        "last_period": row[5],
    }


def _count(connection, query):
    return int(connection.execute(query).fetchone()[0] or 0)


def _key_samples(connection, query, limit):
    rows = connection.execute(query, (max(0, int(limit)),)).fetchall()
    return tuple({"key_code": row[0], "time_period": row[1]} for row in rows)


def _workspace_size(connection):
    page_count = int(connection.execute("PRAGMA page_count").fetchone()[0])
    page_size = int(connection.execute("PRAGMA page_size").fetchone()[0])
    return page_count * page_size


def audit_euro_source_against_target(
    engine,
    import_key,
    *,
    chunk_size=DEFAULT_CHUNK_SIZE,
    workspace_dir=None,
    sample_limit=DEFAULT_SAMPLE_LIMIT,
    minimum_free_bytes=MIN_WORKSPACE_FREE_BYTES,
    progress_callback=None,
):
    """Compare one EURO CSV with its SQL table without writing to SQL."""
    started = perf_counter()
    import_key = str(import_key).upper()
    contract = get_macro_import(import_key)
    if contract.get("group") != "EURO":
        raise ValueError(f"Not a EURO import contract: {import_key}")

    source_path = Path(contract["csv_path"]).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"EURO source CSV not found: {source_path}")
    chunk_size = max(1, int(chunk_size))
    sample_limit = max(0, int(sample_limit))
    columns = mapped_source_columns(contract)
    target_table = validate_identifier(contract["table_name"])
    target_query = _target_query(engine, target_table, columns)

    workspace_root = (
        Path(workspace_dir).expanduser().resolve()
        if workspace_dir is not None
        else Path(gettempdir()).resolve()
    )
    if not workspace_root.is_dir():
        raise FileNotFoundError(f"Audit workspace does not exist: {workspace_root}")
    free_before = shutil.disk_usage(workspace_root).free
    if free_before < max(0, int(minimum_free_bytes)):
        raise OSError(
            f"Insufficient free space for streaming audit: {free_before} bytes"
        )

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

    with TemporaryDirectory(
        prefix=f"euro_audit_{import_key.lower()}_",
        dir=workspace_root,
    ) as temp_dir:
        store_path = Path(temp_dir) / "comparison.sqlite3"
        store = _create_comparison_store(store_path)
        try:
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
                _insert_records(store, "source_rows", records)
                if progress_callback:
                    progress_callback("source", import_key, source_rows)

            with engine.connect() as sql_connection:
                result = sql_connection.execution_options(
                    stream_results=True,
                    max_row_buffer=chunk_size,
                ).execute(target_query).mappings()
                while rows := result.fetchmany(chunk_size):
                    max_target_chunk_rows = max(max_target_chunk_rows, len(rows))
                    records = []
                    for row in rows:
                        target_rows += 1
                        values = tuple(row[column] for column in columns)
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
                    _insert_records(store, "target_rows", records)
                    if progress_callback:
                        progress_callback("target", import_key, target_rows)

            source_summary = _store_summary(store, "source_rows")
            target_summary = _store_summary(store, "target_rows")
            missing_query = """
                SELECT COUNT(*)
                FROM source_rows AS source
                LEFT JOIN target_rows AS target
                  ON target.key_code = source.key_code
                 AND target.time_period = source.time_period
                WHERE target.key_code IS NULL
            """
            extra_query = """
                SELECT COUNT(*)
                FROM target_rows AS target
                LEFT JOIN source_rows AS source
                  ON source.key_code = target.key_code
                 AND source.time_period = target.time_period
                WHERE source.key_code IS NULL
            """
            mismatch_query = """
                SELECT COUNT(*)
                FROM source_rows AS source
                JOIN target_rows AS target
                  ON target.key_code = source.key_code
                 AND target.time_period = source.time_period
                WHERE target.row_hash <> source.row_hash
            """
            source_missing = _count(store, missing_query)
            target_extra = _count(store, extra_query)
            mismatches = _count(store, mismatch_query)
            store_bytes = _workspace_size(store)

            missing_samples = _key_samples(
                store,
                """
                SELECT source.key_code, source.time_period
                FROM source_rows AS source
                LEFT JOIN target_rows AS target
                  ON target.key_code = source.key_code
                 AND target.time_period = source.time_period
                WHERE target.key_code IS NULL
                ORDER BY source.key_code, source.time_period
                LIMIT ?
                """,
                sample_limit,
            )
            extra_samples = _key_samples(
                store,
                """
                SELECT target.key_code, target.time_period
                FROM target_rows AS target
                LEFT JOIN source_rows AS source
                  ON source.key_code = target.key_code
                 AND source.time_period = target.time_period
                WHERE source.key_code IS NULL
                ORDER BY target.key_code, target.time_period
                LIMIT ?
                """,
                sample_limit,
            )
            mismatch_samples = _key_samples(
                store,
                """
                SELECT source.key_code, source.time_period
                FROM source_rows AS source
                JOIN target_rows AS target
                  ON target.key_code = source.key_code
                 AND target.time_period = source.time_period
                WHERE target.row_hash <> source.row_hash
                ORDER BY source.key_code, source.time_period
                LIMIT ?
                """,
                sample_limit,
            )
            source_duplicate_samples = _key_samples(
                store,
                """
                SELECT key_code, time_period
                FROM source_rows
                WHERE occurrences > 1
                ORDER BY key_code, time_period
                LIMIT ?
                """,
                sample_limit,
            )
            target_duplicate_samples = _key_samples(
                store,
                """
                SELECT key_code, time_period
                FROM target_rows
                WHERE occurrences > 1
                ORDER BY key_code, time_period
                LIMIT ?
                """,
                sample_limit,
            )
        finally:
            store.close()

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
