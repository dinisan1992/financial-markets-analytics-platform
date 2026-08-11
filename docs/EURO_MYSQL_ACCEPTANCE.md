# EURO MySQL Acceptance Drill

Version: v0.6.5

Date: 11 August 2026

## Purpose

This drill qualifies the guarded EURO synchronization engine against the same
MariaDB/MySQL transaction behavior used by the local platform. It never writes
to the active schema. The small 198-row EURO fraud-loss contract is copied into
a uniquely named temporary schema, exercised, verified and removed.

The command is read-only by default. Execute mode requires all of:

- `--execute`;
- the exact acceptance confirmation phrase;
- an explicit backup directory outside Git, supplied through `--backup-dir` or
  `PROJECT_BACKUP_DIR`;
- a generated schema name beginning with `mfi_sync_acceptance_v065_`.

## Procedure

The acceptance command performs these operations in order:

1. proves that the active fraud table exactly matches its registered CSV;
2. calculates a deterministic full-row fingerprint of the active table;
3. creates and verifies a table-scoped structure-and-data SQL backup;
4. creates a new isolated schema and restores the backup into it;
5. proves that the restored table has the active table's row count and hash;
6. applies one synthetic insert and two updates, including a source-null
   overwrite;
7. validates the complete result before commit and proves a second apply is a
   zero-write no-op;
8. restores the original test table from the backup;
9. installs a test-only trigger that forces the post-write comparison to fail;
10. proves that MariaDB rolls back the complete transaction;
11. removes the generated schema and rechecks the active table.

## Recorded Result

The v0.6.5 local acceptance run passed:

| Check | Result |
| --- | --- |
| Active rows before | 198 |
| Active full-row SHA-256 before | `F3291C5EF9C7386F7C4002F5FED0BDABABA06CC57649B95D70C945E57B64D1A5` |
| Scoped backup bytes | 110,420 |
| Scoped backup SHA-256 | `34160CAE792C6340D8000B3E8028A1CC32B52A040518B9EDC03F19FFDDDE5300` |
| Restored rows and fingerprint | Exact match |
| Controlled changes | 1 insert, 2 updates, 3 writes |
| Source-null column exercised | `comment_obs` |
| Post-write comparison | Passed before commit |
| Immediate reapply | 0 writes, idempotent |
| Forced mismatch | Detected before commit |
| Rows after forced rollback | 198, original fingerprint preserved |
| Active rows and hash after | Exact match to before |
| Active database writes | 0 |
| Remaining acceptance schemas | 0 |

The SQL dump, generated CSV fixtures and JSON report are local evidence and are
excluded from Git by `.gitignore`.

## Usage

Inspect the scope without database writes:

```powershell
python project_scripts/diagnostics/acceptance_test_euro_sync_mysql.py
```

Run the isolated acceptance drill after reviewing the command:

```powershell
python project_scripts/diagnostics/acceptance_test_euro_sync_mysql.py `
  --execute `
  --backup-dir "<backup-directory-outside-the-repository>" `
  --confirm RUN_ISOLATED_EURO_FRAUD_MYSQL_ACCEPTANCE_V065
```

## Scope Boundary

This result qualifies transaction commit, null overwrite, idempotency, backup
restore and rollback mechanics in an isolated MySQL schema. It is not permission
to update the active database and it does not prove that a future CSV is
financially correct. A production refresh still requires a newer reviewed CSV,
a read-only plan with no blockers, a fresh scoped backup and the import-specific
apply confirmation.
