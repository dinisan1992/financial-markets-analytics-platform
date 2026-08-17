# Official BLS Atomic Promotion

Version: v0.8.1

Date: 17 August 2026

## Scope

This checkpoint promoted the separately built and twice-validated official
Bank Lending Survey shadow. The swap-only command required exact confirmation
and revalidated the pinned readiness report, build report, official CSV,
scoped SQL backup, active checkpoint and complete shadow before changing any
table name.

The atomic operation was:

```sql
RENAME TABLE
  euro_bank_lending_survey
    TO euro_bank_lending_survey__pre_v079_20260817_115720,
  euro_bank_lending_survey__shadow_v079_20260817_115720
    TO euro_bank_lending_survey;
```

No table or source row was deleted. The inverse atomic rename remains the
immediate rollback path.

## Active Table

| Check | Result |
| --- | --- |
| Rows | 1,225,110 |
| Unique business keys | 1,225,110 |
| Null business keys | 0 |
| Non-null observations | 830,090 |
| First period | `2003-Q1` |
| Last period | `2026-Q3` |
| Columns | 27 |
| `time_period` | `VARCHAR(20)` |
| Primary key | `(key_code, time_period)` |
| Technical hash column | Removed after validation |
| Data SHA-256 | `8703EBD15459AAB21169BC074A49C90255A0AC020049CB871E4D465F4EFCEB59` |
| Schema SHA-256 | `3C2D3C6884C565818EC641BB76927BDE88491AEB0068321E5610EF1A04F6E627` |

The complete post-swap source audit found zero missing source keys, zero extra
target keys and zero mapped-value hash mismatches.

## Retained Table

The former active table remains intact as:

`euro_bank_lending_survey__pre_v079_20260817_115720`

It contains 1,164,356 rows with data SHA-256
`CFE1767294A0E345483AFF7AA8C885B8D5D829677BD58B5DB3A73A8866E7FD5D`
and schema SHA-256
`C9F5D7AB529D7FC814496188A2A40DD71A944516D829015255AADDAEE1565E8D`.
No shadow or failed-table artifact remains.

## Safety-Gate Evidence

Before the successful run, two representation-only comparison defects were
caught by the safety gates. The first stopped before the swap. The second
triggered the automatic inverse rename and restored the original active table
with its exact fingerprint. The candidate was retained, the comparisons were
corrected and covered by regression tests, and the complete promotion was then
rerun from the initial validation stage.

The successful operation reports `swap_performed: true`,
`rollback_performed: false` and `source-to-active valid: true`. Its local report
SHA-256 is
`FA5371950D032E0CFE1F42967F240DEEA5EB9731B374150AE1F536C28405090A`.
Generated audit reports, raw sources, backups and local paths remain excluded
from Git.

## Reusable Command Contract

`project_scripts/diagnostics/swap_ecb_bls.py` exposes no build, cleanup or
generic table option. It requires the two pinned report hashes, external source
and backup directories, a bounded validation workspace and the exact
`SWAP_EURO_BANK_LENDING_SURVEY_V081_ACTIVE` confirmation. Any failed
post-swap validation executes the inverse atomic rename before raising the
error.
