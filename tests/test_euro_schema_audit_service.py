from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from services.euro_schema_audit_service import (
    EuroSchemaAudit,
    EuroSeriesAudit,
    classify_period,
    classify_euro_remediation,
    map_source_columns,
    period_type_is_safe,
    write_euro_audit_report,
)


class EuroSchemaAuditServiceTests(unittest.TestCase):
    def test_source_aliases_preserve_atm_target_mapping(self):
        mapped = map_source_columns(
            ["KEY", "TRMNL_LCTN", "TYP_TRNSCTN", "TIME_PERIOD"],
            aliases={
                "key": "key_code",
                "trmnl_lctn": "terminal_location",
                "typ_trnsctn": "transaction_type",
            },
        )
        self.assertEqual(
            ("key_code", "terminal_location", "transaction_type", "time_period"),
            mapped,
        )

    def test_period_patterns_distinguish_semesters_from_years(self):
        self.assertEqual("year", classify_period("2024"))
        self.assertEqual("semester", classify_period("2024-S2"))
        self.assertEqual("quarter", classify_period("2024-Q3"))
        self.assertEqual("month", classify_period("2024-09"))
        self.assertEqual("date", classify_period("2024-09-30"))

    def test_period_type_guard_rejects_lossy_sql_types(self):
        self.assertFalse(period_type_is_safe("INTEGER", ("semester",)))
        self.assertFalse(period_type_is_safe("YEAR", ("semester",)))
        self.assertFalse(period_type_is_safe("DATE", ("month",)))
        self.assertTrue(period_type_is_safe("VARCHAR(20)", ("semester",)))
        self.assertTrue(period_type_is_safe("DATE", ("date",)))

    def test_incomplete_target_history_requires_rebuild(self):
        self.assertEqual(
            "rebuild_required",
            classify_euro_remediation(
                ("target_history_incomplete", "unique_business_key_missing")
            ),
        )

    def test_report_is_read_only_and_serializes_structured_results(self):
        table_audit = EuroSchemaAudit(
            import_key="EURO_TEST",
            table_name="euro_test",
            source_path="source.csv",
            source_bytes=100,
            source_columns=("key_code", "time_period", "obs_value"),
            target_columns=("key_code", "time_period", "obs_value"),
            source_only_columns=(),
            target_only_columns=(),
            target_rows=2,
            audited_source_rows=2,
            source_rows_missing_from_target=0,
            sample_rows=2,
            invalid_sample_rows=0,
            period_patterns=("month",),
            target_period_type="VARCHAR(20)",
            period_type_safe=True,
            primary_key=("key_code", "time_period"),
            unique_business_key=True,
            unique_key_code_only=False,
            null_business_key_rows=0,
            duplicate_business_key_groups=0,
            configured_series=1,
            remediation_class="write_contract_ready",
            blockers=(),
        )
        series_audit = EuroSeriesAudit(
            series_key="EURO_TEST_SERIES",
            table_name="euro_test",
            key_code="TEST.M.U2",
            enabled=True,
            observations=2,
            first_period="2024-01",
            last_period="2024-02",
            non_null_values=2,
            status="available",
        )
        with TemporaryDirectory() as temp_dir:
            outputs = write_euro_audit_report(
                temp_dir,
                [table_audit],
                [series_audit],
            )
            payload = json.loads(Path(outputs["json"]).read_text(encoding="utf-8"))
            self.assertFalse(payload["database_write_performed"])
            self.assertEqual("write_contract_ready", payload["tables"][0]["remediation_class"])
            self.assertEqual(64, len(outputs["json_sha256"]))


if __name__ == "__main__":
    unittest.main()
