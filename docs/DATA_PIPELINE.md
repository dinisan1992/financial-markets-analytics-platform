# Market Data Pipeline

## Purpose

Market CSV files are the local source of truth for raw observations. MySQL stores one observation per asset and calendar date. Technical indicators, volatility, drawdown and risk signals are recalculated by the current analytical engine instead of trusting stale indicator columns from older imports.

## Directory

All configured market assets use `PROJECT_MARKET_CLEAN_DIR`. The default is:

```text
new_market_data/clean
```

The location can be changed in the private `.env` file without editing source code.

## Safe Refresh

1. Download the new CSV from the documented source.
2. Replace or update the matching file in the configured market-data directory.
3. Preview the change:

```powershell
python project_scripts/assets/sync_market_data.py ASSET_KEY
```

4. Review source rows, invalid rows, duplicate source dates, planned inserts, planned updates and the unique-key status.
5. Create a scoped database backup when the plan is material.
6. Apply one reviewed asset:

```powershell
python project_scripts/assets/sync_market_data.py ASSET_KEY --update-sql
```

7. Run the same dry-run again. A successful idempotent refresh reports zero planned inserts and updates.
8. Run the data audit and SQL-only validator.

## Safety Rules

- Dry-run is the default.
- `--all --update-sql` is rejected; bulk writes are disabled.
- Table and column identifiers are validated before SQL construction.
- SQL writes are refused when `snapped_at` is not protected by a unique key.
- Source duplicate dates are collapsed deterministically before planning.
- Source null values do not overwrite existing non-null values.
- Inserts and updates run in a transaction and only raw source columns are written.
- Dashboard, audit and global validation paths never import CSV or mutate SQL.

## Database Remediation

The v0.5.0 market-table remediation used:

```powershell
python project_scripts/diagnostics/backup_market_tables.py --output-dir PATH
python project_scripts/diagnostics/remediate_market_tables.py
python project_scripts/diagnostics/remediate_market_tables.py --apply --backup-file BACKUP.sql
```

The remediation script creates parallel tables, validates row counts and raw values, adds unique daily keys, and performs one atomic multi-table rename. Replaced tables are retained locally with versioned names until a later manual cleanup decision.

## Scope Boundary

This workflow currently governs the 38 market assets. The separate FED and EURO/ECB layer is governed by `macro_import_manifest.py`, `services/macro_import_service.py` and `project_scripts/ingestion/refresh_macro_sources.py`. Its default is a read-only preview. A FED write requires one named import, `--update-sql`, exact table confirmation, a verified table-level SQL backup and a unique business key. EURO refreshes use the separate default-read-only `project_scripts/ingestion/sync_euro_macro.py` planner. Version v0.6.8 preserves the 17-contract planning baseline but classifies 16 schemas as write-ready and Direct Debits as a controlled rebuild because its `YEAR` target column cannot preserve semiannual and quarterly periods. The Direct Debits scoped backup gate is complete; production use still requires a genuinely newer reviewed CSV and all normal guards, while Direct Debits additionally requires a validated `VARCHAR(20)` shadow and separate build/swap authorization.

The canonical provider, identifier, URL, native frequency and OHLC expectation
for each market asset are defined in `market_source_manifest.py` and documented
in `docs/DATA_SOURCES.md`. A local filename alone must never be used to infer a
financial series identity.
