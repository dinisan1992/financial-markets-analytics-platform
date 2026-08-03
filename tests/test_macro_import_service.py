from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib
from types import SimpleNamespace
import unittest

import pandas as pd

from config import BASE_DIR, EURO_SOURCE_DIR, FED_SOURCE_DIR
from macro_import_manifest import MACRO_IMPORTS, get_macro_import_keys
from services.macro_import_service import (
    apply_macro_import,
    normalize_source_columns,
    preview_macro_import,
    validate_sql_backup_for_table,
    run_import_cli,
)


class MacroImportManifestTests(unittest.TestCase):
    def test_manifest_covers_all_import_contracts(self):
        self.assertEqual(11, len(get_macro_import_keys("FED")))
        self.assertEqual(17, len(get_macro_import_keys("EURO")))
        self.assertEqual(28, len(MACRO_IMPORTS))

        for import_key, contract in MACRO_IMPORTS.items():
            expected_source_dir = (
                FED_SOURCE_DIR if contract["group"] == "FED" else EURO_SOURCE_DIR
            )
            self.assertEqual(
                expected_source_dir,
                Path(contract["csv_path"]).parent,
                import_key,
            )
            self.assertTrue((BASE_DIR / contract["script_name"]).exists(), import_key)
            self.assertTrue(contract["source_reference"].startswith("https://"))

    def test_euro_key_header_is_normalized_without_touching_data(self):
        contract = MACRO_IMPORTS["EURO_CONSUMER_PRICES"]
        frame = pd.DataFrame(
            {
                "KEY": ["ICP.M.U2.N.000000.4.INX"],
                "TIME_PERIOD": ["2026-01"],
                "OBS_VALUE": ["100.0"],
            }
        )
        normalized = normalize_source_columns(frame, contract)
        self.assertEqual(
            ["key_code", "time_period", "obs_value"],
            list(normalized.columns),
        )

    def test_all_import_entrypoints_are_import_safe(self):
        module_names = [
            ".".join(Path(contract["script_name"]).with_suffix("").parts)
            for contract in MACRO_IMPORTS.values()
        ]
        with patch(
            "services.macro_import_service.create_engine",
            side_effect=AssertionError("import attempted a database connection"),
        ):
            for module_name in module_names:
                module = importlib.import_module(module_name)
                importlib.reload(module)

    def test_local_legacy_archive_is_non_executable_when_present(self):
        archive = BASE_DIR / "tools" / "legacy" / "pre_v052"
        if not archive.exists():
            self.skipTest("Local Git-ignored legacy archive is not present")
        legacy_files = list(archive.glob("*.legacy.txt"))
        self.assertEqual(28, len(legacy_files))
        for path in legacy_files:
            self.assertGreater(path.stat().st_size, 0)

    def test_active_entrypoints_contain_no_direct_sql_write_code(self):
        forbidden = ("mysql.connector", ".to_sql(", "INSERT INTO")
        for import_key, contract in MACRO_IMPORTS.items():
            content = (BASE_DIR / contract["script_name"]).read_text(
                encoding="utf-8-sig"
            )
            for marker in forbidden:
                self.assertNotIn(marker, content, f"{import_key}: {marker}")


class MacroImportServiceTests(unittest.TestCase):
    def test_fed_preview_is_read_only_and_reports_invalid_and_duplicate_rows(self):
        with TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "fed.csv"
            source.write_text(
                "observation_date,M2SL\n"
                "2026-01-01,100\n"
                "2026-01-01,101\n"
                "invalid,102\n"
                "2026-02-01,invalid\n",
                encoding="utf-8",
            )
            preview = preview_macro_import(
                "FED_M2",
                full_scan=True,
                source_path=source,
            )

        self.assertEqual(4, preview.sampled_rows)
        self.assertEqual(1, preview.valid_sample_rows)
        self.assertEqual(2, preview.invalid_sample_rows)
        self.assertEqual(1, preview.duplicate_sample_keys)
        self.assertIn("invalid_source_rows", preview.blocked_reasons)
        self.assertIn("duplicate_source_keys", preview.blocked_reasons)
        self.assertFalse(preview.database_write_performed)
        self.assertFalse(preview.write_ready)

    def test_euro_preview_is_valid_but_write_blocked_pending_schema_contract(self):
        with TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "euro.csv"
            source.write_text(
                "KEY,TIME_PERIOD,OBS_VALUE\n"
                "ICP.TEST,2026-01,100\n",
                encoding="utf-8",
            )
            preview = preview_macro_import(
                "EURO_CONSUMER_PRICES",
                source_path=source,
            )

        self.assertEqual(1, preview.valid_sample_rows)
        self.assertEqual((), preview.missing_required_columns)
        self.assertIn("schema_remediation_required", preview.blocked_reasons)
        self.assertFalse(preview.write_ready)
        self.assertFalse(preview.database_write_performed)

    def test_sql_backup_requires_structure_and_data_for_exact_table(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.sql"
            path.write_text(
                "CREATE TABLE `fed_m2` (...);\n"
                "INSERT INTO `fed_m2` VALUES ('2026-01-01', 100);\n",
                encoding="utf-8",
            )
            result = validate_sql_backup_for_table(path, "fed_m2")

        self.assertGreater(result["bytes"], 0)
        self.assertEqual(64, len(result["sha256"]))

    def test_euro_update_is_rejected_before_any_engine_or_backup_access(self):
        with self.assertRaisesRegex(RuntimeError, "EURO SQL writes remain blocked"):
            apply_macro_import(
                "EURO_CONSUMER_PRICES",
                backup_file="missing.sql",
                confirm_table="euro_indices_consumer_prices",
            )

    def test_update_requires_exact_table_confirmation(self):
        with self.assertRaisesRegex(ValueError, "must exactly match fed_m2"):
            apply_macro_import(
                "FED_M2",
                backup_file="missing.sql",
                confirm_table="wrong_table",
            )

    def test_cli_requires_backup_and_table_confirmation_before_update(self):
        with patch(
            "services.macro_import_service.apply_macro_import"
        ) as apply_import:
            with self.assertRaisesRegex(SystemExit, "--backup-file"):
                run_import_cli("FED_M2", ["--update-sql"])
        apply_import.assert_not_called()

    def test_update_preflights_the_complete_source_before_writing(self):
        blocked_preview = SimpleNamespace(
            write_ready=False,
            blocked_reasons=("invalid_source_rows",),
        )
        with patch(
            "services.macro_import_service.validate_sql_backup_for_table",
            return_value={"sha256": "A" * 64},
        ), patch(
            "services.macro_import_service.preview_macro_import",
            return_value=blocked_preview,
        ) as preview_import:
            with self.assertRaisesRegex(RuntimeError, "invalid_source_rows"):
                apply_macro_import(
                    "FED_M2",
                    backup_file="backup.sql",
                    confirm_table="fed_m2",
                    engine=object(),
                )

        self.assertTrue(preview_import.call_args.kwargs["full_scan"])

    def test_update_uses_one_transaction_for_all_chunks(self):
        class FakeResult:
            rowcount = 1

        class FakeConnection:
            def __init__(self):
                self.execute_calls = 0

            def execute(self, statement, rows):
                self.execute_calls += 1
                return FakeResult()

        class FakeTransaction:
            def __init__(self, connection):
                self.connection = connection

            def __enter__(self):
                return self.connection

            def __exit__(self, exc_type, exc_value, traceback):
                return False

        class FakeEngine:
            def __init__(self):
                self.begin_calls = 0
                self.connection = FakeConnection()

            def begin(self):
                self.begin_calls += 1
                return FakeTransaction(self.connection)

        with TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "fed.csv"
            source.write_text(
                "observation_date,M2SL\n"
                "2026-01-01,100\n"
                "2026-02-01,101\n"
                "2026-03-01,102\n",
                encoding="utf-8",
            )
            engine = FakeEngine()
            ready_preview = SimpleNamespace(write_ready=True, blocked_reasons=())
            with patch(
                "services.macro_import_service.validate_sql_backup_for_table",
                return_value={"sha256": "A" * 64},
            ), patch(
                "services.macro_import_service.preview_macro_import",
                return_value=ready_preview,
            ):
                result = apply_macro_import(
                    "FED_M2",
                    backup_file="backup.sql",
                    confirm_table="fed_m2",
                    chunk_size=1,
                    engine=engine,
                    source_path=source,
                )

        self.assertEqual(1, engine.begin_calls)
        self.assertEqual(3, engine.connection.execute_calls)
        self.assertEqual(3, result["affected_rows"])


if __name__ == "__main__":
    unittest.main()
