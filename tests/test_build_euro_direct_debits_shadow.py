from unittest.mock import patch
import unittest

from project_scripts.diagnostics.build_euro_direct_debits_shadow import (
    build_parser,
    main,
)
from services.euro_direct_debits_shadow_service import (
    BUILD_DIRECT_DEBITS_CONFIRMATION,
)


class BuildDirectDebitsShadowCommandTests(unittest.TestCase):
    def test_command_exposes_no_swap_stage(self):
        destinations = {action.dest for action in build_parser()._actions}
        self.assertNotIn("stage", destinations)
        self.assertNotIn("swap", destinations)

    @patch(
        "project_scripts.diagnostics.build_euro_direct_debits_shadow."
        "create_engine"
    )
    def test_wrong_confirmation_fails_before_engine_creation(self, create_engine):
        with self.assertRaisesRegex(ValueError, "must exactly match"):
            main(
                [
                    "--backup-file",
                    "backup.sql",
                    "--confirm",
                    "WRONG",
                ]
            )
        create_engine.assert_not_called()
        self.assertEqual(
            "BUILD_EURO_DIRECT_DEBITS_V069_SHADOW",
            BUILD_DIRECT_DEBITS_CONFIRMATION,
        )


if __name__ == "__main__":
    unittest.main()
