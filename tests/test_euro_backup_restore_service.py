from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from services.euro_backup_restore_service import (
    TEST_SCHEMA_PREFIX,
    build_mysql_restore_command,
    new_test_schema_name,
    validate_external_backup_dir,
    validate_test_schema_name,
    verification_confirmation,
    verify_euro_backup_restore,
)


class EuroBackupRestoreServiceTests(unittest.TestCase):
    def test_confirmation_is_import_specific(self):
        self.assertEqual(
            "VERIFY_EURO_DIRECT_DEBITS_BACKUP_RESTORE_V068",
            verification_confirmation("EURO_DIRECT_DEBITS"),
        )

    def test_test_schema_name_is_generated_and_restricted(self):
        schema = new_test_schema_name(
            now=datetime(2026, 8, 11, 17, 0, tzinfo=timezone.utc),
            token="abc123",
        )
        self.assertEqual(
            f"{TEST_SCHEMA_PREFIX}20260811_170000_abc123",
            schema,
        )
        with self.assertRaisesRegex(ValueError, "must start"):
            validate_test_schema_name("btc_data_copy")

    def test_restore_command_does_not_expose_password(self):
        schema = f"{TEST_SCHEMA_PREFIX}20260811_170000_abc123"
        command = build_mysql_restore_command(Path("mysql.exe"), schema)
        self.assertFalse(any("password" in argument.lower() for argument in command))
        self.assertEqual(schema, command[-1])

    @patch("services.euro_backup_restore_service._physical_volume_id")
    def test_external_backup_dir_rejects_repository_and_same_volume(
        self,
        volume_id,
    ):
        root = Path("C:/project").resolve()
        with self.assertRaisesRegex(ValueError, "outside"):
            validate_external_backup_dir(root / "backups", root)
        volume_id.side_effect = [("drive", "c:"), ("drive", "c:")]
        with self.assertRaisesRegex(ValueError, "separate physical volume"):
            validate_external_backup_dir(Path("C:/backups"), root)
        volume_id.side_effect = [("drive", "d:"), ("drive", "c:")]
        self.assertEqual(
            Path("D:/backups").resolve(),
            validate_external_backup_dir(Path("D:/backups"), root),
        )

    @patch(
        "services.euro_backup_restore_service.validate_scoped_backup"
    )
    def test_wrong_confirmation_fails_before_backup_or_database_access(
        self,
        backup_mock,
    ):
        with self.assertRaisesRegex(ValueError, "must exactly match"):
            verify_euro_backup_restore(
                Mock(),
                "EURO_DIRECT_DEBITS",
                "backup.sql",
                "WRONG",
            )
        backup_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
