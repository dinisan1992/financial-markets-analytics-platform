from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from services.ecb_shadow_readiness_service import (
    ECB_IMPORT_KEYS,
    PLAN_VERSION,
    build_confirmation,
    database_state_query,
    file_sha256,
    pinned_plans,
    readiness_blockers,
    swap_confirmation,
    validate_audit_payload,
)


class EcbShadowReadinessServiceTests(unittest.TestCase):
    def test_confirmations_are_versioned_and_exact(self):
        key = "EURO_BANK_LENDING_SURVEY"
        self.assertEqual(
            f"BUILD_{key}_{PLAN_VERSION.upper()}_SHADOW",
            build_confirmation(key),
        )
        self.assertEqual(
            f"SWAP_{key}_{PLAN_VERSION.upper()}_SHADOW",
            swap_confirmation(key),
        )

    def test_file_hash_is_sha256(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.csv"
            path.write_bytes(b"ecb\n")
            self.assertEqual(
                "ECB0574C296193B3CFAEAA1F725AB164339A2E29425E681EF8AA3D199187C709",
                file_sha256(path),
            )

    def test_pinned_plan_rejects_executed_statements(self):
        payload = {
            "database_write_performed": False,
            "active_csv_write_performed": False,
            "statements_executed": True,
            "plans": [],
        }
        with self.assertRaisesRegex(ValueError, "zero executed statements"):
            pinned_plans(payload)

    def test_pinned_plan_requires_all_three_imports(self):
        payload = {
            "database_write_performed": False,
            "active_csv_write_performed": False,
            "statements_executed": False,
            "plans": [
                {"import_key": ECB_IMPORT_KEYS[0], "sql_executed": False}
            ],
        }
        with self.assertRaisesRegex(ValueError, "incomplete"):
            pinned_plans(payload)

    def test_pinned_plan_rejects_active_csv_write(self):
        payload = {
            "database_write_performed": False,
            "active_csv_write_performed": True,
            "statements_executed": False,
            "plans": [],
        }
        with self.assertRaisesRegex(ValueError, "zero active CSV writes"):
            pinned_plans(payload)

    def test_pinned_plan_rejects_individual_sql_execution(self):
        payload = {
            "database_write_performed": False,
            "active_csv_write_performed": False,
            "statements_executed": False,
            "plans": [
                {
                    "import_key": import_key,
                    "sql_executed": import_key == ECB_IMPORT_KEYS[0],
                }
                for import_key in ECB_IMPORT_KEYS
            ],
        }
        with self.assertRaisesRegex(ValueError, "zero executed SQL"):
            pinned_plans(payload)

    def test_audit_payload_requires_exact_candidate(self):
        candidate = Path("candidate.csv").resolve()
        payload = {
            "import_key": ECB_IMPORT_KEYS[0],
            "source_path": str(candidate),
            "source_rows": 1,
            "database_write_performed": False,
        }
        self.assertIs(
            payload,
            validate_audit_payload(ECB_IMPORT_KEYS[0], payload, candidate),
        )

    def test_readiness_detects_changed_active_checkpoint(self):
        pin = {
            "candidate_sha256": "A",
            "backup_sha256": "B",
            "candidate_rows": 10,
            "active_rows": 8,
        }
        audit = {
            "source_rows": 10,
            "target_rows": 9,
            "period_type_safe": True,
        }
        blockers = readiness_blockers(
            pin,
            audit,
            {"sha256": "A"},
            {"sha256": "B"},
            {"target_rows": 9},
            {"capacity_pass": True},
            {"shadow_exists": False, "retained_exists": False},
        )
        self.assertIn("active_row_count_changed", blockers)

    def test_database_state_query_is_select_only(self):
        statement = str(database_state_query("euro_bank_lending_survey"))
        normalized = " ".join(statement.split()).upper()
        self.assertTrue(normalized.startswith("SELECT "))
        self.assertNotIn(" INSERT ", f" {normalized} ")
        self.assertNotIn(" UPDATE ", f" {normalized} ")
        self.assertNotIn(" DELETE ", f" {normalized} ")
        self.assertNotIn(" ALTER ", f" {normalized} ")


if __name__ == "__main__":
    unittest.main()
