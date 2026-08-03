# Controlled Macro Import Safety

Version 0.5.6 places all 11 FED and 17 EURO/ECB source files behind one explicit
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

All 11 FED tables now have a unique `observation_date` key and pass the
write-readiness check:

- `fed_federal_funds_rate`
- `fed_m2`
- `fed_total_assets`
- `fed_reserve_bank_credit`
- `fed_deposits`
- `fed_bank_credit`
- `fed_loans_leases`
- `fed_securities_bank_credit`
- `fed_consumer_loans_credit_cards`
- `fed_credit_card_delinquency`
- `fed_charge_off_rate_credit_cards`

The last four keys were added by the v0.5.3 controlled migration after a
scoped SQL backup, zero-null and zero-duplicate checks, and post-migration row
count/range validation. The reusable command is:

```powershell
python project_scripts/diagnostics/remediate_fed_macro_keys.py
```

It is read-only unless `--apply`, the verified backup path and the exact
confirmation phrase are provided together.

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

The v0.5.4 baseline audit classified the schemas as:

- five `write_contract_ready` tables with a safe period type and composite key;
- six `key_addition_candidate` tables with no null or duplicate business keys;
- six `rebuild_required` tables where adding an index in place would preserve
  corrupted or historically truncated data.

`euro_atm_pos_transactions` cannot receive a unique key in place: semiannual
periods such as `2022-S1` and `2022-S2` were stored in an integer year column,
creating 107,296 duplicate business-key groups. Five further tables used
`key_code` as their only key and retained approximately one period per series.

Use the canonical read-only command before any remediation:

```powershell
python project_scripts/diagnostics/audit_euro_macro_schema.py --deep --output-dir audit_outputs/euro_schema_audit
```

No EURO table is changed by this command. The detailed baseline and proposed
shadow-table process are documented in `docs/EURO_SCHEMA_AUDIT.md`.

Version v0.5.5 completed six required rebuilds using a verified SQL backup,
isolated shadow tables, full-row source signatures and one atomic swap. Version
v0.5.6 then performed a full-source cardinality audit and rebuilt three further
tables whose stored values were not exact. The current classification is:

- 14 `write_contract_ready` schemas;
- zero `key_addition_candidate` schemas;
- three `rebuild_required` schemas with incomplete target history.

All nine replaced tables remain retained for rollback. General EURO imports are
still blocked until a transactional multidimensional updater handles missing
observations explicitly and passes full-source integration tests. Schema
remediation alone does not enable automatic writes.

## Recovery

The previous importers remain available in Git history at v0.5.1. Local copies
are retained under `tools/legacy/pre_v052/` as `.legacy.txt` files and are
excluded from Git, so they cannot be imported or executed accidentally.
