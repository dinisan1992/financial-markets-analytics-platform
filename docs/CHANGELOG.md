# Changelog

All notable changes to this project will be documented here.

---

## [v0.7.1] - 2026-08-11 - Dependency and CI Hardening

### Changed

- Reduced `requirements.txt` from a transitive environment snapshot to eight
  pinned direct runtime dependencies.
- Added `requirements-dev.txt` with pinned Ruff and Coverage tooling.
- Expanded GitHub Actions into a static/import-safety job and a four-environment
  test matrix covering Windows, Linux, Python 3.11 and Python 3.12.
- Added dependency consistency, lint, compile, coverage and coverage-artifact
  checks without requiring database access.
- Established 41% branch coverage across the application, page, dashboard
  and service layers, enforced with a 40% regression floor.
- Removed unused imports and resolved the remaining basic Ruff findings.
- Fixed the missing `get_sqlalchemy_database_url` import in the Power BI BTC
  analysis script.

### Validation

- Passed 207/207 deterministic unit tests, parsed 254/254 active Python files,
  passed Ruff, `pip check`, import safety and
  the 40% coverage gate locally.
- Database writes remained disabled and no database remediation was performed.

---

## [v0.7.0] - 2026-08-11 - Direct Debits Controlled Rebuild

### Added

- A separately confirmed Direct Debits atomic-swap command with no build or
  cleanup mode.
- Optional post-rename and post-hash-removal validators in the shared EURO
  rebuild engine, both covered by automatic rollback.
- Tests proving that the source hash column is removed only after promotion
  validation and that a forced failure executes the inverse atomic rename.

### Database Evidence

- Revalidated the verified backup, reviewed CSV, active-table checkpoint and
  complete 121,564-row shadow before the rename.
- Atomically retained the former active table as
  `euro_direct_debits__pre_v069_20260811_163215` and promoted the validated
  shadow to `euro_direct_debits`.
- Confirmed the new active table has 121,564 unique business keys,
  `time_period VARCHAR(20)`, 31 production columns and no helper hash column.
- Preserved 44,539 annual, 42,039 semiannual and 34,986 quarterly rows.
- Preserved the former table exactly: 75,647 rows and the original full data
  and schema fingerprints remain available for rollback.
- Ran a post-swap synchronization plan with 121,564 unchanged rows, zero
  inserts, updates, target-only rows or blockers.
- Reclassified all 17 EURO schemas as `write_contract_ready`; 16/16 configured
  EURO series remain available.

### Validation

- Passed 205/205 deterministic tests and parsed 253/253 active Python files.
- Passed `pip check`, 38/38 SQL-only asset recalculations, 9/9 Streamlit page
  renders and HTTP 200 application health.

---

## [v0.6.9] - 2026-08-11 - Validated Direct Debits Shadow

### Added

- A build-only Direct Debits command with no swap stage and an exact
  `BUILD_EURO_DIRECT_DEBITS_V069_SHADOW` confirmation.
- Immutable byte-count and SHA-256 gates for the reviewed source CSV, verified
  v0.6.8 backup and active-table data/schema checkpoint.
- Independent active-table before/after fingerprints and explicit shadow-only
  database-write evidence.

### Database Evidence

- Built `euro_direct_debits__shadow_v069_20260811_163215` without renaming or
  modifying the active table.
- Loaded and validated 121,564 unique source rows over all 31 mapped columns,
  with zero null keys, duplicates, missing rows or hash mismatches.
- Preserved 44,539 annual, 42,039 semiannual and 34,986 quarterly rows in
  `time_period VARCHAR(20)` under the composite primary key.
- Repeated the full source-to-shadow comparison through an independent
  read-only path with the same result.
- Confirmed the active table remained at 75,647 rows with its original data and
  schema fingerprints. No swap was authorized or performed.

### Validation

- Passed 199/199 deterministic tests and parsed 249/249 active Python files.
- Passed `pip check`, 38/38 SQL-only asset recalculations, 9/9 Streamlit page
  renders and HTTP 200 application health.

---

## [v0.6.8] - 2026-08-11 - Verified Direct Debits Backup

### Added

- A one-table EURO backup command that requires an external physical volume.
- A separately confirmed restore verifier that creates a generated isolated
  schema, compares complete data and schema fingerprints, and removes the
  schema in a mandatory cleanup path.
- Explicit active-versus-isolated database-write evidence in the verification
  report.

### Backup Evidence

- Created a 25,308,899-byte structure-and-data dump scoped only to
  `euro_direct_debits` on a separate volume.
- Independently confirmed SHA-256
  `724F9B20F7A7A651395FDBC689D99E23B324F96329EC6E629BC60F616682852E`.
- Restored 75,647 rows into a generated isolated schema and matched the active
  full-row fingerprint
  `5BDAB01AFCF91D83161657736E94A0853B280FC946168008571233657EDD2907`.
- Matched the 31-column schema, `(key_code, time_period)` primary key and schema
  fingerprint
  `6E6237FA71CBAF7603782A694107C0B9352D843E13B0258F6F42A32DBEB0F768`.
- Removed the isolated schema and confirmed the active table remained at
  75,647 rows with `time_period YEAR(4)`.

### Validation

- Passed 193/193 deterministic tests and parsed 245/245 active Python files.
- Preserved 38/38 SQL-only asset checks, 9/9 Streamlit page renders and
  dependency integrity.
- Performed no write against the active database table.

---

## [v0.6.7] - 2026-08-11 - Direct Debits Temporal Integrity Diagnosis

### Added

- A read-only, full-key Direct Debits diagnostic with frequency and period-format evidence.
- A plan-only shadow-rebuild command that exposes proposed DDL, retained-table
  names, future swap and rollback statements, and mandatory authorization gates.
- Regression tests for annual, semiannual and quarterly period preservation.

### Corrected

- Extended EURO schema auditing beyond the first 1,000 source rows by combining
  source period patterns with distinct target frequencies.
- Added full-source period-pattern and target-type evidence to every streaming
  synchronization plan.
- Blocked transactional synchronization when the target period type cannot
  preserve the complete source period vocabulary.

### Findings And Safety

- Confirmed that `euro_direct_debits.time_period YEAR` collapsed all
  semiannual and quarterly labels into years.
- Explained all 77,025 source-only and 31,108 target-only business keys, with
  zero unexplained differences.
- Reclassified the current EURO schema baseline as 16 write-contract-ready
  tables and one controlled rebuild.
- Generated a `VARCHAR(20)` shadow plan with no build/apply/swap option and
  confirmed that no database table or row changed.

### Validation

- Passed 187/187 deterministic tests and parsed 240/240 active Python files.
- Preserved 38/38 SQL-only asset checks, 9/9 Streamlit page renders and
  dependency integrity.
- Re-ran the 17-contract deep EURO audit with 16 ready and one rebuild result.

---

## [v0.6.6] - 2026-08-11 - Complete EURO Read-Only Planning

### Added

- A lightweight consolidator for the latest saved plan of every EURO contract.
- A Data Quality `EURO Sync` view with status, source age, row counts, planned
  actions, blockers, source reference and database-write evidence.
- EURO synchronization status in the aggregated audit ZIP and JSON summary.

### Corrected

- Replaced the SQLAlchemy MySQL Connector target-result path with an explicitly
  unbuffered DBAPI cursor capped at 5,000 rows per fetch. This prevents the
  driver from buffering multi-million-row target scans before validation starts.

### Validation

- Completed read-only plans for 17/17 EURO contracts with zero database writes.
- Classified 12 plans as exact, four as changed and one as blocked.
- Completed the 7,812,208-row Balance Sheet Items target scan without the prior
  `MemoryError`.
- Passed 184/184 deterministic tests and parsed 234/234 active Python files.
- Rendered 9/9 Streamlit pages, exercised the complete Data Quality audit in a
  real browser and confirmed the 17/12/4/1/0 EURO status with no console error.
- Confirmed dependency integrity and kept all generated reports outside Git.

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
