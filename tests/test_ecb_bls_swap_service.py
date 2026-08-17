from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from services.ecb_bls_swap_service import (
    IMPORT_KEY,
    SWAP_BLS_CONFIRMATION,
    canonical_evidence,
    swap_bls_active,
    validate_build_report,
)


SUFFIX = "20260817_115720"
SHADOW = f"euro_bank_lending_survey__shadow_v079_{SUFFIX}"


def readiness_plan():
    return {
        "audit": {"source_rows": 10},
        "planned_names": {"shadow_table": SHADOW},
    }


def build_report():
    validation = {"valid": True, "shadow_rows": 10}
    return {
        "stage": "shadow_hash_repair_and_validation",
        "version": "v079",
        "import_key": IMPORT_KEY,
        "shadow_table": SHADOW,
        "first_validation": validation,
        "second_validation": validation,
        "active_table_changed": False,
        "shadow_ready_for_swap_review": True,
        "swap_authorized": False,
        "swap_performed": False,
        "shadow_evidence": {"hash_column_present": True},
    }


class EcbBlsSwapServiceTests(unittest.TestCase):
    def test_canonical_evidence_treats_json_lists_as_runtime_tuples(self):
        from_report = {
            "primary_key": ["key_code", "time_period"],
            "indexes": [],
        }
        from_database = {
            "primary_key": ("key_code", "time_period"),
            "indexes": (),
        }

        self.assertEqual(
            canonical_evidence(from_report),
            canonical_evidence(from_database),
        )

    def test_build_report_rejects_prior_swap(self):
        payload = build_report()
        payload["swap_performed"] = True

        with self.assertRaisesRegex(ValueError, "already records a swap"):
            validate_build_report(payload, readiness_plan())

    @patch("services.ecb_bls_swap_service.swap_validated_shadows")
    def test_wrong_confirmation_stops_before_swap_core(self, core):
        with self.assertRaisesRegex(ValueError, "must exactly match"):
            swap_bls_active(
                Mock(),
                confirmation="WRONG",
                readiness_payload={},
                build_payload={},
                staging_dir="staging",
                backup_dir="backup",
                workspace_dir="workspace",
            )

        core.assert_not_called()

    @patch("services.ecb_bls_swap_service.final_active_evidence")
    @patch("services.ecb_bls_swap_service.audit_euro_source_against_target")
    @patch("services.ecb_bls_swap_service.shadow_table_evidence")
    @patch("services.ecb_bls_swap_service.table_checkpoint")
    @patch("services.ecb_bls_swap_service.active_table_checkpoint")
    @patch("services.ecb_bls_swap_service.validate_scoped_backup")
    @patch("services.ecb_bls_swap_service._validate_pinned_file")
    @patch("services.ecb_bls_swap_service.validate_readiness_report")
    @patch("services.ecb_bls_swap_service.swap_validated_shadows")
    def test_swap_delays_hash_drop_and_preserves_retained_checkpoint(
        self,
        core,
        readiness,
        pinned_file,
        scoped_backup,
        active_checkpoint,
        table_checkpoint_mock,
        shadow_evidence_mock,
        source_audit,
        final_evidence,
    ):
        plan = {
            **readiness_plan(),
            "candidate": {"file_name": "Bank Lending Survey.csv"},
            "backup": {"file_name": "bls.sql"},
        }
        readiness.return_value = (SUFFIX, plan)
        pinned_file.side_effect = [
            {"file_name": "Bank Lending Survey.csv", "sha256": "A"},
            {"file_name": "bls.sql", "sha256": "B"},
        ]
        scoped_backup.return_value = {"sha256": "B", "path": Path("bls.sql")}
        before = {
            "table": "euro_bank_lending_survey",
            "data": {"rows": 8},
            "schema": {
                "sha256": "S",
                "primary_key": ("key_code", "time_period"),
            },
        }
        retained_checkpoint = {
            "data": before["data"],
            "schema": {
                "sha256": "S",
                "primary_key": ["key_code", "time_period"],
            },
        }
        active_checkpoint.side_effect = [before, {"data": {"rows": 10}}]
        build = build_report()
        build["active_after"] = before
        build["shadow_evidence"] = {"hash_column_present": True}
        retained = f"euro_bank_lending_survey__pre_v079_{SUFFIX}"
        table_checkpoint_mock.return_value = retained_checkpoint
        shadow_evidence_mock.return_value = build["shadow_evidence"]
        source_audit.return_value = Mock(valid=True, to_dict=lambda: {"valid": True})
        final_evidence.return_value = {"rows": 10, "hash_column_present": False}
        validation = Mock(valid=True, shadow_rows=10)

        def run_core(**kwargs):
            kwargs["post_swap_validator"](
                engine=kwargs["engine"],
                validations=(validation,),
                retained_tables=(retained,),
            )
            kwargs["post_hash_drop_validator"](
                engine=kwargs["engine"],
                validations=(validation,),
                retained_tables=(retained,),
            )
            return {
                "backup": scoped_backup.return_value,
                "validations": (validation,),
                "retained_tables": (retained,),
                "database_write_performed": True,
                "active_tables_changed": True,
                "memory_bounded_validation": True,
            }

        core.side_effect = run_core
        result = swap_bls_active(
            Mock(),
            confirmation=SWAP_BLS_CONFIRMATION,
            readiness_payload={},
            build_payload=build,
            staging_dir="staging",
            backup_dir="backup",
            workspace_dir="workspace",
        )

        self.assertFalse(core.call_args.kwargs["drop_hash_before_swap"])
        self.assertEqual(
            {IMPORT_KEY: Path("staging").resolve() / "Bank Lending Survey.csv"},
            core.call_args.kwargs["source_path_overrides"],
        )
        self.assertEqual(retained_checkpoint, result["retained_checkpoint"])
        self.assertTrue(result["swap_performed"])
        self.assertFalse(result["rollback_performed"])


if __name__ == "__main__":
    unittest.main()
