from datetime import datetime, timezone
from pathlib import Path
import unittest

import pandas as pd

from project_scripts.diagnostics.acceptance_test_euro_sync_mysql import (
    EXECUTION_CONFIRMATION,
    TEST_SCHEMA_PREFIX,
    build_mysql_restore_command,
    build_rollback_fixture_frame,
    build_success_fixture_frame,
    main,
    new_test_schema_name,
    validate_backup_dir,
    validate_test_schema_name,
)


class EuroSyncMysqlAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            {
                "KEY": "A",
                "TIME_PERIOD": "2024-S1",
                "OBS_VALUE": "1.0",
                "TITLE": "First",
            },
            {
                "KEY": "B",
                "TIME_PERIOD": "2024-S1",
                "OBS_VALUE": "2.0",
                "TITLE": "Second",
            },
            {
                "KEY": "C",
                "TIME_PERIOD": "2024-S1",
                "OBS_VALUE": "3.0",
                "TITLE": "Third",
            },
        ])
        self.mapped = ("key_code", "time_period", "obs_value", "title")

    def test_schema_name_is_generated_inside_strict_prefix(self):
        name = new_test_schema_name(
            now=datetime(2026, 8, 11, 12, 30, tzinfo=timezone.utc),
            token="abc123",
        )

        self.assertEqual(
            f"{TEST_SCHEMA_PREFIX}20260811_123000_abc123",
            name,
        )
        self.assertEqual(name, validate_test_schema_name(name))

    def test_schema_validation_rejects_existing_or_unsafe_names(self):
        with self.assertRaises(ValueError):
            validate_test_schema_name("btc_data", production_schema="btc_data")
        with self.assertRaises(ValueError):
            validate_test_schema_name("unscoped_test")
        with self.assertRaises(ValueError):
            validate_test_schema_name(f"{TEST_SCHEMA_PREFIX}bad-name")

    def test_restore_command_contains_no_password(self):
        schema = f"{TEST_SCHEMA_PREFIX}20260811_123000_abc123"
        command = build_mysql_restore_command(Path("mysql.exe"), schema)

        self.assertEqual(schema, command[-1])
        self.assertFalse(any("password" in part.lower() for part in command))

    def test_backup_directory_must_be_outside_repository(self):
        with self.assertRaisesRegex(ValueError, "outside the repository"):
            validate_backup_dir(Path(__file__).resolve().parents[1] / "backups")

        outside = Path(__file__).resolve().parents[2] / "external_backups"
        self.assertEqual(outside.resolve(), validate_backup_dir(outside))

    def test_success_fixture_has_update_null_and_unique_insert(self):
        fixture, metadata = build_success_fixture_frame(
            self.frame,
            self.mapped,
            {"title"},
        )

        self.assertEqual(4, len(fixture))
        self.assertEqual("2.25", fixture.iloc[0]["OBS_VALUE"])
        self.assertEqual("", fixture.iloc[1]["TITLE"])
        self.assertEqual("2099-S1", fixture.iloc[-1]["TIME_PERIOD"])
        self.assertEqual(1, metadata["planned_inserts"])
        self.assertEqual(2, metadata["planned_updates"])
        self.assertEqual("title", metadata["null_overwrite_column"])

    def test_rollback_fixture_changes_one_existing_observation(self):
        fixture = build_rollback_fixture_frame(self.frame, self.mapped)

        self.assertEqual(3, len(fixture))
        self.assertEqual("3.5", fixture.iloc[0]["OBS_VALUE"])
        self.assertEqual("2.0", fixture.iloc[1]["OBS_VALUE"])

    def test_default_cli_is_read_only(self):
        self.assertEqual(0, main([]))
        with self.assertRaisesRegex(ValueError, EXECUTION_CONFIRMATION):
            main(["--execute", "--confirm", "WRONG"])
        with self.assertRaisesRegex(ValueError, "--backup-dir"):
            main(["--execute", "--confirm", EXECUTION_CONFIRMATION])


if __name__ == "__main__":
    unittest.main()
