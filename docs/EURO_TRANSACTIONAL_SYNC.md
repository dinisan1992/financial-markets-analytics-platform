# EURO Transactional Synchronization

Version: v0.6.5

Date: 11 August 2026

## Purpose

All 17 EURO tables now preserve their complete registered source history and a
unique `(key_code, time_period)` business key. The synchronization engine
updates that baseline without returning to destructive full-table imports or
loading millions of fingerprints into Python memory.

The default operation is a read-only plan. One CSV and one target table are
compared across every mapped column through bounded pandas chunks and a
temporary SQLite fingerprint index.

## Read-Only Plan

```powershell
python project_scripts/ingestion/sync_euro_macro.py EURO_FRAUD_LOSSES
```

The plan reports:

- source and target row and unique-key counts;
- planned inserts and full-row updates;
- unchanged and target-only rows;
- source and target null, duplicate and invalid-numeric blockers;
- source/target difference samples;
- unique business-key availability;
- expected row count after apply;
- the exact import-specific confirmation phrase;
- `database_write_performed: false`.

`--fail-on-blocker` returns exit code 2 when the plan is unsafe. Only one
explicit import key is accepted; there is no bulk `ALL --apply` mode.

## Data Policies

| Condition | Policy |
| --- | --- |
| Source key absent from SQL | Insert |
| Same key, different full-row hash | Update every mapped source column |
| Same key and hash | No SQL statement |
| Explicit source null | Authoritative; write SQL `NULL` |
| Row present only in SQL | Block for manual review |
| Source null business key | Block |
| Source duplicate business key | Block |
| Invalid non-empty numeric value | Block |
| Target duplicate/null key | Block |
| Delete | Disabled |

The source file is treated as an authoritative snapshot for keys it contains.
The engine checks file size and nanosecond modification time before, during and
after synchronization so a changing download cannot be committed accidentally.

## Guarded Apply Path

Apply mode requires all three explicit controls:

```powershell
python project_scripts/ingestion/sync_euro_macro.py IMPORT_KEY `
  --apply `
  --backup-file "<verified-table-backup.sql>" `
  --confirm "<confirmation-from-reviewed-plan>"
```

The service then:

1. verifies that the backup contains structure and data for the exact table;
2. rebuilds the complete disk-backed comparison immediately before writing;
3. rejects every plan blocker;
4. opens one database transaction;
5. streams the source again and writes only planned insert/update keys;
6. checks that written and planned action counts agree;
7. reruns the complete source-to-target audit on the uncommitted connection;
8. commits only when the final comparison is exact.

Any exception or post-write difference exits the transaction and rolls back all
of its changes. Automatic target-row deletion is not implemented.

## Validation Evidence

Deterministic SQLite fixtures prove:

- insert, update and unchanged classification;
- no-op idempotency;
- explicit source-null overwrite;
- target-only blocking and zero-delete policy;
- duplicate-source blocking;
- exact confirmation and backup guards;
- selective writes only;
- complete rollback after a forced post-write validation failure;
- default CLI planning without apply access.

Read-only MySQL plans also passed against:

| Contract | Source rows | Target rows | Inserts | Updates | Blockers |
| --- | ---: | ---: | ---: | ---: | ---: |
| EURO fraud losses | 198 | 198 | 0 | 0 | 0 |
| MFI interest rates | 1,594,491 | 1,594,491 | 0 | 0 | 0 |

The MFI plan completed with 50,000-row chunks, proving the planner on a
production-scale source. Both reports record `database_write_performed: false`.

## MySQL Acceptance Result

The v0.6.5 isolated MySQL drill completed the former acceptance gate. A verified
backup restored all 198 fraud rows exactly, controlled insert/update/null writes
passed the in-transaction audit, a second apply wrote zero rows, and a forced
post-write mismatch rolled back to the original fingerprint. The generated
schema was removed and the active schema's before/after hash was identical.

See `docs/EURO_MYSQL_ACCEPTANCE.md` for the procedure and recorded evidence.
Production apply remains conditional on a genuinely newer reviewed CSV, a fresh
read-only plan with no blockers and a new scoped backup.
