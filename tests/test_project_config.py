import unittest
from pathlib import Path

from asset_config import (
    ASSETS,
    get_all_script_names,
    get_existing_script_names,
    get_missing_script_names,
)
from config import BASE_DIR, PROJECT_VERSION
from market_source_manifest import MARKET_SOURCE_MANIFEST


class ProjectConfigTests(unittest.TestCase):
    def test_version_file_matches_runtime_version(self):
        self.assertEqual(
            PROJECT_VERSION,
            (BASE_DIR / "VERSION").read_text(encoding="ascii").strip(),
        )

    def test_all_assets_have_financial_metadata(self):
        required = {
            "asset_class",
            "periods_per_year",
            "calendar_type",
            "volume_expected",
            "ohlc_expected",
            "positive_values_expected",
            "negative_values_possible",
            "source_type",
            "source_provider",
            "source_identifier",
            "source_reference",
            "source_frequency",
            "source_identity_status",
            "source_native_ohlc_expected",
        }
        for asset_key, config in ASSETS.items():
            self.assertTrue(required.issubset(config), asset_key)
            self.assertGreater(config["periods_per_year"], 0, asset_key)

    def test_source_frequency_overrides_are_explicit(self):
        for asset_key in ["GERMANY10Y", "UK10Y", "JAPAN10Y"]:
            self.assertEqual(ASSETS[asset_key]["calendar_type"], "monthly")
            self.assertEqual(ASSETS[asset_key]["periods_per_year"], 12)

        self.assertEqual(ASSETS["FINANCIAL_CONDITIONS"]["calendar_type"], "weekly")
        self.assertEqual(ASSETS["FINANCIAL_CONDITIONS"]["periods_per_year"], 52)

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

    def test_market_source_manifest_matches_configured_assets(self):
        self.assertEqual(set(ASSETS), set(MARKET_SOURCE_MANIFEST))
        for asset_key, source in MARKET_SOURCE_MANIFEST.items():
            self.assertTrue(source["source_provider"], asset_key)
            self.assertTrue(source["source_identifier"], asset_key)
            self.assertTrue(source["source_reference"].startswith("https://"), asset_key)

    def test_us_treasury_series_identities_are_distinct(self):
        self.assertEqual("^IRX", ASSETS["US3M"]["source_identifier"])
        self.assertIn("RIFLGFCY02_N.B", ASSETS["US2Y"]["source_identifier"])
        self.assertNotEqual(
            ASSETS["US3M"]["table_name"],
            ASSETS["US2Y"]["table_name"],
        )


if __name__ == "__main__":
    unittest.main()
