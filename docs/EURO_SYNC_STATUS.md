# EURO Synchronization Status

Version: v0.7.5

Date: 11 August 2026

## Scope

All 17 registered EURO/ECB source contracts were compared with their active
MySQL targets one at a time. Every execution used planning mode. No `--apply`
argument was used and all saved reports record
`database_write_performed: false`.

The reports are local evidence under Git-ignored `audit_outputs/`. Their latest
state can be consolidated without reading a source CSV or connecting to MySQL:

```powershell
python project_scripts/diagnostics/consolidate_euro_sync_status.py
```

## v0.7.5 Backup And Shadow Gate

Complete active-table backups for BLS, PCP and BSI now exist on a separate
physical volume with structure, data and independent SHA-256 verification.
Post-backup row counts are unchanged. Versioned shadow, retained-table and
atomic-swap previews were generated without execution, and none of the six
planned tables exists. The retention policy makes the current official ECB
snapshot authoritative while preserving withdrawn keys in the future retained
table. See `ECB_BACKUP_AND_SHADOW_PLAN.md`.

## v0.7.4 Official Snapshot Refresh

Fresh complete `BLS`, `PCP` and `BSI` datasets were downloaded from the
official ECB Data API into external staging. All 10,361,570 candidate rows have
unique non-null business keys, valid numeric observations and schemas matching
the registered active CSVs.

SELECT-only MySQL plans found 60,754 BLS candidate-only keys and no target-only
keys; 272,146 PCP candidate-only and 6,168 target-only keys; and 587,428 BSI
candidate-only and 344,327 target-only keys. Broad historical metadata and
value revisions make the v0.7.3 15/1/54 precision findings a preserved baseline
for the October 2025 files, not the current write plan.

The staged files have not replaced active CSVs and no SQL write was performed.
See `ECB_SOURCE_REFRESH.md` for hashes, exact mismatch counts and the next
authorization gates.

## v0.7.3 Precision Review

The three equal-cardinality changed contracts were revalidated with hashes
normalized to their active SQL storage types. Card Payments fell from 459,207
apparent updates to 15 rows, Bank Lending Survey fell from 222,668 to one, and
Balance Sheet Items fell from 3,132,298 to 54
sixth-decimal differences. Source and target keys remain exact in all three
contracts and no database writes were performed. See
`EURO_PRECISION_AUDIT.md`.

Government Finance was not reclassified in this precision cycle because its
main issue is a 3,822,937-row source-universe expansion, not equal-cardinality
field differences.

## v0.7.0 Planning Baseline

| Contract | Status | Source | Target | Inserts | Updates | Target only |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| EURO_ATM_POS_TRANSACTIONS | EXACT | 607,291 | 607,291 | 0 | 0 | 0 |
| EURO_BALANCE_SHEET_ITEMS | CHANGES | 7,812,208 | 7,812,208 | 0 | 3,132,298 | 0 |
| EURO_BANK_LENDING_SURVEY | CHANGES | 1,164,356 | 1,164,356 | 0 | 222,668 | 0 |
| EURO_CARD_PAYMENTS | CHANGES | 815,173 | 815,173 | 0 | 459,207 | 0 |
| EURO_CARD_PAYMENTS_MERCHANT_CATEGORY | EXACT | 419,510 | 419,510 | 0 | 0 | 0 |
| EURO_COMPOSITE_SYSTEMIC_STRESS | EXACT | 142,527 | 142,527 | 0 | 0 | 0 |
| EURO_COUNTRY_FINANCIAL_STRESS | EXACT | 12,806 | 12,806 | 0 | 0 | 0 |
| EURO_CREDIT_TRANSFERS | EXACT | 218,564 | 218,564 | 0 | 0 | 0 |
| EURO_DIRECT_DEBITS | BLOCKED | 121,564 | 75,647 | 77,025 | 159 | 31,108 |
| EURO_EMONEY_PAYMENTS | EXACT | 147,202 | 147,202 | 0 | 0 | 0 |
| EURO_GOVERNMENT_FINANCE | CHANGES | 6,086,437 | 2,263,500 | 3,822,937 | 28,799 | 0 |
| EURO_CONSUMER_PRICES | EXACT | 6,548,663 | 6,548,663 | 0 | 0 | 0 |
| EURO_FRAUD_LOSSES | EXACT | 198 | 198 | 0 | 0 | 0 |
| EURO_NATIONAL_ACCOUNTS | EXACT | 2,721,359 | 2,721,359 | 0 | 0 | 0 |
| EURO_MFI_INTEREST_RATES | EXACT | 1,594,491 | 1,594,491 | 0 | 0 | 0 |
| EURO_RETAIL_INTEREST_RATES | EXACT | 8,798 | 8,798 | 0 | 0 | 0 |
| EURO_PAYMENT_SYSTEM_TRANSACTIONS | EXACT | 103,563 | 103,563 | 0 | 0 | 0 |

Summary: 12 exact contracts, four changed contracts, one blocked contract and
zero database writes. The aggregate 3,899,962 planned inserts and 3,843,131
planned updates include the blocked Direct Debits actions and must not be
interpreted as an approved migration.

The v0.6.7 full-period guard adds `unsafe_time_period_type` to the Direct
Debits blockers. Its source uses annual, semiannual and quarterly periods, but
the target stores `time_period` as `YEAR`.

## Memory Correction

The first Balance Sheet Items plan exposed a MySQL Connector behavior:
SQLAlchemy's `stream_results=True` still selected a buffered driver cursor, so
the driver attempted to materialize millions of target rows and raised
`MemoryError`.

The target reader now selects `cursor(buffered=False)` for MySQL Connector and
fetches at most 5,000 tuples at a time. Other SQLAlchemy drivers retain streamed
execution with the same maximum buffer. The production-scale Balance Sheet
Items plan then completed against 7,812,208 target rows.

## Interpretation And Next Gates

- `EXACT` means the registered source and target are fully idempotent.
- `CHANGES` means the plan has no structural blocker, not that it is approved.
- `BLOCKED` means apply mode rejects the plan before opening a write transaction.
- Direct Debits no longer has an unexplained key revision. Its controlled
  shadow rebuild and promotion replaced the lossy `YEAR` target with the
  validated `VARCHAR(20)` history while retaining the former table for rollback.
- Government Finance is a 3,822,937-row source-universe expansion and requires
  a separate capacity review, scoped backup and controlled migration decision.
- Card Payments, Bank Lending Survey and Balance Sheet Items completed their
  old-snapshot precision review and fresh-snapshot staging. New scoped backups,
  a withdrawn-key retention decision and controlled shadow plans are required
  before any current action can be authorized.

Version v0.7.0 completed the separately authorized Direct Debits promotion. Its
latest plan is exact and idempotent with 121,564 unchanged rows, zero actions,
zero target-only rows and zero blockers. The consolidated 17-contract baseline
is now 13 exact, four with reviewed changes and zero blocked. The live schema
audit classifies all 17 contracts as write-ready. See
`EURO_DIRECT_DEBITS_REMEDIATION.md` and `EURO_DIRECT_DEBITS_SWAP.md`.
