from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
import unittest

from project_scripts.diagnostics.remediate_euro_large_table import (
    main,
    write_report,
)


class EuroLargeRemediationCliTests(unittest.TestCase):
    def test_plan_is_read_only_and_does_not_create_engine(self):
        output = StringIO()
        with patch(
            "project_scripts.diagnostics.remediate_euro_large_table.create_engine"
        ) as create_engine, redirect_stdout(output):
            result = main([
                "EURO_CONSUMER_PRICES",
                "--suffix",
                "20260811_120000",
            ])

        self.assertEqual(0, result)
        create_engine.assert_not_called()
        text = output.getvalue()
        self.assertIn("Database writes: disabled", text)
        self.assertIn("shadow_v062", text)
        self.assertIn("BUILD_EURO_CONSUMER_PRICES_V062_SHADOW", text)
        self.assertIn("ROLLBACK", text.upper())

    def test_build_requires_backup_and_confirmation_before_engine(self):
        with patch(
            "project_scripts.diagnostics.remediate_euro_large_table.create_engine"
        ) as create_engine:
            with self.assertRaisesRegex(SystemExit, "backup-file"):
                main([
                    "EURO_CONSUMER_PRICES",
                    "--stage",
                    "build",
                ])

        create_engine.assert_not_called()

    def test_preflight_is_read_only_and_does_not_require_confirmation(self):
        output = StringIO()
        capacity = {
            "capacity_pass": True,
            "database_write_performed": False,
        }
        engine = MagicMock()
        with patch(
            "project_scripts.diagnostics.remediate_euro_large_table.create_engine",
            return_value=engine,
        ) as create_engine, patch(
            "project_scripts.diagnostics.remediate_euro_large_table."
            "estimate_large_rebuild_capacity",
            return_value=capacity,
        ) as estimate, redirect_stdout(output):
            result = main([
                "EURO_CONSUMER_PRICES",
                "--stage",
                "preflight",
            ])

        self.assertEqual(0, result)
        create_engine.assert_called_once()
        estimate.assert_called_once()
        engine.dispose.assert_called_once()
        self.assertIn("Database writes: disabled", output.getvalue())

    def test_report_name_includes_import_key(self):
        with TemporaryDirectory() as temp_dir:
            path = write_report(
                Path(temp_dir),
                "preflight",
                "20260811_120000",
                {"import_key": "EURO_MFI_INTEREST_RATES"},
            )

        self.assertEqual(
            "euro_mfi_interest_rates_preflight_20260811_120000.json",
            path.name,
        )


if __name__ == "__main__":
    unittest.main()
