# Controlled Macro Import Safety

Version 0.6.5 places all 11 FED and 17 EURO/ECB source files behind explicit
import contracts. Importing a Python module never opens MySQL or starts loading
a CSV. Running an importer without write flags performs a read-only preview.

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

Bulk and legacy EURO writes remain intentionally blocked. Version v0.6.4 adds
a dedicated one-contract synchronization engine with explicit
multidimensional insert, update and missing-value policies. Its default mode is
a read-only, disk-backed plan:

```powershell
python project_scripts/ingestion/sync_euro_macro.py EURO_FRAUD_LOSSES
```

The plan reports inserts, updates, unchanged rows, target-only rows, source and
target quality blockers, unique-key availability and the exact confirmation
required by apply mode. It never plans a delete.

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
v0.5.6 rebuilt three further tables whose stored values were not exact. Version
v0.6.3 completed the remaining three large rebuilds and exact post-swap audit.
The current classification is:

- 17 `write_contract_ready` schemas;
- zero `key_addition_candidate` schemas;
- zero `rebuild_required` schemas.

All 12 replaced active tables remain retained for rollback. The v0.6.4 apply
path is limited to one explicit import and requires:

1. a write-ready read-only plan;
2. a non-empty table-scoped structure-and-data SQL backup;
3. the exact `APPLY_<IMPORT_KEY>_V064_TRANSACTIONAL_SYNC` confirmation;
4. zero target-only rows, null keys, duplicate keys or invalid numerics;
5. a unique `(key_code, time_period)` target key;
6. exact post-write validation before the transaction can commit.

Source nulls are authoritative, so an explicit blank in the source replaces a
stale target value with SQL `NULL`. Target-only observations block rather than
being deleted. Only keys classified as insert or update are sent to SQL.

The engine passed isolated transactional tests, live read-only planning and the
v0.6.5 MySQL acceptance drill. The drill restored a scoped backup, committed
controlled insert/update/null fixtures, proved zero-write idempotency and forced
a complete rollback in a generated test schema. No active MySQL write was
executed. A future production refresh still requires a newer reviewed source,
a blocker-free plan, a fresh scoped backup and exact apply confirmation.

## Recovery

The previous importers remain available in Git history at v0.5.1. Local copies
are retained under `tools/legacy/pre_v052/` as `.legacy.txt` files and are
excluded from Git, so they cannot be imported or executed accidentally.
