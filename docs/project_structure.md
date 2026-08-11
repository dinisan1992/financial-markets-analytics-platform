# Project Structure

This document describes the current repository organization after the cleanup pass.

## Root

The root is reserved for entry points and shared modules:

- `streamlit_app.py` - main Streamlit dashboard.
- `analysis_launcher.py` - terminal menu for running analysis scripts.
- `config.py` - paths, environment variables and database settings.
- `asset_config.py` - market asset metadata and paths.
- `macro_config.py` - FED macro indicator metadata.
- `euro_series_config.py` - EURO macro series metadata.
- `database.py` - BTC/core MySQL helpers.
- `indicators.py` - technical indicator calculations.
- `risk_detection.py` - heuristic suspicious behaviour flags.
- `charts.py` - shared Plotly chart helpers.
- `macro_data_loader.py` - FED macro/market loading helpers.
- `euro_data_loader.py` - EURO macro/market loading helpers.
- `README.md`, `PROJECT_STATUS.md`, `requirements.txt`, `.env.example`, `.gitignore`, `VERSION`.

## Dashboard

`dashboard/` contains modules used by `streamlit_app.py`:

- `asset_charts.py`
- `asset_indicators.py`
- `correlation_charts.py`
- `correlation_data.py`

## Project Scripts

Runnable scripts are organized under `project_scripts/`:

- `project_scripts/assets/` - per-asset processing scripts and `run_all_assets.py`.
- `project_scripts/analysis/` - selectors, market analysis, macro analysis, validation and reports.
- `project_scripts/diagnostics/` - one-off diagnosis and cleanup scripts.
- `project_scripts/ingestion/` - controlled FED/EURO source preview and synchronization entry points.

Each moved script includes a small bootstrap that adds the repository root to `sys.path`, so imports such as `from config import ...` still work when the script is launched directly.

Market data maintenance entry points:

- `project_scripts/assets/sync_market_data.py` - dry-run or explicit single-asset CSV synchronization.
- `project_scripts/assets/run_all_assets.py` - SQL-only validation for all configured assets.
- `project_scripts/diagnostics/backup_market_tables.py` - scoped SQL backup without exposing credentials.
- `project_scripts/diagnostics/acceptance_test_euro_sync_mysql.py` - isolated backup, commit, idempotency and rollback acceptance drill.
- `project_scripts/diagnostics/consolidate_euro_sync_status.py` - read-only consolidation of saved EURO plans into local CSV/JSON evidence.
- `project_scripts/diagnostics/backup_euro_table.py` - scoped EURO structure-and-data backup on a separate physical volume.
- `project_scripts/diagnostics/verify_euro_table_backup.py` - exact-confirmation restore and fingerprint verification in a generated isolated schema.
- `project_scripts/diagnostics/diagnose_euro_direct_debits.py` - SELECT-only diagnosis of Direct Debits period-key loss.
- `project_scripts/diagnostics/plan_euro_direct_debits_rebuild.py` - read-only Direct Debits shadow DDL, swap and rollback plan with no write mode.
- `project_scripts/diagnostics/build_euro_direct_debits_shadow.py` - build-only v0.6.9 Direct Debits shadow loader with pinned inputs and no swap mode.
- `project_scripts/diagnostics/swap_euro_direct_debits.py` - separately confirmed v0.7.0 atomic promotion with retained-table rollback.
- `project_scripts/diagnostics/remediate_market_tables.py` - reversible shadow-table remediation.
- `services/market_data_sync_service.py` - shared parsing, planning, key checks and transactional upsert logic.
- `project_scripts/ingestion/sync_euro_macro.py` - default-read-only EURO synchronization planner.
- `services/euro_sync_service.py` - bounded EURO action planning, guarded upsert and in-transaction validation.
- `services/euro_sync_status_service.py` - lightweight status and freshness view over saved EURO plan reports.
- `services/euro_direct_debits_diagnostic_service.py` - complete source/target period-alignment evidence.
- `services/euro_direct_debits_remediation_service.py` - inspectable rebuild plan and mandatory safety gates; no execution path.
- `services/euro_backup_restore_service.py` - reusable active/restore fingerprints, schema comparison and isolated cleanup controls.
- `services/euro_direct_debits_shadow_service.py` - pinned Direct Debits source/backup gates, shadow-only build and complete before/after validation.
- `services/euro_direct_debits_swap_service.py` - Direct Debits promotion checks, retained checkpoint and post-swap evidence.

## Tools

`tools/` contains import/maintenance utilities:

- `tools/fed/` - FED CSV import scripts.
- `tools/eu/` - EURO/ECB CSV import scripts.
- `tools/sql/` - SQL import utilities.
- `tools/news/` - news/API import scripts.
- `tools/legacy/` - old standalone import scripts kept for reference.

## Data And Outputs

The following folders are intentionally ignored by Git:

- `data/`
- `new_market_data/`
- `outputs/`
- `archive/`

Generated root CSV reports were moved to `outputs/reports/`.
Generated project tree text files were moved to `outputs/project_tree/`.

## GitHub Safety

The repository excludes private/local files:

- `.env` and `.env.*`
- `.streamlit/secrets.toml`
- CSV/XLS datasets
- SQL/database dumps
- compressed backups
- local virtual environments
- generated reports and outputs

Use `.env.example` as the public template and keep real credentials/API keys only in `.env`.
