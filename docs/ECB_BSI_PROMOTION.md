# BSI Atomic Promotion Runbook

Status: completed and independently verified

Date: 17 August 2026

## Scope

This runbook is restricted to `EURO_BALANCE_SHEET_ITEMS`. It cannot target BLS,
PCP or any other table. The promotion command has no build or cleanup mode and
requires the exact `SWAP_EURO_BALANCE_SHEET_ITEMS_V087_ACTIVE` confirmation.

The implementation is bound to three immutable local reports:

| Evidence | SHA-256 |
| --- | --- |
| Readiness report | `D9145086C967C09D7D9D910C0AED5FB08E028C7C784D23538D8893F43803FBEF` |
| Shadow build report | `F3D9C448D68781630B666272F940E020398C1F194EFCC7001DE3F0D8BA19DEE6` |
| Independent post-build verification | `D9F1EB83336C617EC32B8E7B3AAB5E25E1DC22AF66D8B6BBD1DAA99E0E2577EB` |

The reports form a checked chain. The build identifies the exact readiness
report, and the independent verification identifies the exact build report.
The candidate CSV and scoped SQL backup names, sizes and hashes must still
match before either command accepts the evidence.

## Read-Only Preflight

`project_scripts/diagnostics/preflight_ecb_bsi_swap.py` exposes no
confirmation, build, cleanup or swap option. It will:

1. Verify all report hashes and cross-report identities.
2. Re-hash the official CSV and scoped structure-and-data SQL backup.
3. Recompute the active data/schema checkpoint and shadow schema evidence.
4. Repeat the complete source-to-shadow comparison through the forced,
   unbuffered MySQL cursor introduced in v0.8.6.
5. Reject missing active/shadow tables or occupied retained/failed names.
6. Write an ignored local report recording zero database and CSV writes.

The preflight completed against MySQL with 7,812,208 active rows and 8,055,309
matching source/shadow rows. It found zero missing or mismatched source rows,
performed no database or CSV write and did not authorize promotion. Its
ignored local report SHA-256 is
`950B70C560858C51E6A67B9CF89170C0A42AF9DB08B987C03589B7D11BB14DB9`.

## Atomic Procedure

After the successful reviewed preflight and a separate exact authorization,
`project_scripts/diagnostics/swap_ecb_bsi.py` performed this sequence:

1. Repeat all pinned report, source, backup, active and shadow checks.
2. Repeat the complete official-source-to-shadow validation.
3. Atomically rename the active table to its retained name and the validated
   shadow to the active name.
4. Prove that the retained table equals the complete pre-swap active
   checkpoint and that the promoted schema equals the reviewed shadow.
5. Remove the technical source-row hash only after the promoted state passes.
6. Compare the complete official source against the new active table and
   validate its exact decimal type, composite primary key and row counts.
7. Write a signed ignored promotion report without changing the active CSV.

Any failure after the atomic rename invokes the inverse atomic rename. The
former active table is restored and the failed promoted table is retained for
diagnosis; no table or source row is automatically deleted.

## Final State

| Role | Table | Rows |
| --- | --- | ---: |
| Active official snapshot | `euro_balance_sheet_items` | 8,055,309 |
| Immediate rollback checkpoint | `euro_balance_sheet_items__pre_v079_20260817_141854` | 7,812,208 |

The official snapshot is authoritative for the active table. It introduced
587,428 official-source-only keys and withdrew 344,327 former active-only keys.
Every withdrawn or superseded row remains available in the complete retained
rollback checkpoint.

## Execution Evidence

The exact confirmation was received after the read-only preflight was reviewed.
The command repeated all pinned checks, performed the atomic rename, validated
the retained and promoted states, removed the technical hash and completed the
full official-source-to-active audit. It reported `swap_performed: true` and
`rollback_performed: false`.

Independent read-only checks confirmed 8,055,309 active rows, 7,812,208 retained
rows, no shadow or failed-table artifact and no technical hash column in the
active schema. No active CSV changed. The ignored local promotion report
SHA-256 is
`EEDA230CDC30CE0E7037F975B57E5D397B4B4C67860CF1EE628CC8FE708F687B`.
