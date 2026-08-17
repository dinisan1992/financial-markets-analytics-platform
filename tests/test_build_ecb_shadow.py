from contextlib import redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest

from project_scripts.diagnostics.build_ecb_shadow import (
    _verified_pin_file,
    build_parser,
)


class BuildEcbShadowCliTests(unittest.TestCase):
    def test_changed_pin_manifest_stops_before_loading_plans(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shadow_plans.json"
            path.write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                _verified_pin_file(
                    path,
                    {
                        "pin_manifest_file": path.name,
                        "pin_manifest_sha256": "A" * 64,
                    },
                )

    def test_cli_has_no_swap_option(self):
        parser = build_parser()
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(
                    [
                        "EURO_BALANCE_SHEET_ITEMS",
                        "--readiness-report",
                        "readiness.json",
                        "--readiness-sha256",
                        "A",
                        "--staging-dir",
                        "staging",
                        "--backup-dir",
                        "backup",
                        "--audit-dir",
                        "audit",
                        "--workspace-dir",
                        "workspace",
                        "--pin-file",
                        "pin.json",
                        "--confirm",
                        "BUILD_EURO_BALANCE_SHEET_ITEMS_V079_SHADOW",
                        "--swap",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
