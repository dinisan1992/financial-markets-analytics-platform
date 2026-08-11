from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from services.euro_direct_debits_shadow_service import EXPECTED_SOURCE_ROWS
from services.euro_direct_debits_swap_service import (
    SWAP_DIRECT_DEBITS_CONFIRMATION,
    SWAP_VERSION,
    swap_direct_debits_active,
)


class DirectDebitsSwapServiceTests(unittest.TestCase):
    def test_wrong_confirmation_stops_before_backup_and_database_access(self):
        with patch(
            "services.euro_direct_debits_swap_service."
            "validate_direct_debits_backup"
        ) as backup, patch(
            "services.euro_direct_debits_swap_service."
            "swap_validated_shadows"
        ) as core:
            with self.assertRaisesRegex(ValueError, "must exactly match"):
                swap_direct_debits_active(
                    Mock(),
                    "backup.sql",
                    "WRONG",
                    "20260811_163215",
                )
        backup.assert_not_called()
        core.assert_not_called()

    def test_swap_uses_delayed_hash_drop_and_validates_retained_copy(self):
        active = "euro_direct_debits"
        retained = "euro_direct_debits__pre_v069_20260811_163215"
        validation = Mock(
            active_table=active,
            shadow_table="euro_direct_debits__shadow_v069_20260811_163215",
            shadow_rows=EXPECTED_SOURCE_ROWS,
            valid=True,
        )
        before = {
            "data": {"rows": 75_647, "sha256": "A" * 64},
            "schema": {"sha256": "B" * 64},
        }
        after = {
            "data": {"rows": EXPECTED_SOURCE_ROWS, "sha256": "C" * 64},
            "schema": {"sha256": "D" * 64},
        }
        promoted = {"hash_column_present": True}
        final = {"rows": EXPECTED_SOURCE_ROWS, "hash_column_present": False}
        backup = {
            "path": Path("backup.sql"),
            "bytes": 1,
            "sha256": "E" * 64,
            "tables": (active,),
        }

        def core_swap(**kwargs):
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
                "backup": backup,
                "validations": (validation,),
                "retained_tables": (retained,),
                "database_write_performed": True,
                "active_tables_changed": True,
                "swap_statement": "RENAME TABLE ...",
                "rollback_statement": "RENAME TABLE ...",
                "hash_column_drop_stage": "after_validation",
            }

        with patch(
            "services.euro_direct_debits_swap_service."
            "validate_direct_debits_backup",
            return_value=backup,
        ), patch(
            "services.euro_direct_debits_swap_service."
            "validate_direct_debits_source",
            return_value={"path": Path("source.csv")},
        ), patch(
            "services.euro_direct_debits_swap_service."
            "validate_active_table_checkpoint",
            return_value=before,
        ), patch(
            "services.euro_direct_debits_swap_service.table_checkpoint",
            side_effect=[before, before, after],
        ), patch(
            "services.euro_direct_debits_swap_service.shadow_table_evidence",
            return_value=promoted,
        ), patch(
            "services.euro_direct_debits_swap_service.final_active_evidence",
            return_value=final,
        ), patch(
            "services.euro_direct_debits_swap_service.swap_validated_shadows",
            side_effect=core_swap,
        ) as core:
            result = swap_direct_debits_active(
                Mock(),
                "backup.sql",
                SWAP_DIRECT_DEBITS_CONFIRMATION,
                "20260811_163215",
            )

        self.assertEqual(SWAP_VERSION, result["version"])
        self.assertTrue(result["swap_performed"])
        self.assertFalse(result["rollback_performed"])
        self.assertFalse(core.call_args.kwargs["drop_hash_before_swap"])
        self.assertEqual(
            ("EURO_DIRECT_DEBITS",),
            core.call_args.kwargs["import_keys"],
        )


if __name__ == "__main__":
    unittest.main()
