from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from services.ecb_pcp_swap_service import (
    IMPORT_KEY,
    SWAP_PCP_CONFIRMATION,
    canonical_evidence,
    preflight_pcp_swap,
    swap_pcp_active,
    validate_build_report,
    validate_post_build_report,
)


SUFFIX = "20260817_115720"
ACTIVE = "euro_card_payments"
SHADOW = f"{ACTIVE}__shadow_v079_{SUFFIX}"
RETAINED = f"{ACTIVE}__pre_v079_{SUFFIX}"
ROWS = 10


def readiness_plan():
    return {
        "plan_version": "v079",
        "import_key": IMPORT_KEY,
        "active_table": ACTIVE,
        "candidate": {
            "file_name": "Card payments.csv",
            "bytes": 100,
            "sha256": "A",
        },
        "backup": {
            "file_name": "pcp.sql",
            "bytes": 200,
            "sha256": "B",
            "structure_and_data_verified": True,
        },
        "audit": {"source_rows": ROWS, "target_rows": 8},
        "planned_names": {
            "shadow_table": SHADOW,
            "retained_table": RETAINED,
        },
    }


def complete_validation():
    return {
        "valid": True,
        "source_rows": ROWS,
        "shadow_rows": ROWS,
        "source_unique_business_keys": ROWS,
        "shadow_unique_business_keys": ROWS,
        "null_business_keys": 0,
        "duplicate_business_key_groups": 0,
        "row_hash_mismatches": 0,
        "source_hash_mismatches": 0,
        "missing_source_rows": 0,
    }


def active_checkpoint():
    return {
        "table": ACTIVE,
        "data": {"rows": 8, "sha256": "DATA"},
        "schema": {
            "sha256": "SCHEMA",
            "primary_key": ["key_code", "time_period"],
        },
    }


def shadow_evidence():
    return {
        "column_count": 36,
        "primary_key": ["key_code", "time_period"],
        "hash_column_present": True,
        "schema": {"sha256": "SHADOW"},
    }


def build_report():
    checkpoint = active_checkpoint()
    return {
        "stage": "shadow_build",
        "version": "v079",
        "import_key": IMPORT_KEY,
        "suffix": SUFFIX,
        "source": readiness_plan()["candidate"],
        "backup": readiness_plan()["backup"],
        "shadow_table": SHADOW,
        "shadow_evidence": shadow_evidence(),
        "initial_validation": complete_validation(),
        "repeated_validation": complete_validation(),
        "active_before": checkpoint,
        "active_after": checkpoint,
        "database_write_performed": True,
        "database_write_scope": "versioned_shadow_table_only",
        "active_table_changed": False,
        "active_tables_changed": False,
        "shadow_ready_for_swap_review": True,
        "swap_authorized": False,
        "swap_performed": False,
        "readiness_report_file": "readiness.json",
        "readiness_report_sha256": "READINESS_SHA",
    }


def post_build_report(build=None):
    build = build or build_report()
    return {
        "stage": "post_build_verification",
        "version": "v082",
        "import_key": IMPORT_KEY,
        "source_build_report_file": "build.json",
        "source_build_report_sha256": "BUILD_SHA",
        "active_checkpoint": build["active_after"],
        "active_unchanged": True,
        "tables": [ACTIVE, SHADOW],
        "row_counts": {ACTIVE: 8, SHADOW: ROWS},
        "shadow_evidence": build["shadow_evidence"],
        "initial_validation": build["initial_validation"],
        "repeated_validation": build["repeated_validation"],
        "database_write_performed": False,
        "active_csv_write_performed": False,
        "swap_authorized": False,
        "swap_performed": False,
        "shadow_ready_for_review": True,
    }


class EcbPcpSwapServiceTests(unittest.TestCase):
    def test_canonical_evidence_treats_json_lists_as_runtime_tuples(self):
        self.assertEqual(
            canonical_evidence({"key": ["a", "b"]}),
            canonical_evidence({"key": ("a", "b")}),
        )

    def test_build_report_rejects_nonzero_hash_mismatches(self):
        payload = build_report()
        payload["repeated_validation"]["row_hash_mismatches"] = 1

        with self.assertRaisesRegex(ValueError, "row_hash_mismatches"):
            validate_build_report(
                payload,
                readiness_plan(),
                readiness_report_file="readiness.json",
                readiness_report_sha256="READINESS_SHA",
            )

    def test_post_build_report_rejects_active_csv_write(self):
        build = build_report()
        payload = post_build_report(build)
        payload["active_csv_write_performed"] = True

        with self.assertRaisesRegex(ValueError, "active CSV"):
            validate_post_build_report(
                payload,
                build,
                readiness_plan(),
                build_report_file="build.json",
                build_report_sha256="BUILD_SHA",
            )

    @patch("services.ecb_pcp_swap_service.inspect")
    @patch("services.ecb_pcp_swap_service.validate_existing_shadows")
    @patch("services.ecb_pcp_swap_service._validated_swap_context")
    def test_preflight_is_read_only_and_requires_unused_future_names(
        self,
        context_mock,
        validate_shadow,
        inspect_mock,
    ):
        context_mock.return_value = {
            "suffix": SUFFIX,
            "source_path": Path("source.csv"),
            "source": {"sha256": "A"},
            "backup": {"sha256": "B"},
            "active_table": ACTIVE,
            "active_before": active_checkpoint(),
            "shadow_table": SHADOW,
            "shadow_before": shadow_evidence(),
            "expected_rows": ROWS,
            "expected_retained_name": RETAINED,
        }
        validation = Mock(
            valid=True,
            shadow_rows=ROWS,
            to_dict=lambda: {"valid": True, "shadow_rows": ROWS},
        )
        validate_shadow.return_value = (validation,)
        inspect_mock.return_value.get_table_names.return_value = [ACTIVE, SHADOW]

        result = preflight_pcp_swap(
            Mock(),
            readiness_payload={},
            build_payload={},
            post_build_payload={},
            readiness_report_file="readiness.json",
            readiness_report_sha256="READINESS_SHA",
            build_report_file="build.json",
            build_report_sha256="BUILD_SHA",
            staging_dir="staging",
            backup_dir="backup",
            workspace_dir="workspace",
        )

        self.assertTrue(result["ready_for_swap_authorization"])
        self.assertFalse(result["database_write_performed"])
        self.assertFalse(result["swap_authorized"])
        self.assertFalse(result["swap_performed"])

    @patch("services.ecb_pcp_swap_service.inspect")
    @patch("services.ecb_pcp_swap_service.validate_existing_shadows")
    @patch("services.ecb_pcp_swap_service._validated_swap_context")
    def test_preflight_rejects_existing_retained_name(
        self,
        context_mock,
        validate_shadow,
        inspect_mock,
    ):
        context_mock.return_value = {
            "suffix": SUFFIX,
            "source_path": Path("source.csv"),
            "source": {"sha256": "A"},
            "backup": {"sha256": "B"},
            "active_table": ACTIVE,
            "active_before": active_checkpoint(),
            "shadow_table": SHADOW,
            "shadow_before": shadow_evidence(),
            "expected_rows": ROWS,
            "expected_retained_name": RETAINED,
        }
        validate_shadow.return_value = (
            Mock(valid=True, shadow_rows=ROWS, to_dict=lambda: {}),
        )
        inspect_mock.return_value.get_table_names.return_value = [
            ACTIVE,
            SHADOW,
            RETAINED,
        ]

        with self.assertRaisesRegex(RuntimeError, "already exists"):
            preflight_pcp_swap(
                Mock(),
                readiness_payload={},
                build_payload={},
                post_build_payload={},
                readiness_report_file="readiness.json",
                readiness_report_sha256="READINESS_SHA",
                build_report_file="build.json",
                build_report_sha256="BUILD_SHA",
                staging_dir="staging",
                backup_dir="backup",
                workspace_dir="workspace",
            )

    @patch("services.ecb_pcp_swap_service.swap_validated_shadows")
    def test_wrong_confirmation_stops_before_swap_core(self, core):
        with self.assertRaisesRegex(ValueError, "must exactly match"):
            swap_pcp_active(
                Mock(),
                confirmation="WRONG",
                readiness_payload={},
                build_payload={},
                post_build_payload={},
                readiness_report_file="readiness.json",
                readiness_report_sha256="READINESS_SHA",
                build_report_file="build.json",
                build_report_sha256="BUILD_SHA",
                staging_dir="staging",
                backup_dir="backup",
                workspace_dir="workspace",
            )

        core.assert_not_called()

    @patch("services.ecb_pcp_swap_service.shadow_table_evidence")
    @patch("services.ecb_pcp_swap_service.active_table_checkpoint")
    @patch("services.ecb_pcp_swap_service.validate_scoped_backup")
    @patch("services.ecb_pcp_swap_service._validate_pinned_file")
    @patch("services.ecb_pcp_swap_service.validate_readiness_report")
    @patch("services.ecb_pcp_swap_service.swap_validated_shadows")
    def test_changed_active_checkpoint_stops_before_swap_core(
        self,
        core,
        readiness,
        pinned_file,
        scoped_backup,
        current_active,
        current_shadow,
    ):
        plan = readiness_plan()
        readiness.return_value = (SUFFIX, plan)
        pinned_file.side_effect = [
            {"file_name": "Card payments.csv", "sha256": "A"},
            {"file_name": "pcp.sql", "sha256": "B"},
        ]
        scoped_backup.return_value = {"sha256": "B"}
        changed = active_checkpoint()
        changed["data"] = {"rows": 9, "sha256": "CHANGED"}
        current_active.return_value = changed

        build = build_report()
        with self.assertRaisesRegex(ValueError, "checkpoint changed"):
            swap_pcp_active(
                Mock(),
                confirmation=SWAP_PCP_CONFIRMATION,
                readiness_payload={},
                build_payload=build,
                post_build_payload=post_build_report(build),
                readiness_report_file="readiness.json",
                readiness_report_sha256="READINESS_SHA",
                build_report_file="build.json",
                build_report_sha256="BUILD_SHA",
                staging_dir="staging",
                backup_dir="backup",
                workspace_dir="workspace",
            )

        current_shadow.assert_not_called()
        core.assert_not_called()

    @patch("services.ecb_pcp_swap_service.shadow_table_evidence")
    @patch("services.ecb_pcp_swap_service.active_table_checkpoint")
    @patch("services.ecb_pcp_swap_service.validate_scoped_backup")
    @patch("services.ecb_pcp_swap_service._validate_pinned_file")
    @patch("services.ecb_pcp_swap_service.validate_readiness_report")
    @patch("services.ecb_pcp_swap_service.swap_validated_shadows")
    def test_changed_shadow_evidence_stops_before_swap_core(
        self,
        core,
        readiness,
        pinned_file,
        scoped_backup,
        current_active,
        current_shadow,
    ):
        plan = readiness_plan()
        readiness.return_value = (SUFFIX, plan)
        pinned_file.side_effect = [
            {"file_name": "Card payments.csv", "sha256": "A"},
            {"file_name": "pcp.sql", "sha256": "B"},
        ]
        scoped_backup.return_value = {"sha256": "B"}
        current_active.return_value = active_checkpoint()
        changed = shadow_evidence()
        changed["schema"] = {"sha256": "CHANGED"}
        current_shadow.return_value = changed

        build = build_report()
        with self.assertRaisesRegex(ValueError, "shadow schema changed"):
            swap_pcp_active(
                Mock(),
                confirmation=SWAP_PCP_CONFIRMATION,
                readiness_payload={},
                build_payload=build,
                post_build_payload=post_build_report(build),
                readiness_report_file="readiness.json",
                readiness_report_sha256="READINESS_SHA",
                build_report_file="build.json",
                build_report_sha256="BUILD_SHA",
                staging_dir="staging",
                backup_dir="backup",
                workspace_dir="workspace",
            )

        core.assert_not_called()

    @patch("services.ecb_pcp_swap_service.final_active_evidence")
    @patch("services.ecb_pcp_swap_service.audit_euro_source_against_target")
    @patch("services.ecb_pcp_swap_service.shadow_table_evidence")
    @patch("services.ecb_pcp_swap_service.table_checkpoint")
    @patch("services.ecb_pcp_swap_service.active_table_checkpoint")
    @patch("services.ecb_pcp_swap_service.validate_scoped_backup")
    @patch("services.ecb_pcp_swap_service._validate_pinned_file")
    @patch("services.ecb_pcp_swap_service.validate_readiness_report")
    @patch("services.ecb_pcp_swap_service.swap_validated_shadows")
    def test_swap_revalidates_and_preserves_retained_checkpoint(
        self,
        core,
        readiness,
        pinned_file,
        scoped_backup,
        current_active,
        retained_checkpoint_mock,
        current_shadow,
        source_audit,
        final_evidence,
    ):
        plan = readiness_plan()
        readiness.return_value = (SUFFIX, plan)
        pinned_file.side_effect = [
            {"file_name": "Card payments.csv", "sha256": "A"},
            {"file_name": "pcp.sql", "sha256": "B"},
        ]
        scoped_backup.return_value = {"sha256": "B", "path": Path("pcp.sql")}
        before = active_checkpoint()
        after = {"data": {"rows": ROWS}}
        current_active.side_effect = [before, after]
        retained_checkpoint = {
            "data": before["data"],
            "schema": {
                "sha256": "SCHEMA",
                "primary_key": ("key_code", "time_period"),
            },
        }
        retained_checkpoint_mock.return_value = retained_checkpoint
        current_shadow.return_value = shadow_evidence()
        source_audit.return_value = Mock(
            valid=True,
            to_dict=lambda: {"valid": True},
        )
        final_evidence.return_value = {
            "rows": ROWS,
            "hash_column_present": False,
        }
        validation = Mock(valid=True, shadow_rows=ROWS)

        def run_core(**kwargs):
            kwargs["post_swap_validator"](
                engine=kwargs["engine"],
                validations=(validation,),
                retained_tables=(RETAINED,),
            )
            kwargs["post_hash_drop_validator"](
                engine=kwargs["engine"],
                validations=(validation,),
                retained_tables=(RETAINED,),
            )
            return {
                "backup": scoped_backup.return_value,
                "validations": (validation,),
                "retained_tables": (RETAINED,),
                "database_write_performed": True,
                "active_tables_changed": True,
                "memory_bounded_validation": True,
            }

        core.side_effect = run_core
        build = build_report()
        result = swap_pcp_active(
            Mock(),
            confirmation=SWAP_PCP_CONFIRMATION,
            readiness_payload={},
            build_payload=build,
            post_build_payload=post_build_report(build),
            readiness_report_file="readiness.json",
            readiness_report_sha256="READINESS_SHA",
            build_report_file="build.json",
            build_report_sha256="BUILD_SHA",
            staging_dir="staging",
            backup_dir="backup",
            workspace_dir="workspace",
        )

        self.assertFalse(core.call_args.kwargs["drop_hash_before_swap"])
        self.assertEqual(
            {IMPORT_KEY: Path("staging").resolve() / "Card payments.csv"},
            core.call_args.kwargs["source_path_overrides"],
        )
        self.assertEqual(retained_checkpoint, result["retained_checkpoint"])
        self.assertTrue(result["swap_performed"])
        self.assertFalse(result["rollback_performed"])


if __name__ == "__main__":
    unittest.main()
