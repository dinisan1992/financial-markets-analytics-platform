from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
import unittest

from services.ecb_shadow_build_service import (
    compare_source_shadow_row,
    build_ecb_shadow,
    repair_shadow_storage_hash,
    validate_build_import_key,
    validate_readiness_report,
)
from services.ecb_shadow_readiness_service import build_confirmation


IMPORT_KEY = "EURO_BANK_LENDING_SURVEY"
SUFFIX = "20260817_115720"


def readiness_payload():
    return {
        "plan_version": "v079",
        "suffix": SUFFIX,
        "database_write_performed": False,
        "active_csv_write_performed": False,
        "statements_executed": False,
        "error_count": 0,
        "plans": [
            {
                "import_key": IMPORT_KEY,
                "database_write_performed": False,
                "active_csv_write_performed": False,
                "statements_executed": False,
                "build_confirmation": build_confirmation(IMPORT_KEY),
                "blockers": [],
                "ready_for_shadow_build_authorization": True,
                "candidate": {
                    "file_name": "Bank Lending Survey.csv",
                    "bytes": 100,
                    "sha256": "A",
                },
                "backup": {
                    "file_name": "bls.sql",
                    "bytes": 200,
                    "sha256": "B",
                },
                "audit": {"source_rows": 10, "target_rows": 8},
                "planned_names": {
                    "shadow_table": (
                        "euro_bank_lending_survey__shadow_v079_"
                        f"{SUFFIX}"
                    ),
                    "retained_table": (
                        "euro_bank_lending_survey__pre_v079_"
                        f"{SUFFIX}"
                    ),
                    "shadow_exists": False,
                    "retained_exists": False,
                },
            }
        ],
    }


class EcbShadowBuildServiceTests(unittest.TestCase):
    def test_only_bls_is_buildable_in_this_checkpoint(self):
        self.assertEqual(IMPORT_KEY, validate_build_import_key(IMPORT_KEY))
        with self.assertRaisesRegex(ValueError, "not authorized"):
            validate_build_import_key("EURO_CARD_PAYMENTS")

    def test_readiness_report_rejects_executed_statements(self):
        payload = readiness_payload()
        payload["statements_executed"] = True

        with self.assertRaisesRegex(ValueError, "zero executed statements"):
            validate_readiness_report(payload, IMPORT_KEY)

    @patch("services.ecb_shadow_build_service.source_chunks")
    @patch("services.ecb_shadow_build_service.get_macro_import")
    def test_row_comparison_identifies_storage_column(
        self,
        contract_mock,
        chunks_mock,
    ):
        import pandas as pd

        contract_mock.return_value = {
            "table_name": "euro_bank_lending_survey",
            "column_aliases": {},
        }
        chunks_mock.return_value = [
            pd.DataFrame(
                [
                    {
                        "key_code": "KEY",
                        "time_period": "2020-Q2",
                        "obs_value": "1.25",
                    }
                ]
            )
        ]
        engine = MagicMock()
        row = {
            "key_code": "KEY",
            "time_period": "2020-Q2",
            "obs_value": "1.24",
            "_source_row_sha256": "A" * 64,
        }
        connection = engine.connect.return_value.__enter__.return_value
        connection.execute.return_value.mappings.return_value.one.return_value = row

        with patch(
            "services.ecb_shadow_build_service.mapped_source_columns",
            return_value=("key_code", "time_period", "obs_value"),
        ):
            result = compare_source_shadow_row(
                engine,
                IMPORT_KEY,
                "euro_bank_lending_survey__shadow_v079_test",
                "source.csv",
                "KEY",
                "2020-Q2",
            )

        self.assertEqual("obs_value", result["differences"][0]["column"])
        self.assertFalse(result["database_write_performed"])

    @patch("services.ecb_shadow_build_service.build_and_validate_shadows")
    def test_wrong_confirmation_stops_before_shadow_core(self, core):
        with self.assertRaisesRegex(ValueError, "--confirm must exactly match"):
            build_ecb_shadow(
                Mock(),
                IMPORT_KEY,
                confirmation="WRONG",
                readiness_payload=readiness_payload(),
                pin={},
                audit_payload={},
                staging_dir="staging",
                backup_dir="backup",
                workspace_dir="workspace",
            )

        core.assert_not_called()

    @patch("services.ecb_shadow_build_service.compare_source_shadow_row")
    def test_hash_repair_requires_canonical_equivalence(self, diagnose):
        diagnose.return_value = {
            "differences": [{"column": "obs_value"}],
            "source_hash": "A",
            "shadow_hash": "B",
        }
        with self.assertRaisesRegex(ValueError, "not canonically equivalent"):
            repair_shadow_storage_hash(
                MagicMock(),
                IMPORT_KEY,
                "euro_bank_lending_survey__shadow_v079_test",
                "source.csv",
                "KEY",
                "2020-Q2",
                confirmation=(
                    "REPAIR_EURO_BANK_LENDING_SURVEY_V079_SHADOW_HASHES"
                ),
            )

    @patch("services.ecb_shadow_build_service.compare_source_shadow_row")
    def test_hash_repair_updates_exactly_one_guarded_shadow_row(self, diagnose):
        diagnose.return_value = {
            "import_key": IMPORT_KEY,
            "shadow_table": "euro_bank_lending_survey__shadow_v079_test",
            "key_code": "KEY",
            "time_period": "2020-Q2",
            "stored_hash": "A" * 64,
            "source_hash": "B" * 64,
            "shadow_hash": "B" * 64,
            "differences": [],
            "database_write_performed": False,
        }
        engine = MagicMock()
        connection = engine.begin.return_value.__enter__.return_value
        connection.execute.return_value.rowcount = 1

        result = repair_shadow_storage_hash(
            engine,
            IMPORT_KEY,
            "euro_bank_lending_survey__shadow_v079_test",
            "source.csv",
            "KEY",
            "2020-Q2",
            confirmation=(
                "REPAIR_EURO_BANK_LENDING_SURVEY_V079_SHADOW_HASHES"
            ),
        )

        statement = str(connection.execute.call_args.args[0])
        self.assertIn("euro_bank_lending_survey__shadow_v079_test", statement)
        self.assertEqual(1, result["rows_updated"])
        self.assertTrue(result["database_write_performed"])
        self.assertFalse(result["active_table_changed"])

    @patch("services.ecb_shadow_build_service.shadow_table_evidence")
    @patch("services.ecb_shadow_build_service.active_table_checkpoint")
    @patch("services.ecb_shadow_build_service.validate_existing_shadows")
    @patch("services.ecb_shadow_build_service.build_and_validate_shadows")
    @patch("services.ecb_shadow_build_service.build_ecb_shadow_readiness")
    def test_build_uses_pinned_external_source_and_preserves_active_table(
        self,
        fresh_readiness,
        core,
        repeat,
        active_checkpoint,
        evidence,
    ):
        payload = readiness_payload()
        plan = payload["plans"][0]
        fresh_readiness.return_value = {
            **plan,
            "ready_for_shadow_build_authorization": True,
        }
        validation = Mock(
            shadow_table=plan["planned_names"]["shadow_table"],
            shadow_rows=10,
            valid=True,
        )
        validation.to_dict.return_value = {
            "shadow_rows": 10,
            "valid": True,
        }
        repeated = Mock(shadow_rows=10, valid=True)
        repeated.to_dict.return_value = {"shadow_rows": 10, "valid": True}
        core.return_value = {
            "validations": (validation,),
            "memory_bounded_validation": True,
        }
        repeat.return_value = (repeated,)
        active_checkpoint.side_effect = [
            {"data": "same", "schema": "same"},
            {"data": "same", "schema": "same"},
        ]
        evidence.return_value = {"hash_column_present": True}

        result = build_ecb_shadow(
            Mock(),
            IMPORT_KEY,
            confirmation=build_confirmation(IMPORT_KEY),
            readiness_payload=payload,
            pin={},
            audit_payload={"source_rows": 10},
            staging_dir="staging",
            backup_dir="backup",
            workspace_dir="workspace",
        )

        overrides = core.call_args.kwargs["source_path_overrides"]
        self.assertEqual(
            Path("staging").resolve() / "Bank Lending Survey.csv",
            overrides[IMPORT_KEY],
        )
        self.assertFalse(result["active_table_changed"])
        self.assertFalse(result["swap_authorized"])
        self.assertFalse(result["swap_performed"])


if __name__ == "__main__":
    unittest.main()
