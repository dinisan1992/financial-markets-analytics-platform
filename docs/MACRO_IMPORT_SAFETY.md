# Controlled Macro Import Safety

Version 0.5.2 places all 11 FED and 17 EURO/ECB source files behind one explicit
import contract. Importing a Python module never opens MySQL or starts loading a
CSV. Running an importer without flags performs a read-only preview.

## Preview Commands

Preview every source contract without SQL access:

```powershell
python project_scripts/ingestion/refresh_macro_sources.py ALL
```

Validate CSV samples and compare the expected business keys with the current SQL
schema, still without writes:

```powershell
python project_scripts/ingestion/refresh_macro_sources.py ALL --check-sql
```

Use `--full-scan` deliberately. Several EURO source files are larger than 1 GB,
so the default reads only a bounded sample.

Every FED write performs a complete source preflight first. Invalid rows or
duplicate observation dates block the operation, and all write chunks share one
database transaction so a failure cannot leave a partially imported file.

## FED Write Contract

Seven FED tables currently have a unique `observation_date` key and pass the
write-readiness check:

- `fed_federal_funds_rate`
- `fed_m2`
- `fed_reserve_bank_credit`
- `fed_deposits`
- `fed_loans_leases`
- `fed_securities_bank_credit`
- `fed_credit_card_delinquency`

Four FED tables remain blocked because `observation_date` is not unique:

- `fed_total_assets`
- `fed_bank_credit`
- `fed_consumer_loans_credit_cards`
- `fed_charge_off_rate_credit_cards`

A write-ready FED import still requires all three safeguards:

1. `--update-sql`
2. `--confirm-table` with the exact configured table name
3. `--backup-file` pointing to a non-empty SQL dump containing both the table
   structure and its data

No multi-table bulk SQL write is supported.

## EURO Write Contract

All 17 EURO writes are intentionally blocked. These files are multidimensional,
and a safe import requires complete source-to-table mappings plus a unique
`(key_code, time_period)` business key.

Five tables already expose that composite key but remain blocked until their
complete mappings are independently validated. The other 12 require schema
remediation as well. No EURO table is changed automatically by the preview.

## Recovery

The previous importers remain available in Git history at v0.5.1. Local copies
are retained under `tools/legacy/pre_v052/` as `.legacy.txt` files and are
excluded from Git, so they cannot be imported or executed accidentally.
