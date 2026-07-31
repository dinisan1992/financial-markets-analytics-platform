import unittest

import pandas as pd

from services.legacy_import_service import (
    build_duplicate_group_preview,
    build_existing_duplicate_summary,
    build_import_dry_run,
    format_dry_run_report,
    prepare_existing_market_frame,
    prepare_legacy_market_frame,
)


class LegacyImportServiceTests(unittest.TestCase):
    def test_source_preparation_normalizes_parses_and_deduplicates(self):
        source = pd.DataFrame(
            {
                "Snapped At": [
                    "Jan 01, 2024 UTC",
                    "2024-01-01",
                    "2024-01-02",
                    "invalid-date",
                    "2024-01-03",
                ],
                "Price": ["100.0", "101.5", "102", "103", "invalid"],
                "Total Volume": ["1K", "2.5M", "3B", "4", "5"],
            }
        )

        prepared = prepare_legacy_market_frame(source)

        self.assertEqual(prepared.source_rows, 5)
        self.assertEqual(prepared.invalid_rows, 2)
        self.assertEqual(prepared.duplicate_rows, 1)
        self.assertEqual(prepared.duplicate_date_groups, 1)
        self.assertEqual(len(prepared.frame), 2)
        self.assertEqual(prepared.frame.iloc[0]["price"], 101.5)
        self.assertEqual(prepared.frame.iloc[0]["total_volume"], 2_500_000)
        self.assertEqual(prepared.frame.iloc[1]["total_volume"], 3_000_000_000)

    def test_source_preparation_requires_all_base_columns(self):
        with self.assertRaisesRegex(ValueError, "total_volume"):
            prepare_legacy_market_frame(
                pd.DataFrame({"snapped_at": ["2024-01-01"], "price": [100.0]})
            )

    def test_existing_canonical_row_prefers_completeness_then_last(self):
        existing = pd.DataFrame(
            {
                "snapped_at": [
                    "2024-01-01",
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-02",
                ],
                "price": [100.0, 101.0, 200.0, 201.0],
                "total_volume": [10.0, None, 20.0, 21.0],
            }
        )

        normalized, canonical = prepare_existing_market_frame(existing)

        self.assertEqual(len(normalized), 4)
        self.assertEqual(canonical.iloc[0]["price"], 100.0)
        self.assertEqual(canonical.iloc[1]["price"], 201.0)

    def test_duplicate_preview_separates_identical_and_conflicting_groups(self):
        existing = pd.DataFrame(
            {
                "snapped_at": [
                    "2024-01-01",
                    "2024-01-01",
                    "2024-01-02",
                    "2024-01-02",
                ],
                "price": [100.0, 100.0, 200.0, 201.0],
                "total_volume": [10.0, 10.0, 20.0, 20.0],
            }
        )

        preview = build_duplicate_group_preview(existing)
        summary = build_existing_duplicate_summary("TEST", "test_table", existing)

        self.assertEqual(len(preview), 2)
        self.assertEqual(preview["rows_removable"].sum(), 2)
        self.assertEqual(summary["identical_duplicate_groups"], 1)
        self.assertEqual(summary["conflicting_duplicate_groups"], 1)
        self.assertFalse(summary["database_write_performed"])

    def test_dry_run_classifies_insert_update_and_unchanged_without_writes(self):
        source = prepare_legacy_market_frame(
            pd.DataFrame(
                {
                    "snapped_at": ["2024-01-01", "2024-01-02", "2024-01-03"],
                    "price": [100.0, 202.0, 300.0],
                    "total_volume": [10.0, 20.0, 30.0],
                }
            )
        )
        existing = pd.DataFrame(
            {
                "snapped_at": ["2024-01-01", "2024-01-01", "2024-01-02"],
                "price": [100.0, 100.0, 200.0],
                "total_volume": [10.0, 10.0, 20.0],
            }
        )

        report, actions = build_import_dry_run("TEST", "test_table", source, existing)

        self.assertEqual(report.planned_inserts, 1)
        self.assertEqual(report.planned_updates, 1)
        self.assertEqual(report.unchanged_rows, 1)
        self.assertEqual(report.existing_duplicate_rows, 1)
        self.assertEqual(report.source_dates_overlapping_existing_duplicates, 1)
        self.assertEqual(set(actions["action"]), {"insert", "update", "unchanged"})
        self.assertFalse(report.database_write_performed)
        self.assertIn("database_write_performed: False", format_dry_run_report(report))

    def test_empty_source_produces_an_empty_no_write_plan(self):
        source = prepare_legacy_market_frame(
            pd.DataFrame(columns=["snapped_at", "price", "total_volume"])
        )
        existing = pd.DataFrame(columns=["snapped_at", "price", "total_volume"])

        report, actions = build_import_dry_run("TEST", "test_table", source, existing)

        self.assertTrue(actions.empty)
        self.assertEqual(report.planned_inserts, 0)
        self.assertEqual(report.planned_updates, 0)
        self.assertEqual(report.unchanged_rows, 0)
        self.assertFalse(report.database_write_performed)


if __name__ == "__main__":
    unittest.main()
