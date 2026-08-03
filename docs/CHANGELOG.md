# Changelog

All notable changes to this project will be documented here.

---

## [v0.5.1] - 2026-08-03 - Treasury Source Identity and Provenance

### Added

- Executable source contracts for every configured market asset, including provider, identifier, URL, frequency, acquisition method and OHLC expectation.
- Official Federal Reserve H.15 downloader and parser for `RIFLGFCY02_N.B` / FRED `DGS2`.
- Dry-run-first official-source refresh command and a reversible Treasury identity migration tool.
- US3M as a separate analytical asset for Yahoo `^IRX`, the 13-week Treasury bill yield.
- Source provider, series identifier and verification status in Data Quality outputs.

### Corrected

- Reclassified the 16,600-row history previously labelled US2Y after an exact overlap test confirmed it was Yahoo `^IRX`.
- Replaced US2Y with 12,537 official two-year constant-maturity observations from 1976-06-01 through 2026-07-30.
- Preserved native Yahoo OHLC for US3M and left official US2Y OHLC empty in storage so the analytical engine identifies it as synthetic.

### Safety

- Verified a 1,482,349-byte SQL backup containing structure and data before database writes.
- Retained the pre-migration SQL table and an external copy of the original CSV.
- Built and validated a shadow table before the atomic `US2Y`/`US3M` rename; no source rows were deleted.

### Validation

- Passed 85/85 deterministic tests, parsed 194 active Python files and completed `pip check` without broken requirements.
- Loaded and recalculated 38/38 configured assets with database writes disabled.
- Rendered 9/9 Streamlit pages without uncaught exceptions and exercised US2Y, US3M and Data Quality in a real browser.
- Audited 38 assets, 703 correlation pairs and 66 events with no duplicate-date assets, invalid-price assets or load errors.
- Downloaded and validated the official H.15 US2Y package in dry-run mode without writing CSV or SQL data.

---

## [v0.5.0] - 2026-08-03 - Controlled Market Data Synchronization

### Added

- Idempotent CSV-to-SQL planning and single-asset synchronization with dry-run as the default.
- Locale-aware price, volume and date parsing, including malformed STOXX600 row recovery.
- Scoped credential-safe `mysqldump` backup tooling with SHA-256 verification.
- Reversible shadow-table remediation with an atomic multi-table rename and retained SQL backups.
- Daily observation normalization before technical calculations and data loading.

### Changed

- Centralized all 37 market CSV paths through `PROJECT_MARKET_CLEAN_DIR`.
- Converted the global asset runner to SQL-only validation with database writes disabled.
- Removed implicit CSV imports from the remaining core asset execution paths.
- Consolidated EURO, YUAN, LIBRA and SSECOMPOSITE to one observation per date.
- Rebuilt SP500 from its source CSV to correct a confirmed one-day legacy shift.
- Added unique daily keys to SP500, GOLD, DXY, EURO, YUAN, LIBRA and SSECOMPOSITE.
- Imported 158 missing STOXX600 rows, restored 80 BTC market-cap values and corrected 4,679 SSE decimal-volume values.

### Validation

- 78/78 deterministic unit tests pass.
- 187 active Python files parse successfully; `pip check` passes.
- 37/37 assets pass the SQL-only calculation validator.
- 9/9 Streamlit pages render without uncaught exceptions.
- The post-remediation audit reports zero duplicate assets.
- Nine reviewed tables are idempotent against their current CSV sources.

---

## [v0.4.3] - 2026-07-31 - Full-Row Duplicate Classification

### Added

- Separate classifications for duplicate observation keys, base-value conflicts and full-row conflicts.
- Full-row variant counts, exact full-row surplus counts and conflicting-column details for each duplicated date.

### Improved

- The read-only legacy audit now loads every table column instead of assuming matching price and volume implies an identical SQL row.
- Duplicate detail is calculated once and reused by the summary to avoid repeated analysis.

### Validation

- 63/63 deterministic unit tests pass.
- All 36,732 duplicate-date groups have matching price and volume values.
- 36,729 groups contain differences in technical indicator columns and require a controlled keep/recalculation policy.
- 173,633 rows are exact full-row copies; 210,364 rows are surplus observations when preserving one record per date.
- No SQL writes or database mutations were executed.

---

## [v0.4.2] - 2026-07-31 - Legacy Import Safety

### Added

- Centralized legacy CSV normalization, validation and in-memory date deduplication.
- Read-only import plans that classify source rows as insert, update or unchanged.
- Duplicate-group previews for EURO, YUAN, LIBRA and SSECOMPOSITE with identical/conflicting value classification.
- Git-ignored local CSV and JSON diagnostic outputs under `audit_outputs/import_dry_runs/`.

### Improved

- Disabled automatic base CSV imports in the four affected legacy asset scripts.
- Replaced direct import entry points with the explicit `--dry-run-import` preview option.
- Removed duplicated CSV parsers and unreachable direct `INSERT` code from those scripts.

### Validation

- 62/62 deterministic unit tests pass.
- Live read-only diagnostics confirmed that the four affected tables have no indexes.
- All 36,732 duplicate-date groups contain identical price and volume values; no base-value conflicts were found.
- 210,364 surplus observations by date were identified across the four tables without changing database rows or schemas.
- No SQL writes, migrations, CSV imports or database mutations were executed.

---

## [v0.4.1] - 2026-07-31 - Data Remediation Diagnostics

### Added

- Asset freshness report with configured source file, responsible updater and overdue days.
- Duplicate-date group counts, affected date range and maximum rows per date.
- Explicit non-positive-price review status for historically valid exceptions such as WTI on 20 April 2020.
- Prioritized, non-destructive remediation tasks in Streamlit and audit exports.
- Pairwise common observations, common period, coverage ratio, confidence classification and Fisher 95% confidence intervals.
- Automatic archival of the previous local audit ZIP before a new audit is written.

### Improved

- Pair correlations now calculate each asset's returns on its native observation sequence before same-date alignment.
- Multi-asset loaders no longer forward-fill by default.
- Zero values remain valid for yields and stress series while zero market prices remain invalid.
- Data Quality and Correlations pages expose sample quality alongside analytical results.

### Validation

- 56/56 deterministic unit tests pass.
- Read-only audit loaded 37 assets, 666 pairs and 66 events without database writes.
- Correlation confidence distribution: 457 high, 60 moderate, 148 low and 1 insufficient pair.
- No SQL writes, migrations, CSV importers or database mutations were executed.

---

## [v0.4.0] - 2026-07-31 - Analytical Engine v2

### Added

- Per-asset financial metadata for asset class, calendar policy, source frequency and annualization.
- Row-level native/synthetic OHLC provenance and native-data preservation.
- Read-only Data Quality and rule-based Market Regimes pages.
- Event date precision, event detail and recovery analysis.
- Observation-based macro alignment without future-value leakage.
- Independent financial reference tests for indicators, events, BTC cycles, macro alignment and data quality.

### Improved

- Centralized technical preparation and aligned volatility annualization to each asset's frequency.
- Reimplemented ATR and ADX with Wilder smoothing.
- Changed rolling correlation windows to pairwise valid observations.
- Added explicit multi-asset load reports instead of silent failures.
- Hardened news imports against import-time loops, missing timeouts and unintended SQL activity.
- Normalized the Streamlit interface and public documentation to English.

### Validation

- 48/48 unit tests pass.
- 9/9 Streamlit pages pass smoke validation.
- The read-only audit loaded 37 assets, evaluated 666 correlation pairs and classified 66 historical events.
- No SQL writes, migrations, CSV importers or database mutations were executed during the upgrade.
- The local audit baseline is excluded from Git; its SHA-256 is `8BF5A15AC44043E567442E7522626B15F4321B5CB4C449CA081E5ABD9C656531`.

---

## [v0.3.1] - Streamlit Modularization and GitHub Readiness

### Added

- Modular Streamlit page routing under `app_pages/`.
- Dashboard view modules under `dashboard/`.
- Calculation services under `services/`.
- Unit tests for indicators, correlations, event services, data access and asset/risk services.
- GitHub Actions workflow for Python checks.

### Improved

- Reduced `streamlit_app.py` to routing, cache wrappers and dependency composition.
- Moved event-study, BTC cycle, asset risk, technical signal, export and read-only data-access logic into focused modules.
- Kept SQL writes opt-in and out of dashboard runtime paths.
- Strengthened GitHub hygiene with `.env`, venv, datasets, SQL dumps, exports and secrets ignored.

### Validation

- Streamlit import validation passes in bare mode.
- Unit test suite passes with `python -m unittest discover -s tests`.
- No `.env`, virtual environment folders, datasets or SQL dumps are tracked by Git.

---

## [v0.1.0] - Initial Core System

### Added

- CSV ingestion pipeline
- MySQL integration
- Technical indicators
- Plotly dashboards
- Manipulation heuristics
- Power BI exports

### Features

- RSI
- Stochastic RSI
- MACD
- EMA
- ATR
- ADX
- CCI
- OBV
- Bollinger Bands

### Detection Systems

- Pump/Dump detection
- Spoofing heuristics
- Volatility anomaly detection

---

## [v0.2.0] - Modular Refactor

### Added

- Modular architecture
- `config.py`
- `database.py`
- `indicators.py`
- `risk_detection.py`
- `charts.py`
- `asset_config.py`

### Improvements

- Reduced monolithic structure
- Improved code organization
- Improved scalability
- Prepared architecture for multi-asset support
- Added advanced indicators calculated only in DataFrame

### Documentation

- `README.md`
- `project_structure.md`
- `TODO.md`
- `requirements.txt`
- `.gitignore`
- `STREAMLIT_ROADMAP.md`

---

## [v0.2.1] - Multi-Asset Script Stabilization

### Added

- Standardized processing pattern across all main asset scripts
- Added optional SQL update mode using `UPDATE_SQL`
- Added fast in-memory calculation mode for indicators and manipulation flags
- Added `run_all_assets.py`
- Added `ASSETS_STATUS.md`

### Adapted Asset Scripts

- `main.py` / BTC
- `sp500.py`
- `stoxx600.py`
- `ftse100.py`
- `gold.py`
- `dollaramericano.py` / DXY
- `euro.py`
- `yuan.py`
- `libra.py`
- `ssecomposite.py`

### Improvements

- Avoided unnecessary mass SQL updates by default
- Improved execution speed of asset scripts
- Centralized indicator calculation through `indicators.py`
- Centralized manipulation detection through `risk_detection.py`
- Centralized chart generation through `charts.py`
- Reduced duplicated indicator logic inside individual asset scripts
- Preserved asset-specific CSV cleaning logic where needed
- Improved safety by keeping advanced indicators in memory only

### Validation

- All 10 main asset scripts executed successfully through `run_all_assets.py`
- Latest validation result:

```text
Total scripts: 10
Success: 10
Errors: 0
Missing: 0



Fixes
Fixed encoding handling in run_all_assets.py when reading subprocess output on Windows
Reduced console output decoding issues caused by special characters and emojis
Preserved compatibility with current MySQL setup

Known Warnings
Some scripts still show pandas warnings when using pd.read_sql() with raw MySQL connector connections
These warnings are not critical and do not stop execution

Known Limitations
Asset scripts are still structurally duplicated
SQL update mode still performs row-by-row updates
Advanced indicators are not yet stored in SQL
Charts are functional but not yet fully optimized or customizable
Intermarket analysis is not yet implemented
Streamlit dashboard is not yet implemented

Planned
v0.3.0
Generic asset processor
Improved asset_config.py
Multi-asset engine
SQLAlchemy migration for cleaner database reads
SQL optimization
Optional chart display mode
Optional HTML chart export
Logging improvements

v0.4.0
Database schema documentation
Macro/FED/EU ingestion cleanup
Event/news layer documentation
Power BI export refactor
Intermarket analysis preparation
Feature engineering optimization

v0.5.0
Streamlit dashboard
Market overview page
Technical indicators page
Risk signals page
Macro events page
Intermarket analysis page

v0.6.0
Machine learning preparation
Dataset normalization
Regime detection
Clustering
Anomaly detection
Feature importance
Temporal validation
