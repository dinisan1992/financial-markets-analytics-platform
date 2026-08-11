# EURO Direct Debits Verified Backup

Version: v0.6.8

Date: 11 August 2026

## Scope

The backup contains the structure and data of `euro_direct_debits` only. It is
stored on a separate local volume and excluded from Git. This document records
the filename and cryptographic evidence without publishing the private absolute
path or SQL content.

## Backup Evidence

| Property | Result |
| --- | --- |
| Filename | `euro_direct_debits_before_v068_20260811_160137.sql` |
| Bytes | 25,308,899 |
| SHA-256 | `724F9B20F7A7A651395FDBC689D99E23B324F96329EC6E629BC60F616682852E` |
| Tables | 1 (`euro_direct_debits`) |
| Structure marker | Present |
| Data marker | Present |
| Active database write | No |

The digest was calculated by the backup command and independently confirmed
after the file handle was closed.

## Isolated Restore Evidence

The verifier required the exact import-specific confirmation, created a unique
schema beginning with `euro_backup_verify_v068_`, restored the SQL file, and
then compared the restored table with the active table.

| Check | Active before | Restored | Active after |
| --- | --- | --- | --- |
| Rows | 75,647 | 75,647 | 75,647 |
| Data SHA-256 | `5BDAB01AFCF91D83161657736E94A0853B280FC946168008571233657EDD2907` | same | same |
| Columns | 31 | 31 | 31 |
| Schema SHA-256 | `6E6237FA71CBAF7603782A694107C0B9352D843E13B0258F6F42A32DBEB0F768` | same | same |
| Primary key | `(key_code, time_period)` | same | same |

The generated schema was removed in the mandatory cleanup path. An independent
query then confirmed:

- zero schemas matching `euro_backup_verify_v068_%`;
- 75,647 active rows;
- active `time_period` still `YEAR(4)`.

The local restore report SHA-256 is
`F5AD183DBA7D2A04D34251576895708308986FE4A60CA5591658897E77CEB2F2`.
Generated reports remain under Git-ignored `audit_outputs/`.

## Reusable Commands

Create a one-table backup on an external volume:

```powershell
python project_scripts/diagnostics/backup_euro_table.py EURO_DIRECT_DEBITS `
  --output-dir "<external-backup-directory>"
```

Verify restoration in an isolated schema:

```powershell
python project_scripts/diagnostics/verify_euro_table_backup.py `
  EURO_DIRECT_DEBITS `
  --backup-file "<verified-backup.sql>" `
  --confirm VERIFY_EURO_DIRECT_DEBITS_BACKUP_RESTORE_V068
```

The restore command does not place the database password on the command line.
It refuses an existing or incorrectly named test schema and always attempts
cleanup after schema creation.

## v0.6.9 Follow-Up

The separately authorized shadow build is now complete. Version v0.6.9 used
this exact backup as a mandatory checkpoint before creating and validating the
versioned `VARCHAR(20)` table. The backup still protects the unchanged active
table. No atomic swap was authorized or performed; that remains a later,
separate gate. See `EURO_DIRECT_DEBITS_SHADOW.md`.
