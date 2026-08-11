import json
import os
from pathlib import Path
import tempfile
import unittest

from macro_import_manifest import get_macro_import_keys
from services.euro_sync_status_service import (
    load_latest_euro_sync_status,
    summarize_euro_sync_status,
)


class EuroSyncStatusServiceTests(unittest.TestCase):
    def _write_report(self, root, import_key, suffix, plan, database_write=False):
        path = Path(root) / f"{import_key.lower()}_sync_{suffix}.json"
        path.write_text(
            json.dumps(
                {
                    "stage": "plan",
                    "import_key": import_key,
                    "plan": plan,
                    "database_write_performed": database_write,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_classifies_exact_changes_blocked_and_keeps_all_contracts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write_report(
                tmp,
                "EURO_FRAUD_LOSSES",
                "20260101_010101",
                {
                    "table_name": "euro_losses_due_to_fraud",
                    "source_path": r"C:\private\Losses.csv",
                    "source_rows": 10,
                    "target_rows": 10,
                    "unchanged_rows": 10,
                    "write_ready": True,
                    "idempotent": True,
                    "blockers": [],
                },
            )
            self._write_report(
                tmp,
                "EURO_CARD_PAYMENTS",
                "20260101_010102",
                {
                    "source_rows": 12,
                    "target_rows": 10,
                    "planned_inserts": 2,
                    "write_ready": True,
                    "idempotent": False,
                    "blockers": [],
                },
            )
            self._write_report(
                tmp,
                "EURO_DIRECT_DEBITS",
                "20260101_010103",
                {
                    "source_rows": 9,
                    "target_rows": 10,
                    "target_only_rows": 1,
                    "write_ready": False,
                    "idempotent": False,
                    "blockers": ["target_only_rows_require_review"],
                },
            )

            frame = load_latest_euro_sync_status(tmp, as_of="2026-01-10")
            by_key = frame.set_index("import_key")

            self.assertEqual(len(get_macro_import_keys("EURO")), len(frame))
            self.assertEqual("EXACT", by_key.loc["EURO_FRAUD_LOSSES", "status"])
            self.assertEqual("CHANGES", by_key.loc["EURO_CARD_PAYMENTS", "status"])
            self.assertEqual("BLOCKED", by_key.loc["EURO_DIRECT_DEBITS", "status"])
            self.assertEqual(
                "NOT_AUDITED",
                by_key.loc["EURO_MFI_INTEREST_RATES", "status"],
            )
            self.assertEqual("Losses.csv", by_key.loc["EURO_FRAUD_LOSSES", "source_file"])
            self.assertNotIn("C:\\private", by_key.loc["EURO_FRAUD_LOSSES", "source_file"])

    def test_latest_report_wins_and_summary_counts_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = self._write_report(
                tmp,
                "EURO_RETAIL_INTEREST_RATES",
                "old",
                {"planned_updates": 5, "idempotent": False, "blockers": []},
            )
            new = self._write_report(
                tmp,
                "EURO_RETAIL_INTEREST_RATES",
                "new",
                {
                    "planned_inserts": 0,
                    "planned_updates": 0,
                    "target_only_rows": 0,
                    "idempotent": True,
                    "write_ready": True,
                    "blockers": [],
                },
            )
            os.utime(old, (100, 100))
            os.utime(new, (200, 200))

            frame = load_latest_euro_sync_status(tmp)
            summary = summarize_euro_sync_status(frame)

            self.assertEqual(
                "EXACT",
                frame.set_index("import_key").loc[
                    "EURO_RETAIL_INTEREST_RATES", "status"
                ],
            )
            self.assertEqual(1, summary["exact"])
            self.assertEqual(len(get_macro_import_keys("EURO")) - 1, summary["not_audited"])
            self.assertEqual(0, summary["database_writes_reported"])

    def test_malformed_latest_report_is_explicit_and_non_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "euro_direct_debits_sync_broken.json"
            path.write_text("{not-json", encoding="utf-8")

            frame = load_latest_euro_sync_status(tmp)
            row = frame.set_index("import_key").loc["EURO_DIRECT_DEBITS"]

            self.assertEqual("NOT_AUDITED", row["status"])
            self.assertEqual("report_parse_error", row["blockers"])


if __name__ == "__main__":
    unittest.main()
