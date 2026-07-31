import io
from pathlib import Path
import tempfile
import unittest
import zipfile

import pandas as pd

from services.data_quality_service import (
    audit_asset_frame,
    build_audit_zip_bytes,
    build_freshness_report,
    build_pair_coverage_audit,
    build_remediation_report,
)
from project_scripts.analysis.run_data_audit import archive_existing_audit


class DataQualityServiceTests(unittest.TestCase):
    def test_audit_detects_duplicates_invalid_prices_and_native_ohlc(self):
        frame = pd.DataFrame(
            {
                "snapped_at": pd.to_datetime(
                    ["2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"]
                ),
                "price": [100.0, 101.0, 101.0, -1.0],
                "open": [99.0, 100.0, 100.0, 1.0],
                "high": [101.0, 102.0, 102.0, 2.0],
                "low": [98.0, 99.0, 99.0, 0.5],
                "close": [100.0, 101.0, 101.0, 1.0],
                "volume": [10.0, 11.0, 12.0, 13.0],
            }
        )
        config = {
            "table_name": "test_prices",
            "asset_class": "crypto",
            "calendar_type": "continuous",
            "periods_per_year": 365,
            "volume_expected": True,
        }

        result = audit_asset_frame("TEST", config, frame, as_of="2024-01-04")

        self.assertEqual(result["duplicate_dates"], 1)
        self.assertEqual(result["invalid_prices"], 1)
        self.assertEqual(result["native_ohlc_rows"], 4)
        self.assertEqual(result["status"], "WARNING")

    def test_zip_contains_summary_and_each_table(self):
        tables = {
            "asset_audit": pd.DataFrame([{"asset": "TEST", "status": "OK"}]),
            "correlation_coverage": pd.DataFrame(),
            "event_coverage": pd.DataFrame(),
        }
        payload = build_audit_zip_bytes(tables)

        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(
                set(archive.namelist()),
                {
                    "audit_summary.json",
                    "asset_audit.csv",
                    "correlation_coverage.csv",
                    "event_coverage.csv",
                },
            )

    def test_negative_yield_is_not_an_invalid_price(self):
        frame = pd.DataFrame(
            {
                "snapped_at": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                "price": [-0.1, 0.0],
            }
        )
        result = audit_asset_frame(
            "YIELD",
            {
                "table_name": "yield_table",
                "calendar_type": "trading_days",
                "positive_values_expected": False,
            },
            frame,
            as_of="2024-01-02",
        )

        self.assertEqual(result["invalid_prices"], 0)

    def test_pair_coverage_accepts_equivalent_date_types(self):
        frames = {
            "A": pd.DataFrame(
                {"snapped_at": ["2024-01-01", "2024-01-02"], "price": [100.0, 101.0]}
            ),
            "B": pd.DataFrame(
                {
                    "snapped_at": pd.to_datetime(["2024-01-01", "2024-01-02"]),
                    "price": [200.0, 202.0],
                }
            ),
        }

        result = build_pair_coverage_audit(frames)

        self.assertEqual(result.iloc[0]["same_date_prices"], 2)
        self.assertEqual(result.iloc[0]["return_observations"], 1)

    def test_negative_wti_price_requires_review_instead_of_automatic_correction(self):
        frame = pd.DataFrame(
            {
                "snapped_at": pd.to_datetime(["2020-04-20", "2020-04-21"]),
                "price": [-37.63, 10.01],
            }
        )
        result = audit_asset_frame(
            "WTI_OIL",
            {
                "table_name": "wti_oil_analysis",
                "calendar_type": "trading_days",
                "positive_values_expected": True,
                "negative_values_possible": True,
            },
            frame,
            as_of="2020-04-21",
        )

        self.assertEqual(result["invalid_prices"], 0)
        self.assertEqual(result["prices_requiring_review"], 1)
        self.assertIn("non_positive_price_review", result["warnings"])

    def test_duplicate_diagnostics_report_groups_and_range(self):
        frame = pd.DataFrame(
            {
                "snapped_at": pd.to_datetime(
                    ["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02"]
                ),
                "price": [100.0, 100.0, 101.0, 101.0],
            }
        )
        result = audit_asset_frame(
            "TEST",
            {"table_name": "test", "calendar_type": "trading_days"},
            frame,
            as_of="2024-01-02",
        )

        self.assertEqual(result["duplicate_dates"], 2)
        self.assertEqual(result["duplicate_date_groups"], 2)
        self.assertEqual(result["max_rows_per_date"], 2)
        self.assertEqual(str(result["first_duplicate_date"]), "2024-01-01")
        self.assertEqual(str(result["last_duplicate_date"]), "2024-01-02")

    def test_freshness_and_remediation_reports_are_operational(self):
        audit = pd.DataFrame(
            [
                {
                    "asset": "TEST",
                    "table": "test_table",
                    "last_date": pd.Timestamp("2024-01-01").date(),
                    "stale_days": 30,
                    "stale_limit_days": 10,
                    "days_overdue": 20,
                    "freshness_status": "STALE",
                    "source_type": "configured_csv_pipeline",
                    "source_reference": "test.csv",
                    "updater_script": "project_scripts/assets/test.py",
                    "warnings": "duplicate_dates, stale_data",
                    "duplicate_dates": 4,
                    "duplicate_date_groups": 2,
                }
            ]
        )

        freshness = build_freshness_report(audit)
        remediation = build_remediation_report(audit)

        self.assertEqual(freshness.iloc[0]["days_overdue"], 20)
        self.assertEqual(set(remediation["issue"]), {"duplicate_dates", "stale_data"})
        self.assertEqual(remediation.iloc[0]["priority"], "P1")

    def test_pair_correlation_uses_each_assets_native_return_intervals(self):
        frames = {
            "A": pd.DataFrame(
                {
                    "snapped_at": pd.to_datetime(
                        ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
                    ),
                    "price": [100.0, 110.0, 121.0, 133.1],
                }
            ),
            "B": pd.DataFrame(
                {
                    "snapped_at": pd.to_datetime(
                        ["2024-01-01", "2024-01-03", "2024-01-04"]
                    ),
                    "price": [200.0, 220.0, 242.0],
                }
            ),
        }

        result = build_pair_coverage_audit(frames).iloc[0]

        self.assertEqual(result["return_observations"], 2)
        self.assertEqual(str(result["common_start_date"]), "2024-01-03")
        self.assertEqual(result["correlation_confidence"], "INSUFFICIENT")

    def test_existing_audit_zip_is_archived_before_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            payload = b"baseline-audit"
            (output_dir / "audit_outputs.zip").write_bytes(payload)

            archived_path = archive_existing_audit(output_dir)

            self.assertIsNotNone(archived_path)
            self.assertEqual(archived_path.read_bytes(), payload)
            self.assertEqual(archived_path.parent.name, "baselines")


if __name__ == "__main__":
    unittest.main()
