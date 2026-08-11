from unittest.mock import patch
import unittest

from project_scripts.diagnostics.audit_euro_streaming_completeness import (
    parse_args,
)
from services.euro_streaming_validation_service import TARGET_IMPORT_KEYS


class EuroStreamingAuditCliTests(unittest.TestCase):
    def test_all_target_imports_are_selected_by_default(self):
        with patch("sys.argv", ["audit_euro_streaming_completeness.py"]):
            args = parse_args()

        self.assertEqual(list(TARGET_IMPORT_KEYS), args.import_keys)

    def test_one_explicit_import_can_be_selected(self):
        with patch(
            "sys.argv",
            ["audit_euro_streaming_completeness.py", TARGET_IMPORT_KEYS[1]],
        ):
            args = parse_args()

        self.assertEqual([TARGET_IMPORT_KEYS[1]], args.import_keys)


if __name__ == "__main__":
    unittest.main()
