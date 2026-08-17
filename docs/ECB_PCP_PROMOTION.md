# PCP Atomic Promotion Runbook

Status: preflight complete; promotion not authorized or performed

Date: 17 August 2026

## Scope

This runbook is restricted to `EURO_CARD_PAYMENTS`. It cannot target BLS, BSI
or any other table. The promotion command has no build or cleanup mode and
requires the exact `SWAP_EURO_CARD_PAYMENTS_V083_ACTIVE` confirmation.

The command is bound to three immutable local reports:

| Evidence | SHA-256 |
| --- | --- |
| Readiness report | `2F12A83243887974B327E81563DEE526CA7CFFC868E6AFB44AC1015A8AFD0A01` |
| Shadow build report | `D07C53007549F70E26E3885C1D49A52AF5A2064F8EE0E708A57D5762C1A0306D` |
| Independent post-build verification | `A564DD9E61E910BC62825A78B31771D82256C57A045C68431E95040DBC8C6E0B` |

The reports form a checked chain: the build report identifies the exact
readiness report, and the independent verification identifies the exact build
report. Candidate CSV and scoped SQL backup names, sizes and hashes must still
match before the database is opened for promotion.

## Read-Only Preflight

`project_scripts/diagnostics/preflight_ecb_pcp_swap.py` exposes no confirmation
or swap option. It repeats all report, file, backup, active-table and shadow
checks, then performs a complete memory-bounded source-to-shadow comparison.

The latest preflight reproduced:

| Check | Result |
| --- | --- |
| Active rows | 815,173 |
| Shadow/source rows | 1,081,151 |
| Unique source and shadow keys | 1,081,151 |
| Null or duplicate keys | 0 |
| Missing or mismatched rows | 0 |
| Database writes | 0 |
| Active CSV writes | 0 |
| Swap authorized/performed | No / No |

Its ignored local report has SHA-256
`DAE34DE8DDF6EC04FBCA35789187C2C4994066C842F5DA5107230F860331902A`.
Raw reports remain local because they contain machine-specific paths.

## Atomic Procedure

After separate authorization, `project_scripts/diagnostics/swap_ecb_pcp.py`
will perform this single-table sequence:

1. Verify all three report hashes and their cross-report identities.
2. Re-hash the official CSV and scoped structure-and-data SQL backup.
3. Recompute and compare the active data/schema checkpoint and shadow schema.
4. Repeat the complete official-source-to-shadow validation.
5. Atomically rename the active table to its retained name and the validated
   shadow to the active name.
6. Prove that the retained table equals the complete pre-swap active checkpoint
   and that the promoted schema equals the reviewed shadow.
7. Remove the technical source-row hash only after the promoted state passes.
8. Compare the complete official source against the new active table and verify
   its exact decimal value type, composite primary key and row counts.
9. Write a signed local promotion report without changing the configured CSV.

Any failure after the atomic rename triggers an inverse atomic rename that
restores the former active table. A failed promoted table is retained for
diagnosis; no table or source row is automatically deleted.

## Expected State

| Role | Table | Rows |
| --- | --- | --- |
| New active | `euro_card_payments` | 1,081,151 |
| Immediate rollback checkpoint | `euro_card_payments__pre_v079_20260817_115720` | 815,173 |

The official snapshot is authoritative for the new active table. It adds
272,146 current source keys, omits 6,168 withdrawn active-only keys and contains
807,892 reviewed revisions relative to the former active snapshot. Every
withdrawn or superseded row remains available in the retained table.

## Authorization Boundary

This document, the service, tests and read-only preflight do not authorize the
promotion. The exact confirmation is supplied only after an explicit decision
to change the database. BSI remains outside this scope.
