from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch
import unittest

import pandas as pd

from services.euro_fingerprint_store import (
    EuroFingerprintStore,
    SOURCE_DATASET,
    TARGET_DATASET,
    temporary_fingerprint_store,
)
from services.euro_rebuild_service import (
    HASH_COLUMN,
    MAX_SHADOW_FETCH_ROWS,
    _shadow_value_batches,
    canonical_row_hash,
    normalize_row,
    source_fingerprints_to_store,
    validate_shadow_disk_backed,
)


class EuroFingerprintStoreTests(unittest.TestCase):
    def test_shadow_batches_use_unbuffered_bounded_mysql_cursor(self):
        class Cursor:
            def __init__(self):
                self.fetch_sizes = []
                self.executed = []
                self.closed = False
                self.batches = [[("A", "2024-01", "hash")], []]

            def execute(self, statement):
                self.executed.append(statement)

            def fetchmany(self, size):
                self.fetch_sizes.append(size)
                return self.batches.pop(0)

            def close(self):
                self.closed = True

        cursor = Cursor()
        driver_connection = Mock()
        driver_connection.cursor.return_value = cursor
        dialect = type(
            "Dialect",
            (),
            {"name": "mysql", "driver": "mysqlconnector"},
        )()
        engine = type("Engine", (), {"dialect": dialect})()
        fairy = type(
            "ConnectionFairy",
            (),
            {"driver_connection": driver_connection},
        )()
        connection = type(
            "Connection",
            (),
            {"engine": engine, "connection": fairy},
        )()

        batches = list(
            _shadow_value_batches(
                connection,
                Mock(text="SELECT key_code, time_period, row_hash FROM euro_shadow"),
                ("key_code", "time_period", "row_hash"),
                MAX_SHADOW_FETCH_ROWS * 10,
            )
        )

        driver_connection.cursor.assert_called_once_with(buffered=False)
        self.assertEqual(1, len(batches))
        self.assertEqual(MAX_SHADOW_FETCH_ROWS, cursor.fetch_sizes[0])
        self.assertTrue(cursor.closed)

    def test_actions_for_keys_separates_insert_update_and_unchanged(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = EuroFingerprintStore(
                root / "fingerprints.sqlite3",
                workspace_root=root,
                free_disk_bytes_before=1,
            )
            try:
                store.insert_records(
                    SOURCE_DATASET,
                    [
                        ("A", "2024-01", b"same"),
                        ("B", "2024-01", b"new"),
                        ("C", "2024-01", b"missing"),
                    ],
                )
                store.insert_records(
                    TARGET_DATASET,
                    [
                        ("A", "2024-01", b"same"),
                        ("B", "2024-01", b"old"),
                    ],
                )

                actions = store.actions_for_keys(
                    [
                        ("A", "2024-01"),
                        ("B", "2024-01"),
                        ("C", "2024-01"),
                    ],
                    batch_size=2,
                )
            finally:
                store.close()

        self.assertEqual("unchanged", actions[("A", "2024-01")])
        self.assertEqual("update", actions[("B", "2024-01")])
        self.assertEqual("insert", actions[("C", "2024-01")])

    def test_store_classifies_missing_extra_mismatch_and_duplicates(self):
        with TemporaryDirectory() as temp_dir:
            with temporary_fingerprint_store(
                "EURO_TEST",
                workspace_dir=temp_dir,
                minimum_free_bytes=0,
            ) as store:
                store.insert_records(
                    SOURCE_DATASET,
                    [
                        ("A", "2024-01", b"a" * 32),
                        ("B", "2024-01", b"b" * 32),
                        ("C", "2024-01", b"c" * 32),
                        ("C", "2024-01", b"x" * 32),
                    ],
                )
                store.insert_records(
                    TARGET_DATASET,
                    [
                        ("A", "2024-01", b"z" * 32),
                        ("B", "2024-01", b"b" * 32),
                        ("D", "2024-01", b"d" * 32),
                    ],
                )

                self.assertEqual(1, store.summary(SOURCE_DATASET)["duplicate_groups"])
                self.assertEqual(
                    {
                        "source_rows_missing_from_target": 1,
                        "target_rows_missing_from_source": 1,
                        "row_hash_mismatches": 1,
                    },
                    store.comparison(),
                )
                self.assertEqual("C", store.key_samples("missing", 1)[0]["key_code"])
                self.assertGreater(store.size_bytes, 0)

    def test_hash_sample_is_deterministic_and_not_key_ordered(self):
        with TemporaryDirectory() as temp_dir:
            with temporary_fingerprint_store(
                "EURO_TEST",
                workspace_dir=temp_dir,
                minimum_free_bytes=0,
            ) as store:
                store.insert_records(
                    SOURCE_DATASET,
                    [
                        ("A", "2024-01", b"z" * 32),
                        ("B", "2024-01", b"a" * 32),
                    ],
                )
                store.insert_records(
                    TARGET_DATASET,
                    [
                        ("A", "2024-01", b"x" * 32),
                        ("B", "2024-01", b"y" * 32),
                    ],
                )

                ordered = store.key_samples("mismatch", 1)
                hashed = store.key_samples("mismatch", 1, strategy="hash")

        self.assertEqual("A", ordered[0]["key_code"])
        self.assertEqual("B", hashed[0]["key_code"])

    def test_temporary_store_is_removed_after_context_exit(self):
        with TemporaryDirectory() as temp_dir:
            with temporary_fingerprint_store(
                "EURO_TEST",
                workspace_dir=temp_dir,
                minimum_free_bytes=0,
            ) as store:
                path = store.path
                self.assertTrue(path.exists())
            self.assertFalse(path.exists())

    def test_source_duplicate_across_chunks_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.csv"
            pd.DataFrame([
                {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
                {"key_code": "B", "time_period": "2024-01", "obs_value": "2"},
                {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
            ]).to_csv(source, index=False)
            contract = {
                "group": "EURO",
                "csv_path": source,
                "table_name": "euro_test",
                "column_aliases": {},
                "required_columns": ("key_code", "time_period", "obs_value"),
            }
            with temporary_fingerprint_store(
                "EURO_TEST",
                workspace_dir=root,
                minimum_free_bytes=0,
            ) as store:
                with patch(
                    "services.euro_rebuild_service.get_macro_import",
                    return_value=contract,
                ):
                    with self.assertRaisesRegex(ValueError, "Duplicate source"):
                        source_fingerprints_to_store(
                            "EURO_TEST",
                            store,
                            chunk_size=2,
                        )

    def test_shadow_validation_uses_disk_backed_fingerprints(self):
        columns = ("key_code", "time_period", "obs_value")
        record, invalid = normalize_row(
            columns,
            ("A", "2024-01", "1.25"),
        )
        self.assertEqual((), invalid)
        row_hash = canonical_row_hash(columns, record)

        with TemporaryDirectory() as temp_dir:
            with temporary_fingerprint_store(
                "EURO_TEST",
                workspace_dir=temp_dir,
                minimum_free_bytes=0,
            ) as store:
                store.insert_records(
                    SOURCE_DATASET,
                    [("A", "2024-01", bytes.fromhex(row_hash))],
                )
                engine = MagicMock()
                connection = Mock()
                engine.connect.return_value.__enter__.return_value = connection

                summary_result = Mock()
                summary_result.mappings.return_value.one.return_value = {
                    "rows_count": 1,
                    "unique_business_keys": 1,
                    "non_null_values": 1,
                    "null_business_keys": 0,
                    "first_period": "2024-01",
                    "last_period": "2024-01",
                }
                duplicate_result = Mock()
                duplicate_result.scalar_one.return_value = 0
                connection.execute.side_effect = [
                    summary_result,
                    duplicate_result,
                ]
                result = connection.execution_options.return_value.execute.return_value
                rows = result.mappings.return_value
                rows.fetchmany.side_effect = [
                    [{**record, HASH_COLUMN: row_hash}],
                    [],
                ]

                with patch(
                    "services.euro_rebuild_service.get_macro_import",
                    return_value={"table_name": "euro_active"},
                ), patch(
                    "services.euro_rebuild_service._business_key_is_unique",
                    return_value=True,
                ):
                    validation = validate_shadow_disk_backed(
                        engine,
                        "EURO_TEST",
                        "euro_shadow",
                        columns,
                        store,
                        source_rows=1,
                        source_non_null_values=1,
                        chunk_size=1,
                        database_write_performed=False,
                    )

                self.assertTrue(validation.valid)
                self.assertTrue(validation.memory_bounded_validation)
                self.assertFalse(validation.database_write_performed)
                self.assertGreater(validation.comparison_store_bytes, 0)
                connection.execution_options.assert_called_once_with(
                    stream_results=True,
                    max_row_buffer=1,
                )
                rows.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
