import unittest
from pathlib import Path

from asset_config import (
    ASSETS,
    get_all_script_names,
    get_existing_script_names,
    get_missing_script_names,
)
from config import BASE_DIR


class ProjectConfigTests(unittest.TestCase):
    def test_asset_script_paths_are_project_relative(self):
        for asset_key, cfg in ASSETS.items():
            script_name = cfg.get("script_name")

            self.assertIsNotNone(script_name, asset_key)
            self.assertFalse(Path(script_name).is_absolute(), asset_key)

    def test_existing_and_missing_script_helpers_partition_configured_scripts(self):
        configured = set(get_all_script_names())
        existing = set(get_existing_script_names())
        missing = {script_name for _, script_name in get_missing_script_names()}

        self.assertEqual(configured, existing | missing)
        self.assertFalse(existing & missing)

        for script_name in existing:
            self.assertTrue((BASE_DIR / script_name).exists(), script_name)

        for script_name in missing:
            self.assertFalse((BASE_DIR / script_name).exists(), script_name)

    def test_all_configured_asset_scripts_exist(self):
        self.assertEqual([], get_missing_script_names())


if __name__ == "__main__":
    unittest.main()
