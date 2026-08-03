import unittest
from pathlib import Path
import tempfile

import pandas as pd

from services.market_data_sync_service import (
    build_market_sync_plan,
    format_market_sync_plan,
    parse_market_number,
    prepare_market_frame,
    read_market_csv,
    validate_identifier,
)


class MarketDataSyncServiceTests(unittest.TestCase):
    def test_prepare_market_frame_handles_mixed_legacy_values(self):
        source = pd.DataFrame(
            {
                "Snapped At": ["Oct 7, 2025", "2025-10-07 UTC", "bad"],
                "Price": ["6,746.14", "6,750.00", "100"],
                "Total Volume": ["1.2B", "2M", "3"],
            }
        )

        prepared = prepare_market_frame(source)

        self.assertEqual(prepared.source_rows, 3)
        self.assertEqual(prepared.invalid_rows, 1)
        self.assertEqual(prepared.duplicate_rows, 1)
        self.assertEqual(len(prepared.frame), 1)
        self.assertEqual(prepared.frame.iloc[0]["price"], 6750.0)
        self.assertEqual(prepared.frame.iloc[0]["total_volume"], 2_000_000.0)

    def test_prepare_market_frame_preserves_native_ohlc(self):
        source = pd.DataFrame(
            {
                "snapped_at": ["2024-01-01"],
                "price": [100],
                "open": [99],
                "high": [101],
                "low": [98],
                "close": [100],
            }
        )

        prepared = prepare_market_frame(source, csv_path="prices.csv")

        self.assertEqual(prepared.frame.iloc[0]["open"], 99.0)
        self.assertEqual(prepared.frame.iloc[0]["source_file"], "prices.csv")

    def test_sync_plan_is_idempotent_and_reports_existing_duplicates(self):
        source = prepare_market_frame(
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

        plan, actions = build_market_sync_plan(
            "TEST",
            "test_table",
            source,
            existing,
            unique_date_key_available=False,
        )

        self.assertEqual(plan.planned_inserts, 1)
        self.assertEqual(plan.planned_updates, 1)
        self.assertEqual(plan.unchanged_rows, 1)
        self.assertEqual(plan.existing_duplicate_rows, 1)
        self.assertFalse(plan.unique_date_key_available)
        self.assertFalse(plan.database_write_performed)
        self.assertEqual(set(actions["action"]), {"insert", "update", "unchanged"})
        self.assertIn("database_write_performed: False", format_market_sync_plan(plan))

    def test_source_null_does_not_schedule_destructive_update(self):
        source = prepare_market_frame(
            pd.DataFrame(
                {
                    "snapped_at": ["2024-01-01"],
                    "price": [100.0],
                    "total_volume": [None],
                }
            )
        )
        existing = pd.DataFrame(
            {
                "snapped_at": ["2024-01-01"],
                "price": [100.0],
                "total_volume": [50.0],
            }
        )

        plan, _ = build_market_sync_plan(
            "TEST", "test_table", source, existing, True
        )

        self.assertEqual(plan.planned_updates, 0)
        self.assertEqual(plan.unchanged_rows, 1)

    def test_numeric_parser_and_identifier_guard(self):
        self.assertEqual(parse_market_number("(1,234.5)"), -1234.5)
        self.assertEqual(parse_market_number("3.887,70"), 3887.70)
        self.assertEqual(parse_market_number("290,47K"), 290_470.0)
        with self.assertRaisesRegex(ValueError, "Unsafe SQL identifier"):
            validate_identifier("prices; DROP TABLE prices")

    def test_day_first_dates_are_inferred_from_unambiguous_rows(self):
        prepared = prepare_market_frame(
            pd.DataFrame(
                {
                    "snapped_at": ["03/01/1975", "13/01/1975"],
                    "price": [173, 181],
                }
            )
        )

        self.assertEqual(
            prepared.frame["snapped_at"].tolist(),
            [pd.Timestamp("1975-01-03"), pd.Timestamp("1975-01-13")],
        )

    def test_malformed_single_field_csv_rows_are_repaired(self):
        content = (
            "snapped_at,price,open,high,low,volume,change %\n"
            '"04/15/2013,""290.43"",""292.15"",""292.64"",'
            '""288.80"",""233.97M"",""-0.67%"""\n'
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "prices.csv"
            csv_path.write_text(content, encoding="utf-8")
            prepared = read_market_csv(csv_path)

        self.assertEqual(len(prepared.frame), 1)
        self.assertEqual(prepared.frame.iloc[0]["price"], 290.43)
        self.assertEqual(prepared.frame.iloc[0]["total_volume"], 233_970_000.0)
        self.assertEqual(
            prepared.frame.iloc[0]["snapped_at"],
            pd.Timestamp("2013-04-15"),
        )


if __name__ == "__main__":
    unittest.main()
