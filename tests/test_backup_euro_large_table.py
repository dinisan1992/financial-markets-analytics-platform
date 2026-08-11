from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from project_scripts.diagnostics.backup_euro_large_table import main
from project_scripts.diagnostics.backup_market_tables import (
    validate_filename_prefix,
)


class EuroLargeBackupTests(unittest.TestCase):
    def test_filename_prefix_rejects_path_characters(self):
        self.assertEqual("euro_before_v062", validate_filename_prefix(
            "euro_before_v062"
        ))
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            validate_filename_prefix("../backup")

    def test_backup_command_scopes_and_verifies_one_table(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.sql"
            path.write_text(
                "CREATE TABLE `euro_mfi_interest_rate_statistics` (...);\n"
                "INSERT INTO `euro_mfi_interest_rate_statistics` VALUES (1);\n",
                encoding="utf-8",
            )
            verification = {
                "sha256": "A" * 64,
            }
            output = StringIO()
            with patch(
                "project_scripts.diagnostics.backup_euro_large_table."
                "create_backup",
                return_value=(path, "A" * 64),
            ) as create, patch(
                "project_scripts.diagnostics.backup_euro_large_table."
                "validate_scoped_backup",
                return_value=verification,
            ) as validate, redirect_stdout(output):
                result = main([
                    "EURO_MFI_INTEREST_RATES",
                    "--output-dir",
                    temp_dir,
                ])

        self.assertEqual(0, result)
        self.assertEqual(
            ("euro_mfi_interest_rate_statistics",),
            create.call_args.kwargs["tables"],
        )
        self.assertIn("before_v062", create.call_args.kwargs["filename_prefix"])
        validate.assert_called_once()
        self.assertIn("Database writes: disabled", output.getvalue())


if __name__ == "__main__":
    unittest.main()
