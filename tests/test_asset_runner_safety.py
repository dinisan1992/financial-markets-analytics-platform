import unittest

from project_scripts.assets.run_all_assets import build_validation_command
from project_scripts.assets.new_market_asset import process_asset


class AssetRunnerSafetyTests(unittest.TestCase):
    def test_global_runner_never_adds_sql_write_flag(self):
        command = build_validation_command("BTC")

        self.assertIn("--source", command)
        self.assertIn("sql", command)
        self.assertNotIn("--update-sql", command)

    def test_legacy_new_market_runner_rejects_direct_sql_updates(self):
        with self.assertRaisesRegex(ValueError, "sync_market_data.py"):
            process_asset("NASDAQ100", update_sql=True)


if __name__ == "__main__":
    unittest.main()
