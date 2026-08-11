from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

import pandas as pd
from sqlalchemy import create_engine, event

from services.euro_field_difference_service import (
    _storage_precision_equivalent,
    audit_euro_field_differences,
)


class EuroFieldDifferenceServiceTests(unittest.TestCase):
    def test_storage_precision_tolerance_uses_target_sql_type(self):
        self.assertTrue(_storage_precision_equivalent(
            "7.666935143635",
            "7.666935000000",
            "DECIMAL(20, 6)",
        ))
        self.assertFalse(_storage_precision_equivalent(
            "7.666936",
            "7.666935",
            "DECIMAL(20, 6)",
        ))
        self.assertTrue(_storage_precision_equivalent(
            "43.36919644",
            "43.369197845458984",
            "FLOAT",
        ))
        self.assertTrue(_storage_precision_equivalent(
            "9.171205",
            "9.171204566955566",
            "FLOAT",
        ))

    def test_classifies_sampled_field_changes_with_select_only_sql(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "source.csv"
            target_path = root / "target.sqlite3"
            source_rows = [
                {
                    "key_code": "A",
                    "time_period": "2024-01",
                    "obs_value": "1.000",
                    "comment_obs": " value ",
                    "title": "New title",
                },
                {
                    "key_code": "B",
                    "time_period": "2024-02",
                    "obs_value": "2",
                    "comment_obs": "same",
                    "title": "CASE",
                },
            ]
            target_rows = [
                {
                    "key_code": "A",
                    "time_period": "2024-01",
                    "obs_value": "1",
                    "comment_obs": "value",
                    "title": "Old title",
                },
                {
                    "key_code": "B",
                    "time_period": "2024-02",
                    "obs_value": "2.0",
                    "comment_obs": "same",
                    "title": "case",
                },
            ]
            pd.DataFrame(source_rows).to_csv(source_path, index=False)
            engine = create_engine(f"sqlite:///{target_path}")
            pd.DataFrame(target_rows).to_sql("euro_test", engine, index=False)
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
            contract = {
                "group": "EURO",
                "csv_path": source_path,
                "table_name": "euro_test",
                "column_aliases": {},
                "required_columns": ("key_code", "time_period", "obs_value"),
            }
            sample_keys = [
                {"key_code": "A", "time_period": "2024-01"},
                {"key_code": "B", "time_period": "2024-02"},
            ]
            with patch(
                "services.euro_field_difference_service.get_macro_import",
                return_value=contract,
            ):
                try:
                    audit = audit_euro_field_differences(
                        engine,
                        "EURO_TEST",
                        sample_keys,
                        chunk_size=1,
                    )
                finally:
                    event.remove(
                        engine,
                        "before_cursor_execute",
                        capture_statement,
                    )
                    engine.dispose()

        differences = {
            difference.column: difference
            for difference in audit.column_differences
        }
        self.assertEqual(2, audit.compared_rows)
        self.assertEqual(2, audit.differing_rows)
        self.assertNotIn("obs_value", differences)
        self.assertEqual(1, differences["comment_obs"].whitespace_only)
        self.assertEqual(1, differences["title"].case_only)
        self.assertEqual(1, differences["title"].value_changed)
        self.assertFalse(audit.database_write_performed)
        self.assertTrue(statements)
        self.assertTrue(
            all(statement.startswith(("SELECT", "PRAGMA")) for statement in statements),
            statements,
        )

    def test_rejects_empty_sample(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        with patch(
            "services.euro_field_difference_service.get_macro_import",
            return_value={"group": "EURO", "csv_path": "missing.csv"},
        ):
            with self.assertRaises(FileNotFoundError):
                audit_euro_field_differences(engine, "EURO_TEST", [])


if __name__ == "__main__":
    unittest.main()
