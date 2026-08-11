from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import unittest

import pandas as pd
from sqlalchemy import create_engine, event, text

from services.euro_streaming_validation_service import (
    MAX_TARGET_FETCH_ROWS,
    _target_query,
    _target_value_batches,
    audit_euro_source_against_target,
)


class EuroStreamingValidationTests(unittest.TestCase):
    @patch("services.euro_streaming_validation_service.inspect")
    def test_mysql_float_target_is_selected_through_double_cast(self, inspect_mock):
        inspector = inspect_mock.return_value
        inspector.has_table.return_value = True
        inspector.get_columns.return_value = [
            {"name": "key_code", "type": "VARCHAR(100)"},
            {"name": "time_period", "type": "VARCHAR(20)"},
            {"name": "obs_value", "type": "FLOAT"},
        ]
        engine = Mock()
        engine.dialect.name = "mysql"

        query = _target_query(
            engine,
            "euro_test",
            ("key_code", "time_period", "obs_value"),
        )

        self.assertIn("CAST(`obs_value` AS DOUBLE)", query.text)

    def _audit(self, source_rows, target_rows, chunk_size=2):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        source_path = root / "source.csv"
        target_path = root / "target.sqlite3"
        pd.DataFrame(source_rows).to_csv(source_path, index=False)
        engine = create_engine(f"sqlite:///{target_path}")
        self.addCleanup(engine.dispose)
        pd.DataFrame(target_rows).to_sql("euro_test", engine, index=False)
        contract = {
            "group": "EURO",
            "csv_path": source_path,
            "table_name": "euro_test",
            "column_aliases": {},
            "required_columns": ("key_code", "time_period", "obs_value"),
        }
        with patch(
            "services.euro_streaming_validation_service.get_macro_import",
            return_value=contract,
        ):
            return audit_euro_source_against_target(
                engine,
                "EURO_TEST",
                chunk_size=chunk_size,
                workspace_dir=root,
                minimum_free_bytes=0,
            )

    def test_exact_source_and_target_are_valid(self):
        rows = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": "1.25"},
            {"key_code": "A", "time_period": "2024-02", "obs_value": "2.50"},
            {"key_code": "B", "time_period": "2024-Q1", "obs_value": "3"},
        ]
        validation = self._audit(rows, rows)

        self.assertTrue(validation.valid)
        self.assertEqual(3, validation.source_rows)
        self.assertEqual(3, validation.target_rows)
        self.assertLessEqual(validation.max_source_chunk_rows, 2)
        self.assertLessEqual(validation.max_target_chunk_rows, 2)
        self.assertGreater(validation.comparison_store_bytes, 0)
        self.assertFalse(validation.database_write_performed)

    def test_missing_extra_and_mismatched_rows_are_separated(self):
        source = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
            {"key_code": "B", "time_period": "2024-01", "obs_value": "2"},
            {"key_code": "C", "time_period": "2024-01", "obs_value": "3"},
        ]
        target = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": "9"},
            {"key_code": "B", "time_period": "2024-01", "obs_value": "2"},
            {"key_code": "D", "time_period": "2024-01", "obs_value": "4"},
        ]
        validation = self._audit(source, target)

        self.assertFalse(validation.valid)
        self.assertEqual(1, validation.source_rows_missing_from_target)
        self.assertEqual(1, validation.target_rows_missing_from_source)
        self.assertEqual(1, validation.row_hash_mismatches)
        self.assertEqual("C", validation.missing_source_key_samples[0]["key_code"])
        self.assertEqual("D", validation.extra_target_key_samples[0]["key_code"])
        self.assertEqual("A", validation.mismatch_key_samples[0]["key_code"])

    def test_source_quality_failures_are_explicit(self):
        source = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
            {"key_code": "A", "time_period": "2024-01", "obs_value": "2"},
            {"key_code": "", "time_period": "2024-02", "obs_value": "3"},
            {"key_code": "B", "time_period": "2024-03", "obs_value": "invalid"},
        ]
        target = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
        ]
        validation = self._audit(source, target)

        self.assertFalse(validation.valid)
        self.assertEqual(1, validation.source_duplicate_business_key_groups)
        self.assertEqual(1, validation.source_duplicate_rows)
        self.assertEqual(1, validation.source_duplicate_hash_conflicts)
        self.assertEqual(1, validation.source_null_business_keys)
        self.assertEqual(1, validation.source_invalid_numeric_rows)

    def test_target_duplicate_rows_are_counted_without_loading_all_keys(self):
        source = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
        ]
        target = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
            {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
        ]
        validation = self._audit(source, target, chunk_size=1)

        self.assertFalse(validation.valid)
        self.assertEqual(1, validation.target_duplicate_business_key_groups)
        self.assertEqual(1, validation.target_duplicate_rows)
        self.assertEqual(0, validation.target_duplicate_hash_conflicts)

    def test_target_database_receives_read_statements_only(self):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        source_path = root / "source.csv"
        target_path = root / "target.sqlite3"
        rows = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": "1"},
        ]
        pd.DataFrame(rows).to_csv(source_path, index=False)
        engine = create_engine(f"sqlite:///{target_path}")
        self.addCleanup(engine.dispose)
        pd.DataFrame(rows).to_sql("euro_test", engine, index=False)
        statements = []

        def capture_statement(
            connection,
            cursor,
            statement,
            parameters,
            context,
            executemany,
        ):
            statements.append(statement.strip().upper())

        event.listen(engine, "before_cursor_execute", capture_statement)
        self.addCleanup(
            event.remove,
            engine,
            "before_cursor_execute",
            capture_statement,
        )
        contract = {
            "group": "EURO",
            "csv_path": source_path,
            "table_name": "euro_test",
            "column_aliases": {},
            "required_columns": ("key_code", "time_period", "obs_value"),
        }
        with patch(
            "services.euro_streaming_validation_service.get_macro_import",
            return_value=contract,
        ):
            validation = audit_euro_source_against_target(
                engine,
                "EURO_TEST",
                workspace_dir=root,
                minimum_free_bytes=0,
            )

        self.assertTrue(validation.valid)
        self.assertTrue(statements)
        self.assertTrue(
            all(statement.startswith(("SELECT", "PRAGMA")) for statement in statements),
            statements,
        )

    def test_hash_comparison_respects_target_float_precision(self):
        temp_dir = TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        root = Path(temp_dir.name)
        source_path = root / "source.csv"
        target_path = root / "target.sqlite3"
        pd.DataFrame([{
            "key_code": "A",
            "time_period": "2024-01",
            "obs_value": "122.79865325",
        }]).to_csv(source_path, index=False)
        engine = create_engine(f"sqlite:///{target_path}")
        with engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE euro_test ("
                "key_code TEXT, time_period TEXT, obs_value FLOAT)"
            ))
            connection.execute(text(
                "INSERT INTO euro_test VALUES "
                "('A', '2024-01', 122.79865264892578)"
            ))
        contract = {
            "group": "EURO",
            "csv_path": source_path,
            "table_name": "euro_test",
            "column_aliases": {},
            "required_columns": ("key_code", "time_period", "obs_value"),
        }
        with patch(
            "services.euro_streaming_validation_service.get_macro_import",
            return_value=contract,
        ):
            validation = audit_euro_source_against_target(
                engine,
                "EURO_TEST",
                workspace_dir=root,
                minimum_free_bytes=0,
            )
        engine.dispose()

        self.assertTrue(validation.valid)
        self.assertEqual(0, validation.row_hash_mismatches)
        self.assertEqual("FLOAT", validation.target_column_types["obs_value"])

    def test_mysqlconnector_uses_unbuffered_bounded_cursor(self):
        class Cursor:
            def __init__(self):
                self.execute_calls = []
                self.fetch_sizes = []
                self.closed = False
                self.batches = [
                    [("A", "2024-01", "1")],
                    [("B", "2024-01", "2")],
                    [],
                ]

            def execute(self, statement):
                self.execute_calls.append(statement)

            def fetchmany(self, size):
                self.fetch_sizes.append(size)
                return self.batches.pop(0)

            def close(self):
                self.closed = True

        class DriverConnection:
            def __init__(self, cursor):
                self.test_cursor = cursor
                self.buffered_arguments = []

            def cursor(self, buffered):
                self.buffered_arguments.append(buffered)
                return self.test_cursor

        cursor = Cursor()
        driver_connection = DriverConnection(cursor)
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

        batches = list(_target_value_batches(
            connection,
            text("SELECT key_code, time_period, obs_value FROM euro_test"),
            ("key_code", "time_period", "obs_value"),
            MAX_TARGET_FETCH_ROWS * 10,
        ))

        self.assertEqual(False, driver_connection.buffered_arguments[0])
        self.assertEqual(2, len(batches))
        self.assertEqual(MAX_TARGET_FETCH_ROWS, cursor.fetch_sizes[0])
        self.assertTrue(cursor.closed)


if __name__ == "__main__":
    unittest.main()
