from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
import unittest

import pandas as pd

from project_scripts.analysis.euro_series_validator import (
    GROUP_REPORT,
    PAIR_REPORT,
    SERIES_REPORT,
    main,
    validate_series,
)


class EuroSeriesValidatorTests(unittest.TestCase):
    def test_disabled_series_is_skipped_without_database_read(self):
        with patch(
            "project_scripts.analysis.euro_series_validator.load_euro_series"
        ) as loader:
            result = validate_series(
                "EURO_DISABLED",
                {"enabled": False},
                Mock(),
            )

        self.assertEqual("SKIPPED", result["status"])
        loader.assert_not_called()

    def test_main_writes_reports_to_selected_directory(self):
        series = pd.DataFrame([
            {"series_key": "EURO_TEST", "status": "OK"},
        ])
        groups = pd.DataFrame([
            {"group_name": "test", "status": "OK"},
        ])
        pairs = pd.DataFrame([
            {"pair_key": "test", "status": "OK"},
        ])
        engine = Mock()
        with TemporaryDirectory() as temp_dir, patch(
            "project_scripts.analysis.euro_series_validator.get_engine",
            return_value=engine,
        ), patch(
            "project_scripts.analysis.euro_series_validator.validate_all_series",
            return_value=series,
        ), patch(
            "project_scripts.analysis.euro_series_validator.validate_groups",
            return_value=groups,
        ), patch(
            "project_scripts.analysis.euro_series_validator.validate_pairs",
            return_value=pairs,
        ), redirect_stdout(StringIO()):
            result = main(["--output-dir", temp_dir, "--fail-on-error"])
            paths = {
                Path(temp_dir) / SERIES_REPORT,
                Path(temp_dir) / GROUP_REPORT,
                Path(temp_dir) / PAIR_REPORT,
            }
            self.assertTrue(all(path.is_file() for path in paths))

        self.assertEqual(0, result)
        engine.dispose.assert_called_once_with()

    def test_fail_on_error_returns_nonzero(self):
        series = pd.DataFrame([
            {"series_key": "EURO_TEST", "status": "ERROR"},
        ])
        empty_ok = pd.DataFrame([{"status": "OK"}])
        with TemporaryDirectory() as temp_dir, patch(
            "project_scripts.analysis.euro_series_validator.get_engine",
            return_value=Mock(),
        ), patch(
            "project_scripts.analysis.euro_series_validator.validate_all_series",
            return_value=series,
        ), patch(
            "project_scripts.analysis.euro_series_validator.validate_groups",
            return_value=empty_ok,
        ), patch(
            "project_scripts.analysis.euro_series_validator.validate_pairs",
            return_value=empty_ok,
        ), redirect_stdout(StringIO()):
            result = main(["--output-dir", temp_dir, "--fail-on-error"])

        self.assertEqual(2, result)


if __name__ == "__main__":
    unittest.main()
