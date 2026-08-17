from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from services.ecb_shadow_post_build_service import (
    validate_build_report,
    verify_ecb_shadow_build,
)


IMPORT_KEY = "EURO_BALANCE_SHEET_ITEMS"
SUFFIX = "20260817_141854"
ACTIVE = "euro_balance_sheet_items"
SHADOW = f"{ACTIVE}__shadow_v079_{SUFFIX}"
ROWS = 10


def validation():
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


def readiness_plan():
    return {
        "suffix": SUFFIX,
        "candidate": {"file_name": "Balance Sheet Items.csv", "bytes": 1},
        "backup": {
            "file_name": "bsi.sql",
            "bytes": 2,
            "sha256": "B",
            "structure_and_data_verified": True,
        },
        "audit": {"source_rows": ROWS, "target_rows": 8},
        "planned_names": {"shadow_table": SHADOW},
    }


def build_report():
    checkpoint = {"table": ACTIVE, "data": {"rows": 8}, "schema": {}}
    return {
        "stage": "shadow_build",
        "version": "v079",
        "import_key": IMPORT_KEY,
        "suffix": SUFFIX,
        "readiness_report_file": "readiness.json",
        "readiness_report_sha256": "READINESS_SHA",
        "source": readiness_plan()["candidate"],
        "backup": readiness_plan()["backup"],
        "shadow_table": SHADOW,
        "shadow_evidence": {"hash_column_present": True},
        "initial_validation": validation(),
        "repeated_validation": validation(),
        "active_before": checkpoint,
        "active_after": checkpoint,
        "database_write_performed": True,
        "database_write_scope": "versioned_shadow_table_only",
        "active_table_changed": False,
        "active_tables_changed": False,
        "active_csv_write_performed": False,
        "shadow_ready_for_swap_review": True,
        "swap_authorized": False,
        "swap_performed": False,
    }


class EcbShadowPostBuildServiceTests(unittest.TestCase):
    def test_build_report_rejects_mismatch(self):
        payload = build_report()
        payload["repeated_validation"]["row_hash_mismatches"] = 1
        with self.assertRaisesRegex(ValueError, "row_hash_mismatches"):
            validate_build_report(
                payload,
                readiness_plan(),
                readiness_report_file="readiness.json",
                readiness_report_sha256="READINESS_SHA",
            )

    @patch(
        "services.ecb_shadow_post_build_service.validate_existing_shadows"
    )
    @patch("services.ecb_shadow_post_build_service.shadow_summary")
    @patch("services.ecb_shadow_post_build_service.shadow_table_evidence")
    @patch("services.ecb_shadow_post_build_service.active_table_checkpoint")
    @patch("services.ecb_shadow_post_build_service.inspect")
    @patch("services.ecb_shadow_post_build_service.validate_scoped_backup")
    @patch("services.ecb_shadow_post_build_service._validate_pinned_file")
    @patch("services.ecb_shadow_post_build_service.get_macro_import")
    @patch("services.ecb_shadow_post_build_service.validate_readiness_report")
    def test_verification_is_read_only_and_preserves_active(
        self,
        readiness,
        contract,
        pinned_file,
        scoped_backup,
        inspect_mock,
        active_checkpoint,
        shadow_evidence,
        summary,
        validate_shadow,
    ):
        plan = readiness_plan()
        plan.pop("suffix")
        readiness.return_value = (SUFFIX, plan)
        contract.return_value = {"table_name": ACTIVE}
        pinned_file.return_value = readiness_plan()["candidate"]
        scoped_backup.return_value = {
            "bytes": 2,
            "sha256": "B",
        }
        inspect_mock.return_value.get_table_names.return_value = [ACTIVE, SHADOW]
        checkpoint = build_report()["active_after"]
        active_checkpoint.side_effect = [checkpoint, checkpoint]
        shadow_evidence.return_value = {"hash_column_present": True}
        summary.return_value = {
            "rows": ROWS,
            "unique_business_keys": ROWS,
            "null_business_keys": 0,
        }
        validated = Mock(valid=True, to_dict=validation)
        validate_shadow.return_value = (validated,)

        result = verify_ecb_shadow_build(
            Mock(),
            IMPORT_KEY,
            readiness_payload={},
            build_payload=build_report(),
            readiness_report_file="readiness.json",
            readiness_report_sha256="READINESS_SHA",
            build_report_file="build.json",
            build_report_sha256="BUILD_SHA",
            staging_dir=Path("staging"),
            backup_dir=Path("backup"),
            workspace_dir=Path("workspace"),
        )

        self.assertFalse(result["database_write_performed"])
        self.assertFalse(result["active_table_changed"])
        self.assertFalse(result["swap_authorized"])
        self.assertFalse(result["swap_performed"])
        self.assertTrue(result["shadow_ready_for_review"])

    @patch(
        "services.ecb_shadow_post_build_service.validate_existing_shadows"
    )
    def test_unsupported_import_stops_before_validation(self, validate_shadow):
        with self.assertRaisesRegex(ValueError, "not enabled"):
            verify_ecb_shadow_build(
                Mock(),
                "EURO_CARD_PAYMENTS",
                readiness_payload={},
                build_payload={},
                readiness_report_file="readiness.json",
                readiness_report_sha256="A",
                build_report_file="build.json",
                build_report_sha256="B",
                staging_dir="staging",
                backup_dir="backup",
                workspace_dir="workspace",
            )
        validate_shadow.assert_not_called()


if __name__ == "__main__":
    unittest.main()
