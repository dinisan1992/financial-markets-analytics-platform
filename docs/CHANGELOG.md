# Changelog

All notable changes to this project will be documented here.

---

## [v0.6.5] - 2026-08-11 - Isolated MySQL Acceptance

### Added

- A default-read-only MySQL acceptance command for `EURO_FRAUD_LOSSES`.
- Strict generated-schema validation, explicit execution confirmation and an
  external backup-directory requirement.
- Deterministic active-table fingerprints before and after the drill.
- Controlled insert, update, authoritative-null and idempotency fixtures.
- A test-only MariaDB trigger that forces post-write validation failure and
  proves rollback without modifying the synchronization service.

### Validation

- Restored a verified 110,420-byte scoped backup into an isolated schema.
- Matched all 198 restored rows to the active full-row SHA-256 fingerprint.
- Committed one insert and two updates only after complete in-transaction
  validation, then confirmed a zero-write reapply.
- Forced a post-write mismatch and confirmed all 198 rows retained their
  original fingerprint after rollback.
- Confirmed zero writes to the active schema and removed the temporary schema.
- Passed 179/179 deterministic tests and parsed 231/231 active Python files.

---

## [v0.6.4] - 2026-08-11 - Guarded EURO Transactional Synchronization

### Added

- A one-contract EURO synchronization planner backed by the existing bounded SQLite fingerprint store.
- Explicit counts and samples for inserts, updates, unchanged observations and target-only rows.
- A dedicated `sync_euro_macro.py` command that is read-only unless `--apply`, a verified scoped backup and an import-specific confirmation are supplied together.
- Selective upserts for planned insert/update keys only, followed by a complete source-to-target comparison inside the same transaction.
- Progress reporting for long source, target and write scans.

### Policies and Safety

- Source values, including explicit source nulls, are authoritative for matching business keys.
- Source null keys, invalid numerics, duplicate keys and missing unique target keys block synchronization.
- Target-only rows block synchronization for manual review; automatic deletes are disabled.
- Source-file size and modification time are checked before, during and after the transaction.
- A failed post-write comparison raises before commit, rolling back the complete operation.
- No production MySQL write was executed in this release.

### Validation

- Passed 172/172 deterministic tests and parsed 229/229 active Python files.
- Proved selective insert/update behavior, no-op idempotency, authoritative-null handling and forced rollback with isolated SQLite fixtures.
- Passed read-only live plans for 198 fraud observations and 1,594,491 MFI observations with zero actions, blockers or differences.
- Preserved 38/38 SQL asset recalculations, 9/9 Streamlit page renders and dependency integrity.
- Synchronized the root `VERSION` file with `PROJECT_VERSION` and added a release-consistency test.

---

## [v0.6.3] - 2026-08-11 - Complete EURO Source Remediation

### Corrected

- Rebuilt MFI interest rates, national accounts and consumer prices one table at a time from the registered CSV sources.
- Promoted non-key text dimensions to `TEXT` in large shadows so long ECB descriptions are preserved without truncation.
- Added a 1.5 safety factor to large-shadow capacity estimates.
- Corrected the EURO series validator's error status, output isolation, fail-on-error exit code and database-write reporting.

### Database Outcome

- Active SQL now matches 10,864,513 source rows exactly: 1,594,491 MFI, 2,721,359 national-account and 6,548,663 consumer-price observations.
- The post-migration comparison found zero missing, extra, null-key, duplicate-key, invalid-numeric or full-row hash-mismatched rows.
- The deep schema audit classifies 17/17 EURO contracts as write-contract ready and confirms 16/16 configured series are available.
- All three former active tables remain retained under `pre_v062` names with documented atomic rollback statements.
- Three verified table-scoped structure-and-data backups remain on a separate physical volume; SQL dumps and local audit artifacts are excluded from Git.
- One failed 17,250-row national-account shadow remains retained for forensic review and is not part of the active application schema.

### Validation

- Passed 159/159 deterministic tests and parsed 225/225 active Python files.
- Passed `pip check`, 38/38 SQL-only asset recalculations, 9/9 Streamlit page renders and HTTP 200 health.
- Passed 12/12 active EURO/market pair checks; four intentionally disabled fraud series were reported as skipped.
- General EURO refresh writes remain disabled pending the transactional multidimensional updater.

---

## [v0.6.2] - 2026-08-11 - Large EURO Rebuild Safety Workflow

### Added

- A reusable SQLite fingerprint store for exact, disk-backed source and target comparison.
- Memory-bounded shadow loading and pre-swap validation for consumer prices, national accounts and MFI interest rates.
- One-table-only `v062` build and swap services with import-specific confirmation phrases.
- A read-only plan and capacity-preflight CLI with exact shadow, retained, failed, swap and rollback details.
- A dedicated one-table backup command using streaming `mysqldump`, SHA-256 and structure-and-data verification.
- Eighteen deterministic tests for cross-chunk duplicates, comparison semantics, temporary-store cleanup, confirmation guards, capacity checks, CLI safety and backup scope.

### Capacity Findings

- MFI interest rates require an estimated 1,160,347,243-byte shadow and 154,017,792-byte comparison store.
- National accounts require an estimated 1,385,763,282-byte shadow and 352,198,656-byte comparison store.
- Consumer prices require an estimated 2,346,474,969-byte shadow and 600,059,904-byte comparison store.
- All three read-only preflights passed on the current machine with a 5 GiB operating reserve.
- Backup capacity is intentionally excluded from these estimates and a separate physical volume is recommended.

### Validation and Safety

- Passed 155/155 deterministic tests and parsed 224/224 active Python files.
- Existing earlier rebuild services retain their default in-memory behavior; the bounded path is opt-in and restricted to one large table.
- No backup, shadow, retained table, swap, CSV change, SQL write or database mutation was performed.

---

## [v0.6.1] - 2026-08-11 - Memory-Bounded EURO Validation

### Added

- A read-only full-row validator for consumer prices, national accounts and MFI interest rates.
- A temporary SQLite comparison store keyed by `(key_code, time_period)` so memory remains bounded by the configured CSV/SQL chunk size.
- Separate counts and samples for missing source rows, extra target rows, hash mismatches, null keys, invalid numerics and duplicate keys.
- A diagnostic CLI that writes per-table JSON plus consolidated JSON/CSV reports under Git-ignored `audit_outputs/`.
- Seven deterministic tests covering exact matches, missing/extra/mismatched rows, duplicates, invalid values, bounded chunks, CLI defaults and read-only target statements.

### Findings

- Compared 10,864,513 source rows with 1,389,000 active SQL rows in 464 seconds using 50,000-row chunks.
- Confirmed 9,475,513 source rows absent from SQL and zero SQL keys absent from source.
- Identified 313,682 full-row mismatches among overlapping keys: 9,456 consumer-price, 302,628 national-account and 1,598 MFI rows.
- Confirmed zero null business keys, duplicate business keys and invalid numeric rows in both source and target for all three contracts.
- Temporary comparison stores reached approximately 572, 336 and 147 MiB and were deleted after each table.

### Safety

- The target-database test proves that the validator emits only read statements against SQL.
- The live audit reports `database_write_performed=false`; no CSV, SQL row, index, schema or table was changed.
- The three controlled rebuilds remain blocked pending disk-backed shadow validation, scoped backups, capacity review and explicit approval.

---

## [v0.6.0] - 2026-08-03 - Analytical Semantics and Financial Properties

### Improved

- Normalized rolling return entropy to a documented zero-to-one Shannon scale.
- Replaced raw-volume liquidity stress with a unit-invariant difference between rolling volatility and volume z-scores.
- Disabled liquidity stress for assets without expected, meaningful volume and exposed availability explicitly.
- Added native versus approximate-synthetic quality provenance for ATR, ADX and CCI.
- Replaced active spoofing-like terminology with the observable `high_volume_candle_rejection` signal.
- Retained `possible_spoofing` and related summary aliases only for compatibility with historical exports and notebooks.
- Made flat-series CCI and volume-free OBV explicitly unavailable instead of relying on epsilon arithmetic or implicit missing propagation.

### Validation

- Passed 130/130 deterministic unit tests.
- Parsed 211/211 active Python files and completed `pip check` without broken requirements.
- Recalculated 38/38 configured SQL assets with database writes disabled.
- Rendered 9/9 Streamlit pages through `AppTest` without uncaught exceptions; the running server health endpoint returned HTTP 200.
- Added property tests for RSI and ADX bounds, Bollinger ordering, normalized entropy, correlation symmetry and Base 100 anchoring.
- Added regression tests for volume-unit invariance, no-volume behaviour, OHLC-derived indicator quality and event-date direction.
- No CSV import, SQL write, schema migration or database mutation was performed.

---

## [v0.5.6] - 2026-08-03 - EURO Source Completeness and Exact Rebuilds

### Added

- A full-source row-cardinality baseline for the six remaining EURO schemas.
- Version-aware shadow, retained and failed-table names so later migrations do not collide with v0.5.5 recovery tables.
- A backup-gated exact-rebuild command for fraud losses, retail interest rates and payment-system transactions.
- Seven deterministic tests for v0.5.6 confirmation guards, versioned SQL, legacy auto-increment removal, incomplete-history classification and live status-file refresh.

### Corrected

- Rebuilt three source-complete tables from 112,559 observations with `DECIMAL(38,12)`, non-truncated long text and a composite `(key_code, time_period)` primary key.
- Reclassified consumer prices, national accounts and MFI interest rates as controlled rebuilds after identifying 9,475,513 source observations absent from MySQL.
- Improved the EURO schema classification from 11 ready / 6 candidates / 0 rebuilds to 14 ready / 0 candidates / 3 rebuilds.

### Safety

- Verified a 48,858,895-byte structure-and-data SQL dump before creating shadows.
- Compared every mapped source value after SQL storage; all three active tables have zero missing, extra or mismatched rows.
- Retained all former tables under versioned `pre_v056` names and recorded an atomic rollback statement.
- Deferred the three large rebuilds until validation is memory-bounded and migration capacity is rechecked.

---

## [v0.5.5] - 2026-08-03 - EURO Historical Schema Remediation

### Added

- A backup-gated EURO rebuild service with separate build and atomic-swap confirmation phrases.
- Full-row SHA-256 validation between six source CSVs and their shadow tables.
- Packet-bounded inserts, retained-table rollback and automatic post-swap rollback on validation failure.
- Seven deterministic tests for backup scope, confirmations, names, row normalization, batching and atomic SQL generation.

### Changed

- Rebuilt six unsafe EURO tables from 1,548,900 source observations using textual period labels and unique `(key_code, time_period)` contracts.
- Recovered 956,717 historical business keys that the previous schemas could not represent correctly.
- Improved the EURO schema classification from 5 ready / 6 candidates / 6 rebuilds to 11 ready / 6 candidates / 0 rebuilds.

### Safety

- Verified a 324,480,219-byte structure-and-data SQL dump before creating any shadow table.
- Compared every mapped value after SQL storage; all six tables reported zero row-hash mismatches, missing rows, null keys and duplicate keys.
- Swapped all six tables in one atomic `RENAME TABLE` statement.
- Retained every original table under a versioned `pre_v055` name; no retained table or source CSV was deleted.

---

## [v0.5.4] - 2026-08-03 - EURO Schema Audit Baseline

### Added

- A reusable read-only auditor for all 17 EURO CSV-to-MySQL contracts.
- Period-pattern and SQL-type checks that distinguish annual, monthly, quarterly, semiannual and dated observations.
- Structured JSON and CSV audit outputs with an explicit no-database-write marker and SHA-256 digest.
- Deterministic tests for source aliases, period classification, lossy SQL types and report safety.

### Findings

- Classified five EURO tables as write-contract ready, six as composite-key candidates and six as requiring controlled rebuilds.
- Confirmed zero null business keys across all 17 tables and duplicate business keys only in `euro_atm_pos_transactions`.
- Identified historical truncation in five key-only tables and lossy semester-to-integer conversion in the ATM/POS table.
- Confirmed 16/16 configured EURO series and 12/12 active EURO/market pairs remain operational.

### Safety

- The audit opened MySQL only for `SELECT` and schema inspection operations.
- No EURO row or schema was inserted, updated, deleted or migrated.
- Raw CSV files and generated audit outputs remain outside Git.

---

## [v0.5.3] - 2026-08-03 - FED Observation-Date Key Remediation

### Added

- A dry-run-first FED key-remediation command with duplicate/null audits, exact confirmation and post-migration validation.
- Five deterministic tests for SQL scope, write guards, backup coverage and rollback output.

### Changed

- Added `uq_observation_date` to `fed_total_assets`, `fed_bank_credit`, `fed_consumer_loans_credit_cards` and `fed_charge_off_rate_credit_cards`.
- Promoted all 11 FED source contracts to write-ready status while preserving explicit backup and `--update-sql` requirements.

### Safety

- Verified a 181,266-byte SQL dump containing structure and data for all four tables before the migration.
- Confirmed zero null dates and zero duplicate-date groups before every schema change.
- Preserved all row counts and date ranges; no source row was inserted, updated or deleted.
- Recorded reviewed `DROP INDEX uq_observation_date` rollback statements for each changed table.

---

## [v0.5.2] - 2026-08-03 - Controlled Macro Import Safety

### Added

- Executable contracts for 11 FED and 17 EURO/ECB source files.
- A shared macro import preview service and one aggregate CLI for header, sample and SQL-key validation.
- Backup validation, exact table confirmation and unique-key enforcement before any FED upsert.
- Deterministic tests for import-time side effects, source coverage, preview calculations and write guards.

### Changed

- Replaced 28 direct importer entrypoints with thin, read-only-by-default wrappers.
- Added full-source FED preflight, invalid/duplicate source blocking and one atomic transaction across all write chunks.
- Preserved the pre-v0.5.2 implementations locally as Git-ignored, non-executable text; the public history remains available in v0.5.1.
- Classified 7 FED imports as write-ready and 4 as blocked by missing unique date keys.
- Blocked all EURO writes pending complete multidimensional mappings; 12 tables also require a unique `(key_code, time_period)` key.

### Safety

- Importing any FED or EURO entrypoint no longer opens MySQL or starts reading a multi-gigabyte CSV.
- No FED or EURO CSV import, SQL write, migration or schema change was performed during this release.

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
