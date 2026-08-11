from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest

from project_scripts.ingestion.sync_euro_macro import main


class SyncEuroMacroCliTests(unittest.TestCase):
    def test_apply_requires_backup_and_confirmation_before_engine_creation(self):
        with patch(
            "project_scripts.ingestion.sync_euro_macro.create_engine"
        ) as create_engine:
            with self.assertRaisesRegex(SystemExit, "--backup-file"):
                main(["EURO_CONSUMER_PRICES", "--apply"])

        create_engine.assert_not_called()

    def test_default_command_writes_read_only_plan_report(self):
        plan = SimpleNamespace(
            write_ready=True,
            to_dict=lambda: {
                "planned_inserts": 0,
                "planned_updates": 0,
                "database_write_performed": False,
            },
        )
        engine = Mock()
        with TemporaryDirectory() as temp_dir, patch(
            "project_scripts.ingestion.sync_euro_macro.create_engine",
            return_value=engine,
        ), patch(
            "project_scripts.ingestion.sync_euro_macro.build_euro_sync_plan",
            return_value=plan,
        ), patch(
            "project_scripts.ingestion.sync_euro_macro.apply_euro_sync"
        ) as apply_sync:
            result = main([
                "EURO_CONSUMER_PRICES",
                "--output-dir",
                temp_dir,
            ])
            reports = list(Path(temp_dir).glob("*.json"))

        self.assertEqual(0, result)
        self.assertEqual(1, len(reports))
        apply_sync.assert_not_called()
        engine.dispose.assert_called_once_with()

    def test_fail_on_blocker_returns_two_without_applying(self):
        plan = SimpleNamespace(
            write_ready=False,
            to_dict=lambda: {
                "blockers": ["target_only_rows_require_review"],
                "database_write_performed": False,
            },
        )
        engine = Mock()
        with TemporaryDirectory() as temp_dir, patch(
            "project_scripts.ingestion.sync_euro_macro.create_engine",
            return_value=engine,
        ), patch(
            "project_scripts.ingestion.sync_euro_macro.build_euro_sync_plan",
            return_value=plan,
        ):
            result = main([
                "EURO_CONSUMER_PRICES",
                "--fail-on-blocker",
                "--output-dir",
                temp_dir,
            ])

        self.assertEqual(2, result)


if __name__ == "__main__":
    unittest.main()
