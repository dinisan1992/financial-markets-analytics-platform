from unittest.mock import patch
import unittest

from project_scripts.diagnostics.swap_euro_direct_debits import (
    build_parser,
    main,
)
from services.euro_direct_debits_swap_service import (
    SWAP_DIRECT_DEBITS_CONFIRMATION,
)


class SwapDirectDebitsCommandTests(unittest.TestCase):
    def test_command_has_no_build_or_cleanup_stage(self):
        destinations = {action.dest for action in build_parser()._actions}
        self.assertNotIn("stage", destinations)
        self.assertNotIn("build", destinations)
        self.assertNotIn("cleanup", destinations)

    @patch(
        "project_scripts.diagnostics.swap_euro_direct_debits.create_engine"
    )
    def test_wrong_confirmation_fails_before_engine_creation(self, create_engine):
        with self.assertRaisesRegex(ValueError, "must exactly match"):
            main(
                [
                    "--backup-file",
                    "backup.sql",
                    "--confirm",
                    "WRONG",
                    "--suffix",
                    "20260811_163215",
                ]
            )
        create_engine.assert_not_called()
        self.assertEqual(
            "SWAP_EURO_DIRECT_DEBITS_V070_ACTIVE",
            SWAP_DIRECT_DEBITS_CONFIRMATION,
        )


if __name__ == "__main__":
    unittest.main()
