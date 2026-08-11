# EURO Streaming Validation

Version: v0.6.1

Audit date: 11 August 2026

## Purpose

Consumer prices, national accounts and MFI interest rates contain more than
ten million registered source rows. The former exact validator retained every
business-key hash in a Python dictionary and copied that dictionary during
comparison. That design was not acceptably memory-bounded for the remaining
rebuilds.

Version 0.6.1 adds a read-only source-to-target validator that keeps only one
CSV or SQL chunk in Python memory. It writes `(key_code, time_period)` and a
canonical SHA-256 row signature to a temporary local SQLite store, then uses
SQLite joins to classify missing, extra and mismatched rows.

The temporary SQLite database is an audit workspace, not part of the
application database. MySQL receives only metadata reads and `SELECT` queries.

## Command

```powershell
python project_scripts/diagnostics/audit_euro_streaming_completeness.py --chunk-size 50000
```

By default, SQLite workspaces are created under the operating-system temporary
directory and deleted after each table. JSON and CSV reports are written under
`audit_outputs/euro_streaming_validation/`, which is excluded from Git. An
existing alternative temporary directory can be supplied with
`--workspace-dir`. The command also writes `summary.sha256` so the local
baseline can be verified before a later comparison.

## Live Findings

| Import | CSV rows | SQL rows | Missing from SQL | Extra in SQL | Hash mismatches | Store | Time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Consumer prices | 6,548,663 | 675,500 | 5,873,163 | 0 | 9,456 | 572 MiB | 257.9 s |
| National accounts | 2,721,359 | 617,500 | 2,103,859 | 0 | 302,628 | 336 MiB | 140.3 s |
| MFI interest rates | 1,594,491 | 96,000 | 1,498,491 | 0 | 1,598 | 147 MiB | 65.2 s |
| **Total** | **10,864,513** | **1,389,000** | **9,475,513** | **0** | **313,682** | one at a time | **464.0 s** |

All three contracts also reported:

- zero source and target null business keys;
- zero source and target duplicate business keys;
- zero source and target invalid numeric rows;
- source and target chunks no larger than 50,000 rows;
- `database_write_performed=false`.

The consolidated local `summary.json` baseline has SHA-256
`92F97B9C38C418A113A440D20E43AAC2332041287763977099149CD885DFCC13`.

The mismatch count is separate from missing rows. It means the key exists in
both CSV and SQL, but one or more mapped values differ after canonical numeric
normalization. This supports rebuilding from source rather than extending the
incomplete active tables in place.

## Safety Model

The validator:

- validates the registered EURO contract and target columns before scanning;
- preserves textual period labels and the shared decimal/integer normalization;
- hashes every mapped source column, not only `obs_value`;
- records duplicate groups and conflicting duplicate values explicitly;
- keeps target access read-only and reports that fact in every result;
- processes one import at a time and deletes its comparison store on exit;
- refuses to start when the selected workspace has less than 2 GiB free.

A deterministic SQL-capture test asserts that the target engine receives only
read statements. Controlled fixtures independently cover exact equality,
missing rows, extra rows, value mismatches, null keys, invalid numerics and
duplicate keys.

## Migration Gate

This release validates the active source-to-SQL gap but does not authorize or
perform a rebuild. Before any MySQL change:

1. Replace the legacy in-memory fingerprint dictionary in the shadow-build path
   with the disk-backed store.
2. Process one table per migration checkpoint, starting with consumer prices.
3. Create and verify a table-scoped structure-and-data SQL backup.
4. Recheck disk capacity while preserving space for MySQL temporary, redo and
   retained rollback data.
5. Build a versioned shadow and validate rows, keys, non-null values and full-row
   signatures without changing the active table.
6. Present the exact atomic swap and rollback statements for separate approval.
7. Re-run this read-only audit after the swap before proceeding to the next
   table.

No shadow, backup, index, table, SQL row or source CSV was created or changed in
MySQL during v0.6.1.
