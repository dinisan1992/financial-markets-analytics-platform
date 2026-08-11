# EURO Direct Debits Temporal Remediation

Version: v0.6.8

Date: 11 August 2026

## Status

Diagnosis and planning are complete. The active MySQL table has not been
altered. No shadow was created, no row was inserted or updated, and no table was
renamed.

## Confirmed Cause

The registered source contains three temporal frequencies:

| Frequency | Source rows | Target rows | Common exact keys |
| --- | ---: | ---: | ---: |
| Annual (`A`) | 44,539 | 44,539 | 44,539 |
| Semiannual (`H`) | 42,039 | 21,097 | 0 |
| Quarterly (`Q`) | 34,986 | 10,011 | 0 |

The active `euro_direct_debits.time_period` column is `YEAR(4)`. It preserves
annual labels such as `2024`, but collapses labels such as `2024-S1`,
`2024-S2` and `2024-Q1` to `2024`.

The complete source/target key comparison found:

- 121,564 source rows and unique business keys;
- 75,647 active target rows;
- 44,539 exact common keys;
- 77,025 source-only keys, all explained by year collapse;
- 31,108 target-only keys, all explained by corresponding detailed periods;
- zero unexplained source-only or target-only keys.

This is a target-schema defect, not a newly introduced source-key revision.

## Read-Only Commands

Run the diagnosis:

```powershell
python project_scripts/diagnostics/diagnose_euro_direct_debits.py `
  --output-dir audit_outputs/euro_direct_debits
```

Generate an inspectable rebuild plan:

```powershell
python project_scripts/diagnostics/plan_euro_direct_debits_rebuild.py `
  --suffix YYYYMMDD_HHMMSS `
  --output-dir audit_outputs/euro_direct_debits
```

Neither command exposes `--apply`, `--build` or `--swap`. Both connect only for
schema inspection and `SELECT`; their reports remain under Git-ignored
`audit_outputs/`.

The recorded local evidence has SHA-256:

- diagnostic JSON: `40068D9897832298456AF92C312799018F74959C83C14CC9710A9441EDFA09F4`;
- rebuild-plan JSON: `1EB49E1BF2DBCEB67D7A2A19CB9A9849917257ED7889893A320B9E1B9A33EB60`.

## Proposed Schema

The plan creates an isolated shadow based on the active table and changes only
the temporal contract required for faithful source storage:

```sql
time_period VARCHAR(20) NOT NULL
PRIMARY KEY (key_code, time_period)
```

The expected shadow has 121,564 rows and 121,564 unique business keys. The
plan also records versioned shadow, retained and failed-table names, a future
atomic swap statement and its inverse rollback statement. These statements are
evidence only and are not executed by the v0.6.7 command.

## Mandatory Gates

1. Create a fresh Direct Debits structure-and-data backup on the separate
   physical volume.
2. Verify its SHA-256 and restore it independently before relying on it.
3. Obtain explicit authorization for a one-table shadow build.
4. Compare every mapped source and shadow row with disk-backed hashes.
5. Confirm exact row/key counts, zero null keys, zero duplicate keys and zero
   full-row mismatches.
6. Obtain a separate explicit authorization for the atomic swap.
7. Retain the current table under its versioned rollback name.
8. Run the read-only synchronization plan and application validation
   immediately after any future swap.

Until all gates pass, `EURO_DIRECT_DEBITS` remains blocked by
`unsafe_time_period_type` and `target_only_rows_require_review`.

## v0.6.8 Backup Gate

The first two mandatory gates are complete. A 25,308,899-byte scoped backup was
created on a separate volume, independently hashed and restored into a generated
isolated schema. The restored table matches all 75,647 active rows, the complete
data and schema fingerprints, 31 columns and the composite primary key. The
temporary schema was removed and the active table remained unchanged.

The backup result does not authorize the shadow build or swap. Those remain
separate gates. See `EURO_DIRECT_DEBITS_BACKUP.md`.
