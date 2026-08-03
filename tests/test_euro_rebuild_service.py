from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock
import unittest

from services.euro_rebuild_service import (
    BUILD_CONFIRMATION,
    TARGET_IMPORT_KEYS,
    build_and_validate_shadows,
    build_rollback_statement,
    build_swap_statement,
    canonical_row_hash,
    normalize_row,
    record_batches,
    shadow_table_name,
    validate_scoped_backup,
    versioned_table_name,
)


class EuroRebuildServiceTests(unittest.TestCase):
    def test_versioned_table_names_remain_identifier_safe(self):
        name = versioned_table_name(
            "euro_card_payments_by_merchant_category",
            "shadow_v055",
            "20260803_210000",
        )
        self.assertLessEqual(len(name), 64)
        self.assertNotIn("-", name)
        self.assertEqual(name, shadow_table_name(
            "euro_card_payments_by_merchant_category",
            "20260803_210000",
        ))

    def test_scoped_backup_requires_structure_and_data_for_every_table(self):
        tables = ("euro_one", "euro_two")
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.sql"
            path.write_text(
                "CREATE TABLE `euro_one` (...);\n"
                "INSERT INTO `euro_one` VALUES (1);\n"
                "CREATE TABLE `euro_two` (...);\n"
                "INSERT INTO `euro_two` VALUES (2);\n",
                encoding="utf-8",
            )
            result = validate_scoped_backup(path, tables)
        self.assertEqual(tables, result["tables"])
        self.assertEqual(64, len(result["sha256"]))

    def test_scoped_backup_rejects_missing_table_data(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "backup.sql"
            path.write_text(
                "CREATE TABLE `euro_one` (...);\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "euro_one"):
                validate_scoped_backup(path, ("euro_one",))

    def test_wrong_build_confirmation_blocks_before_database_access(self):
        engine = Mock()
        with self.assertRaisesRegex(ValueError, BUILD_CONFIRMATION):
            build_and_validate_shadows(
                engine=engine,
                backup_file="missing.sql",
                confirmation="WRONG",
                suffix="20260803_210000",
            )
        engine.assert_not_called()

    def test_atomic_swap_and_rollback_cover_every_target(self):
        swap = build_swap_statement(TARGET_IMPORT_KEYS, "20260803_210000")
        rollback = build_rollback_statement(
            TARGET_IMPORT_KEYS,
            "20260803_210000",
        )
        self.assertTrue(swap.startswith("RENAME TABLE"))
        self.assertTrue(rollback.startswith("RENAME TABLE"))
        self.assertEqual(swap.count(" TO "), len(TARGET_IMPORT_KEYS) * 2)
        self.assertEqual(rollback.count(" TO "), len(TARGET_IMPORT_KEYS) * 2)
        self.assertIn("shadow_v055", swap)
        self.assertIn("pre_v055", rollback)

    def test_canonical_hash_matches_normalized_financial_values(self):
        columns = (
            "key_code",
            "time_period",
            "obs_value",
            "decimals",
        )
        record, invalid = normalize_row(
            columns,
            ("TEST.M.U2", "2024-01", "1.2345678912344", "3"),
        )
        self.assertEqual((), invalid)
        self.assertEqual(
            canonical_row_hash(columns, record),
            canonical_row_hash(columns, dict(record)),
        )
        self.assertEqual("1.234567891234", format(record["obs_value"], "f"))

    def test_record_batches_bound_mysql_packet_size(self):
        batches = list(record_batches(list(range(11)), 4))

        self.assertEqual([[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10]], batches)


if __name__ == "__main__":
    unittest.main()
