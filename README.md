# Macro-Financial Risk & Market Behaviour Analytics Platform

A Python, MySQL, pandas, Plotly and Streamlit platform for analysing financial markets, macroeconomic indicators, correlations, event impact, technical indicators and rule-based market risk and anomaly signals.

The project was developed as a local analytics platform and professional portfolio project. Raw datasets, SQL dumps and private credentials are intentionally excluded from Git.

## Live Demo

**[Open the public Streamlit demo](https://financial-markets-analytics-demo.streamlit.app/)**

The public demo runs without MySQL, credentials or private CSV files. It reuses
the production pages and analytical services against deterministic synthetic
OHLCV and macro-financial series. Values and event reactions shown in demo mode
are illustrative and are identified as such throughout the application.

## Current Status

Functional local platform with:

- Interactive Streamlit dashboard.
- Multi-asset market analysis.
- Technical indicator engine.
- Rule-based risk and anomaly screening.
- FED macro-market analysis.
- EURO macro-market analysis.
- Multi-asset correlation analysis.
- Market event impact analysis.
- BTC cycle and halving analysis.
- Data quality and validation tools.
- Cross-platform lint, import-safety, dependency, coverage and unit-test checks through GitHub Actions.

Current project version: **v0.8.3**

## Main Analytical Capabilities

### Multi-Asset Analysis

The platform is configured to analyse:

- Crypto: BTC.
- US equity indices: SP500, NASDAQ100, DOWJONES and RUSSELL2000.
- European equity indices: STOXX600, EUROSTOXX50, FTSE100, DAX and CAC40.
- Asian and global equity indices: NIKKEI225, SSECOMPOSITE and EMERGING_MARKETS.
- Commodities: GOLD, SILVER, COPPER, BRENT_OIL, WTI_OIL, NATURAL_GAS, WHEAT and CORN.
- FX and currency indicators: DXY, EURO, YUAN, LIBRA, YEN and SWISS_FRANC.
- Sovereign yields: US3M, US2Y, US10Y, US30Y, GERMANY10Y, UK10Y and JAPAN10Y.
- Volatility and stress indicators: VIX, MOVE_INDEX, FINANCIAL_CONDITIONS and TED_SPREAD.

### FED Macro Layer

Configured indicators include:

- Federal Funds Effective Rate.
- M2 Money Supply.
- Fed Total Assets.
- Reserve Bank Credit.
- Deposits.
- Bank Credit.
- Loans and Leases.
- Securities in Bank Credit.
- Consumer Loans and Credit Cards.
- Credit Card Delinquency Rate.
- Credit Card Charge-Off Rate.

### EURO Macro Layer

Configured series include:

- HICP processed food.
- HICP all-items excluding tobacco.
- HICP services.
- HICP industrial goods.
- HICP administered energy and food.
- MFI corporate loans.
- MFI household consumption loans.
- MFI house purchase loans.
- MFI revolving loans to corporations.
- MFI revolving loans to households.
- MFI corporate deposits.
- MFI household deposits.

A future fraud analytics layer is planned for card fraud, credit transfer fraud, direct debit fraud and e-money fraud losses.

## Dashboard Pages

- **Overview** - project scope and module summary.
- **Asset Explorer** - centralized technical analysis, OHLC provenance, KPIs, risk indicators and event overlays.
- **Market Event Analysis** - cross-asset reactions, date precision, event detail and recovery analysis.
- **Correlations** - pairwise-valid matrices, observation-based rolling correlations, common-period coverage, confidence intervals and normalized performance.
- **Market Regimes** - rule-based regime classification and regime-conditioned performance.
- **FED Macro** - all configured FED/market pairs aligned on real market observations.
- **EURO Macro** - European macroeconomic series aligned on real market observations.
- **Data Quality** - read-only freshness, duplicate, price-review, remediation, pair-confidence, event-coverage and EURO synchronization-status audit with aggregated ZIP export.
- **Project Status** - current implementation and validation status.

## Application Screenshots

| Overview | Asset Explorer |
| --- | --- |
| ![Overview dashboard](docs/images/overview.png) | ![Asset Explorer](docs/images/asset_explorer.png) |

| Market Event Analysis | Correlations |
| --- | --- |
| ![Market Event Analysis](docs/images/market_event_analysis.png) | ![Correlation analysis](docs/images/correlations.png) |

| Market Regimes | Data Quality |
| --- | --- |
| ![Market Regimes](docs/images/market_regimes.png) | ![Data Quality audit](docs/images/data_quality.png) |

| FED Macro | EURO Macro |
| --- | --- |
| ![FED macro analysis](docs/images/fed_macro.png) | ![EURO macro analysis](docs/images/euro_macro.png) |

![Project Status](docs/images/project_status.png)

## Technical Indicators

The central indicator engine calculates:

- Native OHLC preservation when valid, with synthetic OHLC only for missing or invalid rows.
- Row-level `ohlc_source`, ATR, ADX and CCI quality provenance.
- Daily returns and price change percentages.
- EMA 9, 12, 20, 26, 50, 100 and 200.
- Bollinger Bands.
- RSI.
- Stochastic RSI.
- MACD, signal and histogram-related metrics.
- Momentum.
- ATR.
- ADX.
- CCI.
- OBV.
- Rolling and realized volatility.
- Drawdown and drawdown duration.
- Volume moving averages and volume z-score.
- Unit-invariant liquidity stress for assets with meaningful volume.
- Normalized market entropy on a 0-to-1 scale.

## Risk and Anomaly Screening

The project includes a heuristic screening layer for:

- Abnormal volume spikes.
- Possible pump/dump patterns.
- High-volume candle rejection patterns.
- Extreme RSI conditions.
- Abnormal price, volume, candle and volatility combinations.

These signals are analytical alerts only. A high-volume candle rejection is a
small-body candle with abnormal volume; it is not order-book spoofing detection.
The signals do not prove market manipulation and are not trading recommendations.

## Architecture

The application is separated into configuration, data access, analytical services, dashboard components and page modules.

- `streamlit_app.py` acts as the application entry point, cache wrapper and page router.
- `app/` contains layout, navigation and session-state helpers.
- `app_pages/` contains the main Streamlit page modules.
- `services/` contains reusable business and analytical logic.
- `dashboard/` contains visualization and Streamlit view components.
- `project_scripts/` contains asset processing, analysis and diagnostic scripts.
- `tools/` contains FED, EURO, news, SQL and legacy utilities.
- `tests/` contains automated unit tests.

## Project Structure

```text
.
|-- streamlit_app.py
|-- analysis_launcher.py
|-- config.py
|-- asset_config.py
|-- macro_config.py
|-- euro_series_config.py
|-- indicators.py
|-- risk_detection.py
|-- database.py
|-- app/
|   |-- layout.py
|   |-- navigation.py
|   `-- state.py
|-- app_pages/
|   |-- overview.py
|   |-- asset_explorer.py
|   |-- market_event_analysis.py
|   |-- correlations.py
|   |-- market_regimes.py
|   |-- fed_macro.py
|   |-- euro_macro.py
|   |-- data_quality.py
|   `-- project_status.py
|-- services/
|   |-- data_access_service.py
|   |-- event_analysis_service.py
|   |-- data_quality_service.py
|   |-- macro_analytics_service.py
|   |-- market_regime_service.py
|   |-- btc_cycle_service.py
|   |-- technical_signal_service.py
|   |-- risk_statistics_service.py
|   |-- export_service.py
|   `-- project_status_service.py
|-- dashboard/
|-- project_scripts/
|   |-- assets/
|   |-- analysis/
|   `-- diagnostics/
|-- tools/
|   |-- fed/
|   |-- eu/
|   |-- news/
|   |-- legacy/
|   `-- sql/
|-- tests/
|-- demo/
|   |-- streamlit_demo.py
|   |-- demo/
|   |   |-- data.py
|   |   `-- runtime.py
|   `-- tests/
|-- docs/
|-- data/              # ignored by Git
|-- new_market_data/   # ignored by Git
|-- outputs/           # ignored by Git
|-- archive/           # ignored by Git
|-- requirements.txt
|-- requirements-dev.txt
|-- ruff.toml
|-- .coveragerc
|-- .env.example
`-- .gitignore
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

For development, install the runtime dependencies plus the pinned quality
tools:

```powershell
python -m pip install -r requirements-dev.txt
```

Create a private `.env` file:

```powershell
copy .env.example .env
```

Fill in the local database credentials and any optional API keys.

Run the dashboard:

```powershell
python -m streamlit run streamlit_app.py
```

## Environment Variables

Supported variables:

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `PROJECT_DATA_DIR`
- `PROJECT_NEW_MARKET_DATA_DIR`
- `PROJECT_MARKET_CLEAN_DIR`
- `PROJECT_SOURCE_DATA_DIR`
- `FED_SOURCE_DIR`
- `EURO_SOURCE_DIR`
- `NEWSDATA_API_KEY`
- `CRYPTOPANIC_API_TOKEN`
- `DEFAULT_UPDATE_SQL`

The default local database is `btc_data` on `localhost:3306`. Dashboard and validation paths are read-only. CSV synchronization is a separate explicit command and requires `--update-sql` for one named asset.

Preview one asset without writing:

```powershell
python project_scripts/assets/sync_market_data.py SP500
```

Apply a reviewed plan:

```powershell
python project_scripts/assets/sync_market_data.py SP500 --update-sql
```

Bulk writes are intentionally disabled. See `docs/DATA_PIPELINE.md` for the backup, dry-run and remediation workflow.

Provider, ticker/series identity, source URL, native frequency and OHLC contracts
are documented in `docs/DATA_SOURCES.md` and enforced by
`market_source_manifest.py`.

FED and EURO source files have a separate controlled preview command:

```powershell
python project_scripts/ingestion/refresh_macro_sources.py ALL --check-sql
```

The macro preview command validates all 28 source contracts and never writes by default. A
single FED import can use `--update-sql` only with an exact table confirmation,
a verified SQL backup containing that table and a unique business key. Version
v0.7.0 qualifies the dedicated, default-read-only EURO synchronization planner
and one-table transactional apply engine. It classifies inserts, updates,
unchanged and target-only rows through a disk-backed comparison; deletions are
disabled, target-only rows block a write, and apply mode requires a scoped
backup plus an import-specific confirmation. Full-source period checks now also
block a plan when the SQL period type cannot preserve the source frequency.
See `docs/EURO_SCHEMA_AUDIT.md`,
`docs/EURO_SCHEMA_REMEDIATION.md`, `docs/EURO_SOURCE_COMPLETENESS.md` and
`docs/EURO_STREAMING_VALIDATION.md` for the read-only large-source evidence,
`docs/EURO_LARGE_REBUILD_PLAN.md` for the isolated rebuild runbook,
`docs/EURO_LARGE_REBUILD_RESULTS.md` for the execution evidence, and
`docs/EURO_TRANSACTIONAL_SYNC.md` for refresh policies,
`docs/EURO_MYSQL_ACCEPTANCE.md` for the isolated MySQL evidence,
`docs/EURO_SYNC_STATUS.md` for the complete 17-contract planning baseline,
`docs/EURO_PRECISION_AUDIT.md` for the storage-aware field-difference review,
`docs/EURO_DIRECT_DEBITS_REMEDIATION.md` for the confirmed period-loss defect,
`docs/EURO_DIRECT_DEBITS_BACKUP.md` for the independently restored backup,
`docs/EURO_DIRECT_DEBITS_SHADOW.md` for the validated non-active replacement,
`docs/EURO_DIRECT_DEBITS_SWAP.md` for the atomic promotion and rollback evidence,
and `docs/MACRO_IMPORT_SAFETY.md` for importer controls.

Three production-scale ECB sources also have an official, probe-first staging
command:

```powershell
python project_scripts/ingestion/refresh_ecb_sources.py
```

Complete downloads require an explicit external `--staging-dir`. The command
validates schema, hashes each candidate and can compare staged snapshots with
active CSVs through a disk-backed index. It cannot replace active CSVs and has
no SQL write mode. See `docs/ECB_SOURCE_REFRESH.md`.

Version v0.7.9 adds a separate read-only readiness gate for those candidates:

```powershell
python project_scripts/diagnostics/plan_ecb_shadow_refresh.py `
  --staging-dir <external-staging-directory> `
  --backup-dir <external-backup-directory> `
  --audit-dir <fresh-audit-directory> `
  --workspace-dir <external-workspace-directory> `
  --pin-file <reviewed-shadow-plan.json>
```

The command verifies candidate and backup hashes, consumes a fresh complete
source-to-target audit, checks live table state and storage capacity, and emits
DDL/swap/rollback previews. It deliberately exposes no build, apply or swap
mode. See `docs/ECB_SHADOW_READINESS.md`.

## Validation Snapshot

The v0.8.3 release validation includes:

- 267/267 deterministic unit tests pass.
- 12/12 public-demo contracts pass, including fixed-window invariance,
  plausible stress/macro levels, shared equity structure and SQL isolation.
- The demo smoke test generates all 38 configured assets, 10 events and aligned
  macro data; its dedicated AppTest renders 9/9 pages without exceptions.
- The complete active Python tree compiles successfully and `pip check` reports no broken requirements.
- Ruff passes across the active Python tree with no lint errors.
- Branch coverage is measured across `app`, `app_pages`, `dashboard` and `services`, with a 40% regression gate over the current 44% baseline.
- GitHub Actions runs static/import-safety/demo-page checks and a four-environment
  unit and demo-test matrix covering Windows, Linux, Python 3.11 and Python 3.12.
- 38/38 configured SQL assets recalculate successfully with database writes disabled.
- 9/9 Streamlit pages render without uncaught exceptions and the running server reports HTTP 200 health.
- Financial property tests cover indicator bounds, Bollinger ordering, correlation symmetry, Base 100 anchoring and event-date direction.
- Regression tests cover normalized entropy, volume-unit invariance, unavailable volume metrics and OHLC-derived indicator quality.
- The EURO planner is memory-bounded, dry-run by default and restricted to one explicit import contract.
- Policies are explicit: source nulls are authoritative, target-only rows block, source duplicates and invalid numerics block, and deletes are disabled.
- The apply engine writes only planned inserts and updates inside one transaction, then repeats the complete source-to-target comparison before commit.
- Deterministic SQLite tests prove idempotency, selective upsert, authoritative-null handling and full rollback after a forced post-write failure.
- Read-only MySQL smoke plans confirmed 198/198 fraud rows and 1,594,491/1,594,491 MFI rows unchanged, with zero actions or blockers.
- A verified 110,420-byte fraud-table backup restored exactly into an isolated MySQL schema with all 198 rows and the active full-row SHA-256 fingerprint.
- The isolated MySQL drill committed one insert and two updates, including a source-null overwrite, and the immediate reapply wrote zero rows.
- A forced post-write mismatch rolled back the complete MySQL transaction; all 198 original rows and their fingerprint were preserved.
- The active schema was never written, its before/after fingerprint was identical, and no temporary acceptance schema remained.
- The pre-remediation read-only baseline covered 17/17 EURO contracts: 12 exact, four with reviewed changes and one blocked by target-only rows.
- A complete Direct Debits key analysis proves that the `YEAR` target column collapsed every semiannual and quarterly source period: all 77,025 source-only and 31,108 target-only keys are explained, with zero unexplained differences.
- The full-source synchronization guard rejected the lossy period type, and the pre-swap deep audit classified 16 contracts as write-ready plus one controlled rebuild.
- The original Direct Debits planning command remains read-only; a separate build-only command has no swap option and requires the exact v0.6.9 confirmation.
- A 25,308,899-byte Direct Debits structure-and-data backup was created on a separate volume, independently hashed and restored into a generated isolated schema.
- All 75,647 restored rows, the complete row fingerprint, 31-column schema fingerprint and composite primary key match the active table; the temporary schema was removed and the active table remained unchanged.
- A versioned `VARCHAR(20)` Direct Debits shadow now preserves 121,564/121,564 reviewed source rows, including all annual, semiannual and quarterly periods.
- Before promotion, two complete source-to-shadow comparisons found zero missing, extra, duplicate or mismatched rows while the active table remained unchanged.
- Version v0.7.0 atomically promoted that shadow and retained the former 75,647-row table under `euro_direct_debits__pre_v069_20260811_163215` for rollback.
- The post-swap plan is exact and idempotent: 121,564 unchanged rows, zero inserts, updates, target-only rows or blockers; the schema audit now classifies 17/17 EURO contracts as write-ready.
- MySQL Connector target scans use an explicitly unbuffered cursor capped at 5,000 rows; the 7,812,208-row balance-sheet plan completed without buffering the result set into memory.
- EURO row fingerprints now respect target `FLOAT` and `DECIMAL` precision,
  normalize signed zero and ignore outer text whitespace, preventing permanent
  false updates caused by SQL storage representation.
- Complete read-only revalidation reduced Card Payments from 459,207 apparent
  updates to 15 rows, Bank Lending Survey from 222,668 to one row, and Balance
  Sheet Items from 3,132,298 to 54 sixth-decimal differences.
- A deterministic hash-sampled field auditor reports the exact differing
  columns and examples through SELECT-only SQL access without publishing local
  source paths.
- Official complete BLS, PCP and BSI snapshots were downloaded into external
  staging with validated headers and SHA-256 evidence; none replaced an active
  CSV.
- The three candidates contain 10,361,570 unique business keys in total with
  zero null keys, invalid numerics, duplicates or hash conflicts.
- SELECT-only MySQL plans classify 920,328 candidate-only keys, 350,495
  target-only keys and broad official metadata/value revisions; no plan was
  applied.
- Three scoped SQL backups preserve the complete active BLS, PCP and BSI
  tables on a separate physical volume with independently verified SHA-256.
- Versioned shadow and retained-table SQL previews are complete; schema
  inspection confirms none was executed or created.
- A fresh 10,361,570-row source-to-live-table audit reproduced the reviewed
  BLS, PCP and BSI classifications with zero database writes.
- The read-only v0.7.9 readiness gate reverified all candidate and backup
  hashes, current row counts, planned table-name availability and storage
  capacity; all three contracts are ready for separately authorized,
  one-at-a-time shadow builds.
- The separately authorized BLS build created a 1,225,110-row versioned shadow
  from the official staged snapshot and validated every business key and mapped
  value twice through memory-bounded comparisons.
- One signed-zero representation (`-0E-12` in CSV, `0E-12` in MySQL) exposed a
  technical hash normalization gap. The canonical hash now treats both as
  financial zero; exactly one guarded shadow-only hash was repaired and the
  complete validation then reported zero mismatches.
- The separately authorized atomic BLS promotion revalidated the pinned source,
  backup, active checkpoint and complete shadow before changing table names.
- The official 1,225,110-row snapshot is active with zero source/target
  differences. The former 1,164,356-row active table remains intact under its
  versioned retained name; no table or source row was deleted. See
  `docs/ECB_BLS_SWAP.md`.
- The separately authorized PCP build created a 1,081,151-row Card Payments
  shadow and validated every official source key and mapped value twice with
  zero mismatches.
- Before promotion, the 815,173-row PCP active table retained identical data
  and schema fingerprints while the shadow remained isolated. See
  `docs/ECB_PCP_SHADOW.md`.
- A separate PCP-only atomic promotion command is now guarded by the signed
  readiness, build and independent verification reports. Its SELECT-only
  preflight repeated the complete 1,081,151-row source-to-shadow comparison
  with zero differences and zero database writes.
- Version v0.8.3 atomically promoted the official PCP snapshot after explicit
  authorization and complete revalidation. The 1,081,151-row source is now
  active with zero differences; the former 815,173-row table remains intact as
  the immediate rollback checkpoint. No CSV changed and no shadow or failed
  artifact remains. See `docs/ECB_PCP_SWAP.md`.
- A fresh BSI-only readiness checkpoint reverified the 8,055,309-row official
  source, 7,812,208-row active table, 5.13 GB scoped backup, unused future
  names and current storage capacity with zero database writes. The builder is
  now restricted to BSI and still exposes no swap mode. See
  `docs/ECB_BSI_READINESS.md`.
- Data Quality exposes the latest saved status, source freshness, planned actions and blockers for every EURO contract without rescanning CSVs or querying MySQL.

The retained v0.5.6 database validation includes:

- 121/121 deterministic unit tests passed at that checkpoint, 211 active Python files parsed successfully and `pip check` reported no broken requirements.
- 28/28 FED and EURO CSV contracts pass controlled preview; all entrypoint modules import without opening a database connection.
- Full-source and SQL contract checks identify all 11 FED imports as write-ready; EURO schema status is 14 contract-ready and three controlled rebuilds.
- Four FED tables received a unique `observation_date` key after duplicate/null checks and a verified scoped SQL backup; no source rows were changed or removed.
- Six unsafe EURO schemas were rebuilt from 1,548,900 source observations through validated shadow tables and an atomic swap.
- The remediation recovered 956,717 unique historical business keys relative to the previous schemas; zero null or duplicate keys remain.
- A 324,480,219-byte structure-and-data backup was verified before the swap, and all six original tables remain retained locally for rollback.
- Three further EURO tables were rebuilt exactly from 112,559 source rows after full-row checks found decimal rounding and text truncation in the former copies.
- A separate 48,858,895-byte SQL backup was verified; all three former tables remain retained under `pre_v056` names.
- Source cardinality checks found 9,475,513 observations still absent from consumer prices, national accounts and MFI interest rates; these tables remain blocked rather than being given misleading keys.
- 16/16 configured EURO series are present and 12/12 active EURO/market pairs load and align successfully.
- Every active macro importer requires explicit `--update-sql`; general EURO refresh writes remain disabled pending the transactional multidimensional updater.
- 15/15 configured FED/market pairs loaded and aligned successfully from the live MySQL data.
- 38/38 configured asset tables load and recalculate successfully through the SQL-only global validator with database writes disabled.
- 9/9 Streamlit pages render without uncaught exceptions; US2Y, US3M and Data Quality were exercised in a real browser session.
- The post-migration audit reports 38 assets, 703 correlation pairs, 66 events, zero duplicate assets, zero invalid price assets and no load errors.
- US2Y refreshes from the official Federal Reserve H.15 package in dry-run mode and validates 12,537 unique observations without writing CSV or SQL data.
- US2Y and US3M are idempotent against their current CSV files and have unique temporal keys.
- A 1,482,349-byte SQL backup containing structure and data was verified before the Treasury migration; the original SQL table and CSV remain available locally for recovery.

The previous database-enabled validation covered all then-configured assets, 11/11 FED series and 12/12 active EURO loaders. See `PROJECT_STATUS.md` for details.

## Data and Reproducibility

The production-scale local database and raw datasets are not included in the repository.

A database-free public demo is included under `demo/` and deployed on
[Streamlit Community Cloud](https://financial-markets-analytics-demo.streamlit.app/).
It uses synthetic data with stable date-window semantics and does not represent
historical prices or investment results.

The public repository focuses on:

- source code;
- analytical methodology;
- project architecture;
- tests;
- configuration examples;
- documentation.

The local database remains intentionally separate from the public source repository.

## GitHub Safety

The repository is configured to exclude:

- `.env` files and private credentials.
- Streamlit secrets.
- Raw CSV and Excel datasets.
- SQL and database dumps.
- Local virtual environments.
- Generated outputs and reports.
- Local backups and archives.

## Roadmap

Planned improvements include:

- Calibrate risk thresholds by asset class and data provenance.
- Replace important year-only world events with verified exact dates.
- Add dry-run and explicit entry points to the remaining SQL-capable ETL scripts.
- Obtain explicit authorization before running the prepared BSI-only shadow
  build. Its refreshed backup, readiness and capacity checks are complete.
- Retain the former BLS and PCP tables until a separate retention review.
- Treat the 3,822,937-row Government Finance source expansion as a separate controlled migration.
- Refresh the remaining stale market sources through verified provider
  contracts.
- Develop Event Study v2 with benchmark, abnormal-return and cumulative
  abnormal-return contracts.
- Develop the deferred EURO fraud analytics layer.
- Start machine-learning experiments only after feature and label governance is stable.

## Disclaimer

This project is for educational, analytical and portfolio purposes only. It does not provide financial advice.
