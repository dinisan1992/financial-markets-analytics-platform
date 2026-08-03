from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from project_scripts.diagnostics.migrate_treasury_source_identity import (
    validate_sql_backup,
    versioned_name,
)


class TreasurySourceMigrationTests(unittest.TestCase):
    def test_versioned_table_name_stays_identifier_safe(self):
        name = versioned_name("us2y_analysis", "shadow_v051", "20260803_170000")
        self.assertEqual(
            "us2y_analysis__shadow_v051_20260803_170000",
            name,
        )

    def test_sql_backup_requires_structure_and_data_markers(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.sql"
            path.write_text(
                "CREATE TABLE `us2y_analysis` (...);\n"
                "INSERT INTO `us2y_analysis` VALUES ('1960-01-05');\n",
                encoding="utf-8",
            )
            result = validate_sql_backup(path)

        self.assertGreater(result["bytes"], 0)
        self.assertEqual(64, len(result["sha256"]))

    def test_sql_backup_without_insert_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.sql"
            path.write_text(
                "CREATE TABLE `us2y_analysis` (...);\n1960-01-05\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "missing data markers"):
                validate_sql_backup(path)


if __name__ == "__main__":
    unittest.main()
