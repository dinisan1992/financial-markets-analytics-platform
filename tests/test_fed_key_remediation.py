from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from project_scripts.diagnostics.remediate_fed_macro_keys import (
    APPLY_CONFIRMATION,
    TARGET_TABLES,
    FedKeyAudit,
    apply_fed_key_remediation,
    build_add_key_statement,
    build_drop_key_statement,
    validate_scoped_backup,
)


def _audit(table_name, unique_date_key=False, duplicate_groups=0):
    return FedKeyAudit(
        table_name=table_name,
        table_exists=True,
        date_column_exists=True,
        date_nullable=False,
        rows_count=10,
        non_null_dates=10,
        distinct_dates=10 if duplicate_groups == 0 else 9,
        null_dates=0,
        duplicate_groups=duplicate_groups,
        first_date="2025-01-01",
        last_date="2025-03-05",
        unique_date_key=unique_date_key,
    )


class FakeResult:
    pass


class FakeConnection:
    def __init__(self, statements):
        self.statements = statements

    def execute(self, statement):
        self.statements.append(str(statement))
        return FakeResult()


class FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        return False


class FakeEngine:
    def __init__(self):
        self.statements = []

    def begin(self):
        return FakeTransaction(FakeConnection(self.statements))


class FedKeyRemediationTests(unittest.TestCase):
    def test_statements_are_scoped_to_the_expected_index(self):
        self.assertEqual(
            "ALTER TABLE `fed_total_assets` ADD UNIQUE KEY "
            "`uq_observation_date` (`observation_date`)",
            build_add_key_statement("fed_total_assets"),
        )
        self.assertEqual(
            "ALTER TABLE `fed_total_assets` DROP INDEX `uq_observation_date`",
            build_drop_key_statement("fed_total_assets"),
        )

    def test_confirmation_is_required_before_audit_or_write(self):
        engine = FakeEngine()
        with self.assertRaisesRegex(ValueError, APPLY_CONFIRMATION):
            apply_fed_key_remediation(
                engine,
                backup_file="missing.sql",
                confirmation="wrong",
            )
        self.assertEqual([], engine.statements)

    def test_duplicate_audit_blocks_backup_access_and_write(self):
        engine = FakeEngine()
        audits = [_audit(table_name) for table_name in TARGET_TABLES]
        audits[0] = _audit(TARGET_TABLES[0], duplicate_groups=1)
        with patch(
            "project_scripts.diagnostics.remediate_fed_macro_keys."
            "audit_fed_key_targets",
            return_value=audits,
        ), patch(
            "project_scripts.diagnostics.remediate_fed_macro_keys."
            "validate_scoped_backup"
        ) as validate_backup:
            with self.assertRaisesRegex(RuntimeError, TARGET_TABLES[0]):
                apply_fed_key_remediation(
                    engine,
                    backup_file="missing.sql",
                    confirmation=APPLY_CONFIRMATION,
                )
        validate_backup.assert_not_called()
        self.assertEqual([], engine.statements)

    def test_scoped_backup_requires_every_target_table(self):
        with TemporaryDirectory() as temp_dir:
            backup = Path(temp_dir) / "backup.sql"
            backup.write_text(
                "CREATE TABLE `fed_total_assets` (...);\n"
                "INSERT INTO `fed_total_assets` VALUES (1);\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "fed_bank_credit"):
                validate_scoped_backup(backup)

    def test_apply_adds_only_missing_keys_and_returns_rollback_sql(self):
        engine = FakeEngine()
        pre_audits = [_audit(table_name) for table_name in TARGET_TABLES]
        pre_audits[0] = _audit(TARGET_TABLES[0], unique_date_key=True)
        post_audits = [
            _audit(table_name, unique_date_key=True) for table_name in TARGET_TABLES
        ]
        backup_result = {
            table_name: {"sha256": "A" * 64} for table_name in TARGET_TABLES
        }
        with patch(
            "project_scripts.diagnostics.remediate_fed_macro_keys."
            "audit_fed_key_targets",
            side_effect=(pre_audits, post_audits),
        ), patch(
            "project_scripts.diagnostics.remediate_fed_macro_keys."
            "validate_scoped_backup",
            return_value=backup_result,
        ):
            result = apply_fed_key_remediation(
                engine,
                backup_file="backup.sql",
                confirmation=APPLY_CONFIRMATION,
            )

        self.assertEqual(3, len(engine.statements))
        self.assertEqual(TARGET_TABLES[1:], result["changed_tables"])
        self.assertEqual((TARGET_TABLES[0],), result["already_ready_tables"])
        self.assertEqual(3, len(result["rollback_statements"]))


if __name__ == "__main__":
    unittest.main()
