from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

import pandas as pd
from sqlalchemy import create_engine, text

from services.euro_streaming_validation_service import (
    audit_euro_source_against_target as real_audit,
)
from services.euro_sync_service import (
    apply_euro_sync,
    build_euro_sync_plan,
    sync_confirmation,
)


class EuroSyncServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.source_path = self.root / "source.csv"
        self.engine = create_engine(f"sqlite:///{self.root / 'target.sqlite3'}")
        self.addCleanup(self.engine.dispose)
        self.contract = {
            "group": "EURO",
            "csv_path": self.source_path,
            "table_name": "euro_test",
            "mode": "multidimensional_series",
            "source_key_columns": ("key_code", "time_period"),
            "target_key_columns": ("key_code", "time_period"),
            "column_aliases": {},
            "required_columns": ("key_code", "time_period", "obs_value"),
        }

    @contextmanager
    def contract_patches(self):
        with patch(
            "services.euro_sync_service.get_macro_import",
            return_value=self.contract,
        ), patch(
            "services.euro_streaming_validation_service.get_macro_import",
            return_value=self.contract,
        ):
            yield

    def create_target(self, rows):
        with self.engine.begin() as connection:
            connection.execute(text(
                """
                CREATE TABLE euro_test (
                    key_code TEXT NOT NULL,
                    time_period TEXT NOT NULL,
                    obs_value NUMERIC NULL,
                    note TEXT NULL,
                    PRIMARY KEY (key_code, time_period)
                )
                """
            ))
            if rows:
                connection.execute(
                    text(
                        """
                        INSERT INTO euro_test
                            (key_code, time_period, obs_value, note)
                        VALUES
                            (:key_code, :time_period, :obs_value, :note)
                        """
                    ),
                    rows,
                )

    def write_source(self, rows):
        pd.DataFrame(rows).to_csv(self.source_path, index=False)

    def backup_path(self):
        path = self.root / "backup.sql"
        path.write_text(
            "CREATE TABLE `euro_test` (...);\n"
            "INSERT INTO `euro_test` VALUES ('A', '2024-01', 1, 'old');\n",
            encoding="utf-8",
        )
        return path

    def build_plan(self):
        with self.contract_patches():
            return build_euro_sync_plan(
                self.engine,
                "EURO_TEST",
                chunk_size=2,
                workspace_dir=self.root,
                minimum_free_bytes=0,
                source_path=self.source_path,
            )

    def test_plan_classifies_actions_and_never_plans_deletes(self):
        self.write_source([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 9, "note": "changed"},
            {"key_code": "B", "time_period": "2024-01", "obs_value": 2, "note": "same"},
            {"key_code": "C", "time_period": "2024-01", "obs_value": 3, "note": "new"},
        ])
        self.create_target([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "old"},
            {"key_code": "B", "time_period": "2024-01", "obs_value": 2, "note": "same"},
        ])

        plan = self.build_plan()

        self.assertTrue(plan.write_ready)
        self.assertEqual(1, plan.planned_inserts)
        self.assertEqual(1, plan.planned_updates)
        self.assertEqual(1, plan.unchanged_rows)
        self.assertEqual(0, plan.planned_deletes)
        self.assertEqual("disabled", plan.deletion_policy)
        self.assertEqual("authoritative_overwrite", plan.source_null_policy)
        self.assertFalse(plan.database_write_performed)

    def test_target_only_rows_block_sync_instead_of_being_deleted(self):
        self.write_source([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "same"},
        ])
        self.create_target([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "same"},
            {"key_code": "D", "time_period": "2024-01", "obs_value": 4, "note": "target"},
        ])

        plan = self.build_plan()

        self.assertFalse(plan.write_ready)
        self.assertEqual(1, plan.target_only_rows)
        self.assertEqual(0, plan.planned_deletes)
        self.assertIn("target_only_rows_require_review", plan.blockers)

    def test_duplicate_source_business_keys_block_sync(self):
        self.write_source([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "first"},
            {"key_code": "A", "time_period": "2024-01", "obs_value": 2, "note": "second"},
        ])
        self.create_target([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "first"},
        ])

        plan = self.build_plan()

        self.assertFalse(plan.write_ready)
        self.assertEqual(1, plan.source_duplicate_business_key_groups)
        self.assertIn("source_duplicate_business_keys", plan.blockers)

    def test_apply_writes_only_changed_keys_and_validates_before_commit(self):
        source = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": 9, "note": "changed"},
            {"key_code": "B", "time_period": "2024-01", "obs_value": 2, "note": "same"},
            {"key_code": "C", "time_period": "2024-01", "obs_value": 3, "note": "new"},
        ]
        self.write_source(source)
        self.create_target([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "old"},
            {"key_code": "B", "time_period": "2024-01", "obs_value": 2, "note": "same"},
        ])

        with self.contract_patches():
            result = apply_euro_sync(
                self.engine,
                "EURO_TEST",
                backup_file=self.backup_path(),
                confirmation=sync_confirmation("EURO_TEST"),
                chunk_size=2,
                insert_batch_size=1,
                workspace_dir=self.root,
                minimum_free_bytes=0,
                source_path=self.source_path,
            )

        actual = pd.read_sql(
            "SELECT key_code, time_period, obs_value, note "
            "FROM euro_test ORDER BY key_code",
            self.engine,
        )
        self.assertEqual(2, result["written_rows"])
        self.assertTrue(result["post_validation_valid"])
        self.assertTrue(result["database_write_performed"])
        self.assertEqual(["A", "B", "C"], actual["key_code"].tolist())
        self.assertEqual([9, 2, 3], actual["obs_value"].tolist())
        self.assertEqual(["changed", "same", "new"], actual["note"].tolist())

    def test_authoritative_source_null_overwrites_stale_target_value(self):
        self.write_source([
            {
                "key_code": "A",
                "time_period": "2024-01",
                "obs_value": 1,
                "note": "",
            },
        ])
        self.create_target([
            {
                "key_code": "A",
                "time_period": "2024-01",
                "obs_value": 1,
                "note": "stale",
            },
        ])

        with self.contract_patches():
            result = apply_euro_sync(
                self.engine,
                "EURO_TEST",
                backup_file=self.backup_path(),
                confirmation=sync_confirmation("EURO_TEST"),
                workspace_dir=self.root,
                minimum_free_bytes=0,
                source_path=self.source_path,
            )

        note = pd.read_sql("SELECT note FROM euro_test", self.engine).iloc[0]["note"]
        self.assertEqual("authoritative_overwrite", result["plan"]["source_null_policy"])
        self.assertEqual(1, result["written_rows"])
        self.assertTrue(pd.isna(note))

    def test_post_validation_failure_rolls_back_the_complete_transaction(self):
        self.write_source([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 9, "note": "changed"},
            {"key_code": "C", "time_period": "2024-01", "obs_value": 3, "note": "new"},
        ])
        self.create_target([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "old"},
        ])

        def fail_post_validation(*args, **kwargs):
            validation = real_audit(*args, **kwargs)
            if kwargs.get("sql_connection") is not None:
                return replace(validation, row_hash_mismatches=1)
            return validation

        with self.contract_patches(), patch(
            "services.euro_sync_service.audit_euro_source_against_target",
            side_effect=fail_post_validation,
        ):
            with self.assertRaisesRegex(RuntimeError, "transaction rolled back"):
                apply_euro_sync(
                    self.engine,
                    "EURO_TEST",
                    backup_file=self.backup_path(),
                    confirmation=sync_confirmation("EURO_TEST"),
                    chunk_size=2,
                    workspace_dir=self.root,
                    minimum_free_bytes=0,
                    source_path=self.source_path,
                )

        actual = pd.read_sql(
            "SELECT key_code, obs_value, note FROM euro_test ORDER BY key_code",
            self.engine,
        )
        self.assertEqual(["A"], actual["key_code"].tolist())
        self.assertEqual([1], actual["obs_value"].tolist())
        self.assertEqual(["old"], actual["note"].tolist())

    def test_exact_source_is_a_no_op_without_database_write(self):
        rows = [
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "same"},
        ]
        self.write_source(rows)
        self.create_target(rows)

        with self.contract_patches():
            result = apply_euro_sync(
                self.engine,
                "EURO_TEST",
                backup_file=self.backup_path(),
                confirmation=sync_confirmation("EURO_TEST"),
                workspace_dir=self.root,
                minimum_free_bytes=0,
                source_path=self.source_path,
            )

        self.assertTrue(result["plan"]["idempotent"])
        self.assertEqual(0, result["written_rows"])
        self.assertFalse(result["database_write_performed"])

    def test_apply_requires_exact_contract_confirmation(self):
        self.write_source([
            {"key_code": "A", "time_period": "2024-01", "obs_value": 1, "note": "same"},
        ])
        self.create_target([])

        with self.contract_patches():
            with self.assertRaisesRegex(ValueError, "must exactly match"):
                apply_euro_sync(
                    self.engine,
                    "EURO_TEST",
                    backup_file="missing.sql",
                    confirmation="WRONG",
                    workspace_dir=self.root,
                    minimum_free_bytes=0,
                    source_path=self.source_path,
                )


if __name__ == "__main__":
    unittest.main()
