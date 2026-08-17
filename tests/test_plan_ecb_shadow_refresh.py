from pathlib import Path
from contextlib import redirect_stderr
import io
import unittest

from project_scripts.diagnostics.plan_ecb_shadow_refresh import parse_args
from services.ecb_shadow_readiness_service import ECB_IMPORT_KEYS


class EcbShadowReadinessCliTests(unittest.TestCase):
    def test_default_scope_contains_all_three_ecb_imports(self):
        args = parse_args(
            [
                "--staging-dir",
                "staging",
                "--backup-dir",
                "backups",
                "--audit-dir",
                "audits",
                "--workspace-dir",
                "workspace",
                "--pin-file",
                "pins.json",
            ]
        )
        self.assertEqual(list(ECB_IMPORT_KEYS), args.import_keys)
        self.assertIsInstance(args.staging_dir, Path)

    def test_cli_exposes_no_apply_or_swap_option(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parse_args(
                    [
                        "--staging-dir",
                        "staging",
                        "--backup-dir",
                        "backups",
                        "--audit-dir",
                        "audits",
                        "--workspace-dir",
                        "workspace",
                        "--pin-file",
                        "pins.json",
                        "--apply",
                    ]
                )


if __name__ == "__main__":
    unittest.main()
