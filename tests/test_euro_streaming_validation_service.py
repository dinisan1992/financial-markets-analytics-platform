from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

import pandas as pd
from sqlalchemy import create_engine, event

from services.euro_streaming_validation_service import (
    audit_euro_source_against_target,
)


class EuroStreamingValidationTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
