from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from project_scripts.diagnostics.backup_euro_table import main


class BackupEuroTableTests(unittest.TestCase):
    def test_backup_scopes_direct_debits_and_verifies_digest(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.sql"
            verification = {
                "path": path,
                "bytes": 100,
                "sha256": "A" * 64,
            }
            output = StringIO()
            with patch(
                "project_scripts.diagnostics.backup_euro_table."
                "validate_external_backup_dir",
                return_value=Path(temp_dir),
            ), patch(
                "project_scripts.diagnostics.backup_euro_table.create_backup",
                return_value=(path, "A" * 64),
            ) as create, patch(
                "project_scripts.diagnostics.backup_euro_table."
                "validate_scoped_backup",
                return_value=verification,
            ) as validate, redirect_stdout(output):
                result = main(
                    [
                        "EURO_DIRECT_DEBITS",
                        "--output-dir",
                        temp_dir,
                    ]
                )

        self.assertEqual(0, result)
        self.assertEqual(
            ("euro_direct_debits",),
            create.call_args.kwargs["tables"],
        )
        validate.assert_called_once_with(path, ("euro_direct_debits",))
        self.assertIn('"database_write_performed": false', output.getvalue())


if __name__ == "__main__":
    unittest.main()
