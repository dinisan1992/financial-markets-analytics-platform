from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from macro_import_manifest import get_macro_import
from services.official_euro_source_service import (
    compare_euro_source_files,
    download_official_euro_source,
    probe_official_euro_source,
)


class FakeResponse:
    def __init__(self, body, url="https://data-api.ecb.europa.eu/test"):
        self.content = body
        self.url = url
        self.status_code = 200
        self.headers = {"Content-Type": "text/csv"}
        self.encoding = "utf-8"
        self.closed = False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        for start in range(0, len(self.content), max(1, chunk_size)):
            yield self.content[start:start + chunk_size]

    def close(self):
        self.closed = True


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def get(self, *args, **kwargs):
        self.requests.append((args, kwargs))
        return self.responses.pop(0)


def _write(path, text):
    Path(path).write_text(text, encoding="utf-8", newline="")


class OfficialEuroSourceServiceTests(unittest.TestCase):
    def test_reviewed_contracts_expose_official_dataflows(self):
        expected = {
            "EURO_CARD_PAYMENTS": "PCP",
            "EURO_BANK_LENDING_SURVEY": "BLS",
            "EURO_BALANCE_SHEET_ITEMS": "BSI",
            "EURO_GOVERNMENT_FINANCE": "GFS",
        }
        for import_key, dataflow in expected.items():
            with self.subTest(import_key=import_key):
                contract = get_macro_import(import_key)
                self.assertEqual(dataflow, contract["source_dataflow"])
                self.assertEqual(
                    "https://data-api.ecb.europa.eu/service/data/"
                    f"{dataflow}?format=csvdata",
                    contract["source_download_url"],
                )

    def test_probe_preserves_schema_and_requests_latest_series_observation(self):
        body = (
            b"KEY,TIME_PERIOD,OBS_VALUE\r\n"
            b"BLS.Q.AT.TEST,2026-Q3,-6.25\r\n"
        )
        with TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "active.csv"
            source.write_bytes(
                b"KEY,TIME_PERIOD,OBS_VALUE\nBLS.Q.AT.TEST,2025-Q4,0\n"
            )
            response = FakeResponse(body)
            session = FakeSession(response)
            probe = probe_official_euro_source(
                "EURO_BANK_LENDING_SURVEY",
                source_path=source,
                session=session,
            )

        self.assertEqual("BLS", probe.dataflow)
        self.assertEqual("2026-Q3", probe.time_period)
        self.assertEqual(-6.25, float(probe.obs_value))
        self.assertTrue(session.requests[0][0][0].endswith("/BLS/Q.AT.TEST"))
        self.assertTrue(response.closed)
        self.assertFalse(probe.database_write_performed)
        self.assertFalse(probe.active_csv_write_performed)

    def test_download_writes_only_a_validated_staging_candidate(self):
        body = (
            b"KEY,TIME_PERIOD,OBS_VALUE\n"
            b"BLS.Q.AT.TEST,2026-Q3,-6.25\n"
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "active.csv"
            staging = root / "staging"
            source.write_bytes(
                b"KEY,TIME_PERIOD,OBS_VALUE\nBLS.Q.AT.TEST,2025-Q4,0\n"
            )
            original = source.read_bytes()
            download = download_official_euro_source(
                "EURO_BANK_LENDING_SURVEY",
                staging,
                source_path=source,
                session=FakeSession(FakeResponse(body)),
                attempts=1,
                chunk_bytes=7,
                minimum_free_bytes=0,
            )

            candidate = Path(download.destination)
            self.assertEqual(body, candidate.read_bytes())
            self.assertEqual(original, source.read_bytes())

        self.assertEqual(sha256(body).hexdigest().upper(), download.sha256)
        self.assertFalse(download.database_write_performed)
        self.assertFalse(download.active_csv_write_performed)

    def test_download_rejects_changed_schema_and_removes_partial_file(self):
        body = b"KEY,TIME_PERIOD,CHANGED_VALUE\nBLS.Q.AT.TEST,2026-Q3,1\n"
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "active.csv"
            staging = root / "staging"
            source.write_bytes(
                b"KEY,TIME_PERIOD,OBS_VALUE\nBLS.Q.AT.TEST,2025-Q4,0\n"
            )
            session = FakeSession(FakeResponse(body))
            with self.assertRaisesRegex(ValueError, "schema differs"):
                download_official_euro_source(
                    "EURO_BANK_LENDING_SURVEY",
                    staging,
                    source_path=source,
                    session=session,
                    minimum_free_bytes=0,
                )

            self.assertFalse((staging / "active.csv").exists())
            self.assertFalse((staging / "active.csv.partial").exists())
            self.assertEqual(1, len(session.requests))

    def test_disk_backed_comparison_classifies_new_removed_and_changed_rows(self):
        active_csv = """\
KEY,TIME_PERIOD,OBS_VALUE
BLS.A,2024,1
BLS.A,2025,2
BLS.REMOVED,2024,9
"""
        candidate_csv = """\
KEY,TIME_PERIOD,OBS_VALUE
BLS.A,2024,1
BLS.A,2025,3
BLS.NEW,2026,4
"""
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            active = root / "active.csv"
            candidate = root / "candidate.csv"
            workspace = root / "workspace"
            workspace.mkdir()
            _write(active, active_csv)
            _write(candidate, candidate_csv)
            comparison = compare_euro_source_files(
                "EURO_BANK_LENDING_SURVEY",
                candidate,
                active_path=active,
                workspace_dir=workspace,
                chunk_size=2,
                minimum_free_bytes=0,
            )

        self.assertEqual(3, comparison.candidate_rows)
        self.assertEqual(3, comparison.active_rows)
        self.assertEqual(1, comparison.new_keys)
        self.assertEqual(1, comparison.removed_keys)
        self.assertEqual(1, comparison.changed_rows)
        self.assertTrue(comparison.safe_for_read_only_sql_plan)
        self.assertFalse(comparison.database_write_performed)
        self.assertFalse(comparison.active_csv_write_performed)

    def test_duplicate_candidate_keys_block_sql_planning(self):
        active_csv = "KEY,TIME_PERIOD,OBS_VALUE\nBLS.A,2024,1\n"
        candidate_csv = (
            "KEY,TIME_PERIOD,OBS_VALUE\n"
            "BLS.A,2024,1\n"
            "BLS.A,2024,2\n"
        )
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            active = root / "active.csv"
            candidate = root / "candidate.csv"
            workspace = root / "workspace"
            workspace.mkdir()
            _write(active, active_csv)
            _write(candidate, candidate_csv)
            comparison = compare_euro_source_files(
                "EURO_BANK_LENDING_SURVEY",
                candidate,
                active_path=active,
                workspace_dir=workspace,
                chunk_size=1,
                minimum_free_bytes=0,
            )

        self.assertEqual(1, comparison.candidate_duplicate_groups)
        self.assertEqual(1, comparison.candidate_duplicate_rows)
        self.assertEqual(1, comparison.candidate_hash_conflicts)
        self.assertFalse(comparison.safe_for_read_only_sql_plan)


if __name__ == "__main__":
    unittest.main()
