import unittest

from project_scripts.diagnostics.backup_market_tables import (
    DEFAULT_TABLES,
    build_mysqldump_command,
)
from project_scripts.diagnostics.remediate_market_tables import (
    TARGETS,
    build_rename_statement,
    versioned_table_name,
)


class MarketTableRemediationTests(unittest.TestCase):
    def test_backup_command_never_contains_database_password(self):
        command = build_mysqldump_command("mysqldump", DEFAULT_TABLES)

        self.assertFalse(any("password" in argument.lower() for argument in command))
        self.assertIn("--single-transaction", command)
        self.assertIn("btc_analysis", command)

    def test_versioned_names_remain_valid_mysql_identifiers(self):
        name = versioned_table_name("a" * 64, "pre_v050", "20260803")

        self.assertLessEqual(len(name), 64)
        self.assertNotIn("-", name)

    def test_atomic_rename_keeps_original_tables_as_backups(self):
        statement = build_rename_statement(TARGETS, "20260803")

        self.assertTrue(statement.startswith("RENAME TABLE"))
        self.assertEqual(statement.count(" TO "), len(TARGETS) * 2)
        self.assertIn("sp500_analysis_clean__pre_v050_20260803", statement)
        self.assertIn("sp500_analysis_clean__shadow_20260803", statement)


if __name__ == "__main__":
    unittest.main()
