from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch
import unittest

from services.euro_large_rebuild_service import (
    REBUILD_VERSION,
    TARGET_IMPORT_KEYS,
    build_confirmation,
    build_large_shadow,
    estimate_large_rebuild_capacity,
    swap_confirmation,
    swap_large_shadow,
)
from services.euro_rebuild_service import (
    retained_table_name,
    shadow_table_name,
)


class EuroLargeRebuildServiceTests(unittest.TestCase):
    def test_confirmations_are_table_specific(self):
        import_key = "EURO_CONSUMER_PRICES"

        self.assertEqual(
            "BUILD_EURO_CONSUMER_PRICES_V062_SHADOW",
            build_confirmation(import_key),
        )
        self.assertEqual(
            "SWAP_EURO_CONSUMER_PRICES_V062_SHADOW",
            swap_confirmation(import_key),
        )

    def test_v062_names_are_isolated_from_earlier_rebuilds(self):
        table = "euro_indices_consumer_prices"
        suffix = "20260811_120000"

        self.assertIn(
            "shadow_v062",
            shadow_table_name(table, suffix, REBUILD_VERSION),
        )
        self.assertIn(
            "pre_v062",
            retained_table_name(table, suffix, REBUILD_VERSION),
        )

    def test_wrong_build_confirmation_stops_before_core_service(self):
        with patch(
            "services.euro_large_rebuild_service.build_and_validate_shadows"
        ) as core:
            with self.assertRaisesRegex(ValueError, "BUILD_EURO_CONSUMER"):
                build_large_shadow(
                    engine=Mock(),
                    import_key="EURO_CONSUMER_PRICES",
                    backup_file="missing.sql",
                    confirmation="WRONG",
                    suffix="20260811_120000",
                )
        core.assert_not_called()

    def test_build_calls_core_for_one_table_with_bounded_validation(self):
        import_key = "EURO_NATIONAL_ACCOUNTS"
        sentinel = {"status": "ok"}
        with patch(
            "services.euro_large_rebuild_service.build_and_validate_shadows",
            return_value=sentinel,
        ) as core:
            result = build_large_shadow(
                engine=Mock(),
                import_key=import_key,
                backup_file="backup.sql",
                confirmation=build_confirmation(import_key),
                suffix="20260811_120000",
            )

        self.assertIs(sentinel, result)
        self.assertEqual((import_key,), core.call_args.kwargs["import_keys"])
        self.assertTrue(core.call_args.kwargs["memory_bounded"])
        self.assertEqual(REBUILD_VERSION, core.call_args.kwargs["version"])

    def test_swap_calls_core_for_one_table_with_bounded_validation(self):
        import_key = "EURO_MFI_INTEREST_RATES"
        sentinel = {"status": "ok"}
        with patch(
            "services.euro_large_rebuild_service.swap_validated_shadows",
            return_value=sentinel,
        ) as core:
            result = swap_large_shadow(
                engine=Mock(),
                import_key=import_key,
                backup_file="backup.sql",
                confirmation=swap_confirmation(import_key),
                suffix="20260811_120000",
            )

        self.assertIs(sentinel, result)
        self.assertEqual((import_key,), core.call_args.kwargs["import_keys"])
        self.assertTrue(core.call_args.kwargs["memory_bounded"])

    def test_wrong_swap_confirmation_stops_before_core_service(self):
        with patch(
            "services.euro_large_rebuild_service.swap_validated_shadows"
        ) as core:
            with self.assertRaisesRegex(ValueError, "SWAP_EURO_MFI"):
                swap_large_shadow(
                    engine=Mock(),
                    import_key="EURO_MFI_INTEREST_RATES",
                    backup_file="missing.sql",
                    confirmation="WRONG",
                    suffix="20260811_120000",
                )
        core.assert_not_called()

    def test_unsupported_table_is_rejected_before_core_service(self):
        with patch(
            "services.euro_large_rebuild_service.build_and_validate_shadows"
        ) as core:
            with self.assertRaisesRegex(ValueError, "Unsupported"):
                build_large_shadow(
                    engine=Mock(),
                    import_key="EURO_CARD_PAYMENTS",
                    backup_file="backup.sql",
                    confirmation="anything",
                    suffix="20260811_120000",
                )
        core.assert_not_called()
        self.assertEqual(3, len(TARGET_IMPORT_KEYS))

    def test_capacity_estimate_is_read_only_and_includes_reserve(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source.csv"
            source.write_text("header\nvalue\n", encoding="utf-8")
            mysql_dir = root / "mysql"
            workspace = root / "workspace"
            mysql_dir.mkdir()
            workspace.mkdir()
            engine = MagicMock()
            connection = engine.connect.return_value.__enter__.return_value
            connection.execute.return_value.mappings.return_value.one.return_value = {
                "mysql_data_dir": str(mysql_dir),
                "target_rows": 100,
                "active_table_bytes": 1_000,
            }
            contract = {
                "table_name": "euro_indices_consumer_prices",
                "csv_path": source,
            }
            baselines = {
                "EURO_CONSUMER_PRICES": {
                    "source_rows": 1_000,
                    "comparison_store_bytes": 200,
                }
            }
            with patch(
                "services.euro_large_rebuild_service.get_macro_import",
                return_value=contract,
            ), patch(
                "services.euro_large_rebuild_service.V061_AUDIT_BASELINES",
                baselines,
            ), patch(
                "services.euro_large_rebuild_service.shutil.disk_usage",
                return_value=Mock(free=20_000),
            ):
                result = estimate_large_rebuild_capacity(
                    engine,
                    "EURO_CONSUMER_PRICES",
                    workspace_dir=workspace,
                    operating_reserve_bytes=100,
                )

        self.assertEqual(10_000, result["estimated_shadow_bytes"])
        self.assertEqual(10_300, result["combined_required_bytes"])
        self.assertTrue(result["capacity_pass"])
        self.assertFalse(result["database_write_performed"])
        self.assertFalse(result["backup_space_included"])


if __name__ == "__main__":
    unittest.main()
