from contextlib import redirect_stderr
import io
from unittest.mock import patch
import unittest

from project_scripts.diagnostics.preflight_ecb_bsi_swap import (
    build_parser,
    main,
)


class PreflightEcbBsiSwapCommandTests(unittest.TestCase):
    def test_command_exposes_no_confirmation_or_swap_mode(self):
        destinations = {action.dest for action in build_parser()._actions}
        self.assertNotIn("confirm", destinations)
        self.assertNotIn("swap", destinations)
        self.assertNotIn("build", destinations)
        self.assertNotIn("cleanup", destinations)

    @patch(
        "project_scripts.diagnostics.preflight_ecb_bsi_swap.create_engine"
    )
    def test_invalid_chunk_size_fails_before_engine_creation(self, create_engine):
        with redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(SystemExit, "must be positive"):
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
                        "--chunk-size",
                        "0",
                    ]
                )
        create_engine.assert_not_called()


if __name__ == "__main__":
    unittest.main()
