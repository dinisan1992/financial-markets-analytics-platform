from contextlib import redirect_stderr
import io
from unittest.mock import patch
import unittest

from project_scripts.diagnostics.verify_ecb_shadow_build import (
    build_parser,
    main,
)


class VerifyEcbShadowBuildCommandTests(unittest.TestCase):
    def test_command_exposes_no_write_or_promotion_mode(self):
        destinations = {action.dest for action in build_parser()._actions}
        for forbidden in ("confirm", "swap", "build", "cleanup", "apply"):
            self.assertNotIn(forbidden, destinations)

    @patch(
        "project_scripts.diagnostics.verify_ecb_shadow_build.create_engine"
    )
    def test_invalid_chunk_size_fails_before_engine_creation(self, create_engine):
        with redirect_stderr(io.StringIO()):
            with self.assertRaisesRegex(SystemExit, "must be positive"):
                main(
                    [
                        "EURO_BALANCE_SHEET_ITEMS",
                        "--readiness-report",
                        "readiness.json",
                        "--readiness-sha256",
                        "A",
                        "--build-report",
                        "build.json",
                        "--build-sha256",
                        "B",
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
