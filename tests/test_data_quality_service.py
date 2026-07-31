import io
import unittest
import zipfile

import pandas as pd

from services.data_quality_service import (
    audit_asset_frame,
    build_audit_zip_bytes,
    build_pair_coverage_audit,
)


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


if __name__ == "__main__":
    unittest.main()
