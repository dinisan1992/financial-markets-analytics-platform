# EURO Streaming Validation

Audit baseline: v0.6.1; post-migration verification: v0.6.3

Migration tooling: v0.6.2

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

Version 0.6.2 completes the code-side migration gate without authorizing a
database change. The shadow loader and pre-swap validator now reuse the same
disk-backed store, operate on one table per command and use isolated `v062`
names plus table-specific confirmations.

The execution order is MFI interest rates, national accounts and consumer
prices. For each table, the required checkpoints are:

1. create and verify a table-scoped structure-and-data SQL backup on a separate
   physical volume;
2. repeat the read-only capacity preflight;
3. build and fully validate the shadow without changing the active table;
4. inspect the report and exact swap and rollback statements;
5. obtain separate approval for the atomic swap;
6. rerun this read-only audit before proceeding to the next table.

No shadow, backup, index, table, SQL row or source CSV was created or changed in
MySQL during v0.6.1 or v0.6.2.

## v0.6.3 Post-Migration Verification

After separate approved backups, builds and atomic swaps, the same validator
was rerun against all three active tables with `--fail-on-difference`:

| Import | Source rows | Active SQL rows | Missing | Extra | Hash mismatch |
| --- | ---: | ---: | ---: | ---: | ---: |
| Consumer prices | 6,548,663 | 6,548,663 | 0 | 0 | 0 |
| National accounts | 2,721,359 | 2,721,359 | 0 | 0 | 0 |
| MFI interest rates | 1,594,491 | 1,594,491 | 0 | 0 | 0 |
| **Total** | **10,864,513** | **10,864,513** | **0** | **0** | **0** |

The run also found zero null business keys, duplicate business keys and invalid
numeric values. Source and target chunks remained bounded at 50,000 rows and
the database received read operations only. The consolidated result digest is:

`6B0EC4A231ADDA60FB48091E27B9D5BC8E31174D6C8840157EBCF78D6F382F59`

The v0.6.1 figures above remain the immutable before-migration baseline. See
`EURO_LARGE_REBUILD_RESULTS.md` for backup, retained-table and rollback details.
