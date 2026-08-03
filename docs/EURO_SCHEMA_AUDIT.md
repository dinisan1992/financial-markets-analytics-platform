# EURO Schema Audit Baseline

Version: v0.5.4

Audit date: 3 August 2026

Database mode: read-only

## Purpose

This audit compares all 17 registered ECB/EURO CSV contracts with their current
MySQL schemas before any data remediation. It inspects source headers and period
samples, SQL columns and types, primary and unique keys, null business keys,
duplicate `(key_code, time_period)` groups and the availability of configured
application series.

The audit command is:

```powershell
python project_scripts/diagnostics/audit_euro_macro_schema.py --deep --output-dir audit_outputs/euro_schema_audit
```

The command performs schema inspection and `SELECT` queries only. Generated
reports are local, Git-ignored artifacts. The baseline JSON records
`database_write_performed: false` and has SHA-256:

`16E2EE216C839E7FA974DE1E64332385EF4F4B37C6559AFDF31C64946B332A35`

## Classification

### Write Contract Ready

These five tables already have a safe time-period type, zero null or duplicate
business keys and a unique `(key_code, time_period)` contract:

- `euro_balance_sheet_items`
- `euro_bank_lending_survey`
- `euro_card_payments`
- `euro_direct_debits`
- `euro_government_finance_statistics`

They remain write-blocked until full-source mapping and transactional importer
tests are completed.

### Composite-Key Candidates

These six tables have compatible period types and no null or duplicate business
keys, but still use an `id` primary key without a unique business key:

- `euro_indices_consumer_prices`
- `euro_losses_due_to_fraud`
- `euro_main_aggregates_national_accounts`
- `euro_mfi_interest_rate_statistics`
- `euro_retail_interest_rates`
- `euro_transactions_payments_systems`

A unique key may be added only after a scoped SQL backup, full duplicate/null
audit and a dry-run migration with exact row-count and range checks.

### Controlled Rebuild Required

These six tables must be reconstructed from the source CSV in isolated shadow
tables. Adding an index to the current table is not a valid repair:

| Table | Source rows | Current rows | Main blocker |
| --- | ---: | ---: | --- |
| `euro_atm_pos_transactions` | 607,291 | 607,291 | Semiannual periods collapsed into integer years; 107,296 duplicate key groups |
| `euro_card_payments_by_merchant_category` | 419,510 | 30,680 | `key_code`-only primary key retained approximately one period per series |
| `euro_composite_indicator_stress` | 142,527 | 42 | `key_code`-only primary key retained approximately one period per series |
| `euro_country_level_financial_stress` | 12,806 | 28 | Monthly source periods mapped to `DATE`; `key_code`-only primary key |
| `euro_credit_transfers` | 218,564 | 36,244 | Annual source periods mapped to `DATE`; `key_code`-only primary key |
| `euro_emoney_payment_transactions` | 147,202 | 24,194 | `key_code`-only primary key retained approximately one period per series |

Every source file in this group has a unique `(KEY, TIME_PERIOD)` business key.
The history loss occurred in the target schema or legacy importer, not in the
reviewed CSV source.

For ATM/POS, all 107,296 duplicated target groups contain two rows and 26,718
groups contain conflicting `obs_value` values. The source contains both annual
and semiannual labels, so the target period must remain textual.

## Application Coverage

- 16/16 configured EURO series are available in MySQL.
- 12/12 active EURO/market pairs load and align successfully.
- HICP series cover approximately 2000 to August/September 2025.
- Configured MFI rate series cover January 2000 to August 2025.
- Four disabled fraud series contain six semiannual observations each.

The current application remains operational because its active HICP and MFI
series are stored in tables outside the rebuild group. This does not make the
six historical-loss tables safe to refresh.

## Controlled Remediation Plan

1. Create a scoped structure-and-data SQL backup for the exact target group.
2. Create shadow tables with textual `time_period` and a unique composite key.
3. Stream source CSVs in bounded chunks into one transaction per table.
4. Validate source and shadow row counts, unique business-key counts, period
   patterns, configured series, value ranges and representative samples.
5. Run application and database-backed integration tests against the shadows.
6. Produce an explicit before/after report and reviewed rollback statements.
7. Swap a table only after user confirmation; retain the original table until
   the complete post-migration audit passes.

No step in this document authorizes an automatic multi-table write or deletion.
