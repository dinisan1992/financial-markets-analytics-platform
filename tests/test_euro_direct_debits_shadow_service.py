from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import unittest

from services.euro_direct_debits_shadow_service import (
    BUILD_DIRECT_DEBITS_CONFIRMATION,
    EXPECTED_SOURCE_ROWS,
    SHADOW_VERSION,
    VERIFIED_BACKUP_BYTES,
    VERIFIED_BACKUP_SHA256,
    build_direct_debits_shadow,
    validate_direct_debits_backup,
)


class DirectDebitsShadowServiceTests(unittest.TestCase):
    def test_wrong_confirmation_stops_before_backup_and_database_access(self):
        with patch(
            "services.euro_direct_debits_shadow_service."
            "validate_direct_debits_backup"
        ) as backup, patch(
            "services.euro_direct_debits_shadow_service."
            "build_and_validate_shadows"
        ) as core:
            with self.assertRaisesRegex(ValueError, "must exactly match"):
                build_direct_debits_shadow(
                    Mock(),
                    "backup.sql",
                    "WRONG",
                    "20260811_170000",
                )
        backup.assert_not_called()
        core.assert_not_called()

    def test_backup_must_match_verified_v068_evidence(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.sql"
            path.write_text("placeholder", encoding="utf-8")
            scoped = {
                "path": path,
                "bytes": VERIFIED_BACKUP_BYTES,
                "sha256": "0" * 64,
                "tables": ("euro_direct_debits",),
            }
            with patch(
                "services.euro_direct_debits_shadow_service."
                "validate_scoped_backup",
                return_value=scoped,
            ):
                with self.assertRaisesRegex(ValueError, "SHA-256"):
                    validate_direct_debits_backup(path)

    def test_build_is_one_table_memory_bounded_and_has_no_swap(self):
        shadow = "euro_direct_debits__shadow_v069_20260811_170000"
        validation = Mock(
            shadow_table=shadow,
            shadow_rows=EXPECTED_SOURCE_ROWS,
            valid=True,
        )
        core_result = {
            "backup": {
                "path": Path("backup.sql"),
                "bytes": VERIFIED_BACKUP_BYTES,
                "sha256": VERIFIED_BACKUP_SHA256,
                "tables": ("euro_direct_debits",),
            },
            "validations": (validation,),
            "database_write_performed": True,
            "active_tables_changed": False,
            "memory_bounded_validation": True,
        }
        checkpoint = {
            "data": {"rows": 75_647, "sha256": "A" * 64},
            "schema": {"sha256": "B" * 64},
        }
        evidence = {
            "time_period_type": "VARCHAR(20)",
            "primary_key": ("key_code", "time_period"),
        }
        with patch(
            "services.euro_direct_debits_shadow_service."
            "validate_direct_debits_backup",
            return_value=core_result["backup"],
        ), patch(
            "services.euro_direct_debits_shadow_service."
            "validate_direct_debits_source",
            return_value={
                "path": Path("source.csv"),
                "bytes": 1,
                "sha256": "C" * 64,
            },
        ), patch(
            "services.euro_direct_debits_shadow_service."
            "validate_active_table_checkpoint",
            side_effect=[checkpoint, checkpoint],
        ), patch(
            "services.euro_direct_debits_shadow_service."
            "shadow_table_evidence",
            return_value=evidence,
        ), patch(
            "services.euro_direct_debits_shadow_service."
            "build_and_validate_shadows",
            return_value=core_result,
        ) as core:
            result = build_direct_debits_shadow(
                Mock(),
                "backup.sql",
                BUILD_DIRECT_DEBITS_CONFIRMATION,
                "20260811_170000",
            )

        self.assertEqual(("EURO_DIRECT_DEBITS",), core.call_args.kwargs["import_keys"])
        self.assertEqual(SHADOW_VERSION, core.call_args.kwargs["version"])
        self.assertTrue(core.call_args.kwargs["memory_bounded"])
        self.assertFalse(result["active_table_changed"])
        self.assertFalse(result["swap_authorized"])
        self.assertFalse(result["swap_performed"])
        self.assertTrue(result["shadow_ready_for_swap_review"])

    def test_active_checkpoint_difference_fails_after_shadow_validation(self):
        shadow = "euro_direct_debits__shadow_v069_20260811_170000"
        validation = Mock(
            shadow_table=shadow,
            shadow_rows=EXPECTED_SOURCE_ROWS,
            valid=True,
        )
        before = {"data": {"rows": 1}, "schema": {"sha256": "A"}}
        after = {"data": {"rows": 2}, "schema": {"sha256": "A"}}
        with patch(
            "services.euro_direct_debits_shadow_service."
            "validate_direct_debits_backup",
            return_value={"path": Path("backup.sql")},
        ), patch(
            "services.euro_direct_debits_shadow_service."
            "validate_direct_debits_source",
            return_value={"path": Path("source.csv")},
        ), patch(
            "services.euro_direct_debits_shadow_service."
            "validate_active_table_checkpoint",
            side_effect=[before, after],
        ), patch(
            "services.euro_direct_debits_shadow_service."
            "shadow_table_evidence",
            return_value={},
        ), patch(
            "services.euro_direct_debits_shadow_service."
            "build_and_validate_shadows",
            return_value={
                "validations": (validation,),
                "database_write_performed": True,
                "active_tables_changed": False,
            },
        ):
            with self.assertRaisesRegex(RuntimeError, "changed during"):
                build_direct_debits_shadow(
                    Mock(),
                    "backup.sql",
                    BUILD_DIRECT_DEBITS_CONFIRMATION,
                    "20260811_170000",
                )


if __name__ == "__main__":
    unittest.main()
