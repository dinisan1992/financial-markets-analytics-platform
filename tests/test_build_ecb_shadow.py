from contextlib import redirect_stderr
import io
import unittest

from project_scripts.diagnostics.build_ecb_shadow import build_parser


class BuildEcbShadowCliTests(unittest.TestCase):
    def test_cli_has_no_swap_option(self):
        parser = build_parser()
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(
                    [
                        "EURO_BANK_LENDING_SURVEY",
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
                        "BUILD_EURO_BANK_LENDING_SURVEY_V079_SHADOW",
                        "--swap",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
