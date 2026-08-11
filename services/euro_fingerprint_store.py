from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import shutil
import sqlite3
from tempfile import TemporaryDirectory, gettempdir


SOURCE_DATASET = "source_rows"
TARGET_DATASET = "target_rows"
DATASETS = frozenset({SOURCE_DATASET, TARGET_DATASET})
DEFAULT_MINIMUM_FREE_BYTES = 2 * 1024**3


class EuroFingerprintStore:
    """Disk-backed business-key and row-hash store for exact EURO checks."""

    def __init__(self, path, *, workspace_root, free_disk_bytes_before):
        self.path = Path(path)
        self.workspace_root = Path(workspace_root)
        self.free_disk_bytes_before = int(free_disk_bytes_before)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA journal_mode=OFF")
        self.connection.execute("PRAGMA synchronous=OFF")
        self.connection.execute("PRAGMA temp_store=FILE")
        self.connection.execute("PRAGMA cache_size=-65536")
        for dataset in DATASETS:
            self.connection.execute(
                f"""
                CREATE TABLE {dataset} (
                    key_code TEXT NOT NULL,
                    time_period TEXT NOT NULL,
                    row_hash BLOB NOT NULL,
                    occurrences INTEGER NOT NULL DEFAULT 1,
                    hash_conflicts INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (key_code, time_period)
                ) WITHOUT ROWID
                """
            )
        self.connection.commit()

    @staticmethod
    def _dataset(dataset):
        if dataset not in DATASETS:
            raise ValueError(f"Unsupported fingerprint dataset: {dataset}")
        return dataset

    def insert_records(self, dataset, records):
        dataset = self._dataset(dataset)
        if not records:
            return
        self.connection.executemany(
            f"""
            INSERT INTO {dataset} (key_code, time_period, row_hash)
            VALUES (?, ?, ?)
            ON CONFLICT(key_code, time_period) DO UPDATE SET
                occurrences = occurrences + 1,
                hash_conflicts = hash_conflicts +
                    CASE WHEN row_hash <> excluded.row_hash THEN 1 ELSE 0 END
            """,
            records,
        )
        self.connection.commit()

    def clear(self, dataset):
        dataset = self._dataset(dataset)
        self.connection.execute(f"DELETE FROM {dataset}")
        self.connection.commit()

    def summary(self, dataset):
        dataset = self._dataset(dataset)
        row = self.connection.execute(
            f"""
            SELECT
                COUNT(*) AS unique_keys,
                COALESCE(SUM(occurrences - 1), 0) AS duplicate_rows,
                COALESCE(SUM(occurrences > 1), 0) AS duplicate_groups,
                COALESCE(SUM(hash_conflicts), 0) AS hash_conflicts,
                MIN(time_period) AS first_period,
                MAX(time_period) AS last_period
            FROM {dataset}
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

    def comparison(self):
        missing = self._count(
            """
            SELECT COUNT(*)
            FROM source_rows AS source
            LEFT JOIN target_rows AS target
              ON target.key_code = source.key_code
             AND target.time_period = source.time_period
            WHERE target.key_code IS NULL
            """
        )
        extra = self._count(
            """
            SELECT COUNT(*)
            FROM target_rows AS target
            LEFT JOIN source_rows AS source
              ON source.key_code = target.key_code
             AND source.time_period = target.time_period
            WHERE source.key_code IS NULL
            """
        )
        mismatches = self._count(
            """
            SELECT COUNT(*)
            FROM source_rows AS source
            JOIN target_rows AS target
              ON target.key_code = source.key_code
             AND target.time_period = source.time_period
            WHERE target.row_hash <> source.row_hash
            """
        )
        return {
            "source_rows_missing_from_target": missing,
            "target_rows_missing_from_source": extra,
            "row_hash_mismatches": mismatches,
        }

    def key_samples(self, difference, limit, strategy="ordered"):
        if strategy not in {"ordered", "hash"}:
            raise ValueError(f"Unsupported sample strategy: {strategy}")
        order_by = {
            "missing": {
                "ordered": "source.key_code, source.time_period",
                "hash": "source.row_hash, source.key_code, source.time_period",
            },
            "extra": {
                "ordered": "target.key_code, target.time_period",
                "hash": "target.row_hash, target.key_code, target.time_period",
            },
            "mismatch": {
                "ordered": "source.key_code, source.time_period",
                "hash": "source.row_hash, source.key_code, source.time_period",
            },
            "source_duplicate": {
                "ordered": "key_code, time_period",
                "hash": "row_hash, key_code, time_period",
            },
            "target_duplicate": {
                "ordered": "key_code, time_period",
                "hash": "row_hash, key_code, time_period",
            },
        }
        queries = {
            "missing": f"""
                SELECT source.key_code, source.time_period
                FROM source_rows AS source
                LEFT JOIN target_rows AS target
                  ON target.key_code = source.key_code
                 AND target.time_period = source.time_period
                WHERE target.key_code IS NULL
                ORDER BY {order_by["missing"][strategy]}
                LIMIT ?
            """,
            "extra": f"""
                SELECT target.key_code, target.time_period
                FROM target_rows AS target
                LEFT JOIN source_rows AS source
                  ON source.key_code = target.key_code
                 AND source.time_period = target.time_period
                WHERE source.key_code IS NULL
                ORDER BY {order_by["extra"][strategy]}
                LIMIT ?
            """,
            "mismatch": f"""
                SELECT source.key_code, source.time_period
                FROM source_rows AS source
                JOIN target_rows AS target
                  ON target.key_code = source.key_code
                 AND target.time_period = source.time_period
                WHERE target.row_hash <> source.row_hash
                ORDER BY {order_by["mismatch"][strategy]}
                LIMIT ?
            """,
            "source_duplicate": f"""
                SELECT key_code, time_period
                FROM source_rows
                WHERE occurrences > 1
                ORDER BY {order_by["source_duplicate"][strategy]}
                LIMIT ?
            """,
            "target_duplicate": f"""
                SELECT key_code, time_period
                FROM target_rows
                WHERE occurrences > 1
                ORDER BY {order_by["target_duplicate"][strategy]}
                LIMIT ?
            """,
        }
        if difference not in queries:
            raise ValueError(f"Unsupported fingerprint difference: {difference}")
        rows = self.connection.execute(
            queries[difference],
            (max(0, int(limit)),),
        ).fetchall()
        return tuple(
            {"key_code": row[0], "time_period": row[1]}
            for row in rows
        )

    def actions_for_keys(self, keys, batch_size=400):
        """Classify source keys without loading the complete index into memory."""
        normalized = tuple(dict.fromkeys(
            (str(key_code), str(time_period))
            for key_code, time_period in keys
        ))
        actions = {}
        batch_size = max(1, min(int(batch_size), 400))
        for start in range(0, len(normalized), batch_size):
            batch = normalized[start:start + batch_size]
            placeholders = ", ".join("(?, ?)" for _ in batch)
            parameters = tuple(value for key in batch for value in key)
            rows = self.connection.execute(
                f"""
                SELECT
                    source.key_code,
                    source.time_period,
                    CASE
                        WHEN target.key_code IS NULL THEN 'insert'
                        WHEN target.row_hash <> source.row_hash THEN 'update'
                        ELSE 'unchanged'
                    END AS action
                FROM source_rows AS source
                LEFT JOIN target_rows AS target
                  ON target.key_code = source.key_code
                 AND target.time_period = source.time_period
                WHERE (source.key_code, source.time_period)
                      IN ({placeholders})
                """,
                parameters,
            ).fetchall()
            actions.update({(row[0], row[1]): row[2] for row in rows})
        return actions

    def _count(self, query):
        return int(self.connection.execute(query).fetchone()[0] or 0)

    @property
    def size_bytes(self):
        page_count = int(
            self.connection.execute("PRAGMA page_count").fetchone()[0]
        )
        page_size = int(
            self.connection.execute("PRAGMA page_size").fetchone()[0]
        )
        return page_count * page_size

    def close(self):
        self.connection.close()


@contextmanager
def temporary_fingerprint_store(
    import_key,
    *,
    workspace_dir=None,
    minimum_free_bytes=DEFAULT_MINIMUM_FREE_BYTES,
):
    workspace_root = (
        Path(workspace_dir).expanduser().resolve()
        if workspace_dir is not None
        else Path(gettempdir()).resolve()
    )
    if not workspace_root.is_dir():
        raise FileNotFoundError(
            f"Fingerprint workspace does not exist: {workspace_root}"
        )
    free_before = shutil.disk_usage(workspace_root).free
    if free_before < max(0, int(minimum_free_bytes)):
        raise OSError(
            f"Insufficient free space for fingerprint store: {free_before} bytes"
        )

    with TemporaryDirectory(
        prefix=f"euro_fingerprints_{str(import_key).lower()}_",
        dir=workspace_root,
    ) as temp_dir:
        store = EuroFingerprintStore(
            Path(temp_dir) / "fingerprints.sqlite3",
            workspace_root=workspace_root,
            free_disk_bytes_before=free_before,
        )
        try:
            yield store
        finally:
            store.close()
