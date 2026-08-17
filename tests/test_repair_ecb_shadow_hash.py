from contextlib import redirect_stderr
import io
import unittest

from project_scripts.diagnostics.repair_ecb_shadow_hash import build_parser


class RepairEcbShadowHashCliTests(unittest.TestCase):
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
                        "--source-file",
                        "source.csv",
                        "--workspace-dir",
                        "workspace",
                        "--key-code",
                        "KEY",
                        "--time-period",
                        "2020-Q2",
                        "--confirm",
                        "REPAIR_EURO_BANK_LENDING_SURVEY_V079_SHADOW_HASHES",
                        "--swap",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
