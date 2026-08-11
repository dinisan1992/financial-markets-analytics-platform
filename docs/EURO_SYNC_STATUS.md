# EURO Synchronization Status

Version: v0.6.7

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

## Results

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
- Direct Debits no longer has an unexplained key revision. A complete key
  comparison explains all 77,025 source-only and 31,108 target-only rows as
  the result of lossy `YEAR` storage. It requires a controlled shadow rebuild,
  not transactional upsert against the current table.
- Government Finance is a 3,822,937-row source-universe expansion and requires
  a separate capacity review, scoped backup and controlled migration decision.
- Card Payments, Bank Lending Survey and Balance Sheet Items require field-level
  mismatch review before any write authorization.

No active-data remediation is part of v0.6.7. The diagnostic and rebuild plan
are read-only; see `EURO_DIRECT_DEBITS_REMEDIATION.md`.
