from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, Mock, patch
import unittest

from services.euro_rebuild_service import (
    BUILD_CONFIRMATION,
    TARGET_IMPORT_KEYS,
    build_and_validate_shadows,
    build_rollback_statement,
    build_shadow_schema_statements,
    build_swap_statement,
    canonical_row_hash,
    normalize_row,
    record_batches,
    shadow_table_name,
    swap_validated_shadows,
    validate_scoped_backup,
    versioned_table_name,
    source_chunks,
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
        engine = MagicMock()
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

    def test_canonical_hash_respects_storage_precision_and_outer_whitespace(self):
        columns = ("key_code", "time_period", "obs_value", "title")
        source, _ = normalize_row(
            columns,
            ("A", "2024-01", "9.171205", "Example "),
        )
        target, _ = normalize_row(
            columns,
            ("A", "2024-01", "9.171204566955566", "Example"),
        )
        column_types = {"obs_value": "FLOAT"}

        self.assertEqual(
            canonical_row_hash(columns, source, column_types),
            canonical_row_hash(columns, target, column_types),
        )

    def test_canonical_hash_treats_signed_storage_zero_as_zero(self):
        columns = ("key_code", "time_period", "obs_value")
        source, _ = normalize_row(columns, ("A", "2024-01", "-0.0000001"))
        target, _ = normalize_row(columns, ("A", "2024-01", "0"))
        column_types = {"obs_value": "DECIMAL(20, 6)"}

        self.assertEqual(
            canonical_row_hash(columns, source, column_types),
            canonical_row_hash(columns, target, column_types),
        )

    def test_canonical_hash_treats_signed_zero_as_zero_without_type_metadata(self):
        columns = ("key_code", "time_period", "obs_value")
        source, _ = normalize_row(columns, ("A", "2024-Q1", "-0E-12"))
        target, _ = normalize_row(columns, ("A", "2024-Q1", "0E-12"))

        self.assertEqual(
            canonical_row_hash(columns, source),
            canonical_row_hash(columns, target),
        )

    def test_record_batches_bound_mysql_packet_size(self):
        batches = list(record_batches(list(range(11)), 4))

        self.assertEqual([[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10]], batches)

    def test_source_chunks_can_use_an_explicit_external_path(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            configured = root / "configured.csv"
            external = root / "external.csv"
            configured.write_text("value\nconfigured\n", encoding="utf-8")
            external.write_text("value\nexternal\n", encoding="utf-8")

            chunks = list(
                source_chunks(
                    {"csv_path": configured},
                    chunk_size=10,
                    source_path=external,
                )
            )

        self.assertEqual("external", chunks[0].iloc[0]["value"])

    @patch("services.euro_rebuild_service.inspect")
    @patch("services.euro_rebuild_service._business_key_is_unique", return_value=True)
    @patch("services.euro_rebuild_service._post_swap_summary")
    @patch("services.euro_rebuild_service.validate_existing_shadows")
    @patch("services.euro_rebuild_service._table_exists")
    @patch("services.euro_rebuild_service.validate_scoped_backup")
    def test_hash_can_be_dropped_only_after_post_swap_validation(
        self,
        backup_mock,
        exists_mock,
        validate_mock,
        summary_mock,
        _unique_mock,
        inspect_mock,
    ):
        validation = Mock(
            active_table="euro_direct_debits",
            shadow_table="euro_direct_debits__shadow_v069_20260811_163215",
            source_rows=10,
        )
        backup_mock.return_value = {"path": Path("backup.sql")}
        exists_mock.side_effect = [True, False, False]
        validate_mock.return_value = (validation,)
        summary_mock.return_value = {
            "rows_count": 10,
            "unique_business_keys": 10,
            "null_business_keys": 0,
        }
        inspect_mock.return_value.get_columns.side_effect = [
            [{"name": "time_period", "type": "VARCHAR(20)"}],
            [{"name": "time_period", "type": "VARCHAR(20)"}],
        ]
        engine = MagicMock()
        connection = engine.begin.return_value.__enter__.return_value
        events = []
        connection.execute.side_effect = lambda statement: events.append(str(statement))

        def promoted(**_kwargs):
            events.append("PROMOTED_VALID")

        def final(**_kwargs):
            events.append("FINAL_VALID")

        result = swap_validated_shadows(
            engine=engine,
            backup_file="backup.sql",
            confirmation="SWAP_EURO_REBUILD_SHADOWS",
            suffix="20260811_163215",
            import_keys=("EURO_DIRECT_DEBITS",),
            version="v069",
            drop_hash_before_swap=False,
            post_swap_validator=promoted,
            post_hash_drop_validator=final,
        )

        self.assertIn("RENAME TABLE", events[0])
        self.assertEqual("PROMOTED_VALID", events[1])
        self.assertIn("DROP COLUMN", events[2])
        self.assertEqual("FINAL_VALID", events[3])
        self.assertEqual("after_validation", result["hash_column_drop_stage"])

    @patch("services.euro_rebuild_service.inspect")
    @patch("services.euro_rebuild_service._business_key_is_unique", return_value=True)
    @patch("services.euro_rebuild_service._post_swap_summary")
    @patch("services.euro_rebuild_service.validate_existing_shadows")
    @patch("services.euro_rebuild_service._table_exists")
    @patch("services.euro_rebuild_service.validate_scoped_backup")
    def test_failed_post_swap_validator_runs_atomic_rollback(
        self,
        backup_mock,
        exists_mock,
        validate_mock,
        summary_mock,
        _unique_mock,
        inspect_mock,
    ):
        validation = Mock(
            active_table="euro_direct_debits",
            shadow_table="euro_direct_debits__shadow_v069_20260811_163215",
            source_rows=10,
        )
        backup_mock.return_value = {"path": Path("backup.sql")}
        exists_mock.side_effect = [True, False, False]
        validate_mock.return_value = (validation,)
        summary_mock.return_value = {
            "rows_count": 10,
            "unique_business_keys": 10,
            "null_business_keys": 0,
        }
        inspect_mock.return_value.get_columns.return_value = [
            {"name": "time_period", "type": "VARCHAR(20)"}
        ]
        engine = MagicMock()
        connection = engine.begin.return_value.__enter__.return_value
        statements = []
        connection.execute.side_effect = lambda statement: statements.append(
            str(statement)
        )

        with self.assertRaisesRegex(RuntimeError, "forced failure"):
            swap_validated_shadows(
                engine=engine,
                backup_file="backup.sql",
                confirmation="SWAP_EURO_REBUILD_SHADOWS",
                suffix="20260811_163215",
                import_keys=("EURO_DIRECT_DEBITS",),
                version="v069",
                drop_hash_before_swap=False,
                post_swap_validator=lambda **_kwargs: (_ for _ in ()).throw(
                    RuntimeError("forced failure")
                ),
            )

        self.assertEqual(2, len(statements))
        self.assertIn("shadow_v069", statements[0])
        self.assertIn("failed_v069", statements[1])

    @patch(
        "services.euro_rebuild_service._mapped_source_columns",
        return_value=(
            "key_code",
            "time_period",
            "obs_value",
            "data_comp",
            "freq",
        ),
    )
    @patch("services.euro_rebuild_service.inspect")
    def test_shadow_schema_promotes_unindexed_text_without_truncation(
        self,
        inspect_mock,
        _columns_mock,
    ):
        inspect_mock.return_value.get_columns.return_value = [
            {"name": "key_code", "type": "VARCHAR(255)"},
            {"name": "time_period", "type": "VARCHAR(20)"},
            {"name": "obs_value", "type": "DECIMAL(20,6)"},
            {"name": "data_comp", "type": "VARCHAR(50)"},
            {"name": "freq", "type": "CHAR(1)"},
        ]

        statements = build_shadow_schema_statements(
            Mock(),
            "EURO_NATIONAL_ACCOUNTS",
            "20260811_103224",
            version="v062",
        )

        alter = statements[-1]
        self.assertIn("MODIFY `data_comp` TEXT NULL", alter)
        self.assertIn("MODIFY `freq` TEXT NULL", alter)
        self.assertIn("MODIFY `key_code` VARCHAR(255) NOT NULL", alter)
        self.assertIn("MODIFY `time_period` VARCHAR(20) NOT NULL", alter)


if __name__ == "__main__":
    unittest.main()
