from contextlib import redirect_stderr
import io
from unittest.mock import patch
import unittest

from project_scripts.diagnostics.swap_ecb_pcp import build_parser, main


class SwapEcbPcpCommandTests(unittest.TestCase):
    def test_command_exposes_no_build_or_cleanup_stage(self):
        destinations = {action.dest for action in build_parser()._actions}
        self.assertNotIn("stage", destinations)
        self.assertNotIn("build", destinations)
        self.assertNotIn("cleanup", destinations)

    @patch("project_scripts.diagnostics.swap_ecb_pcp.create_engine")
    def test_wrong_confirmation_fails_before_engine_creation(self, create_engine):
        with redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(ValueError, "must exactly match"):
                main(
                    [
                        "--readiness-report",
                        "readiness.json",
                        "--readiness-sha256",
                        "A",
                        "--build-report",
                        "build.json",
                        "--build-sha256",
                        "B",
                        "--verification-report",
                        "verification.json",
                        "--verification-sha256",
                        "C",
                        "--staging-dir",
                        "staging",
                        "--backup-dir",
                        "backup",
                        "--workspace-dir",
                        "workspace",
                        "--confirm",
                        "WRONG",
                    ]
                )
        create_engine.assert_not_called()


if __name__ == "__main__":
    unittest.main()
