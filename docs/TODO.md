# TODO

## Historical Work Completed in v0.2.0 / v0.2.1

- Modular BTC pipeline tested successfully
- `main.py` validated
- `config.py` validated
- `database.py` validated
- `indicators.py` validated
- `risk_detection.py` validated
- `charts.py` validated
- MySQL connection validated
- Plotly dashboard validated
- Manipulation detection validated
- Confirmed no destructive SQL operations in core pipeline
- Adapted SP500 as first asset-pilot
- Adapted STOXX600
- Adapted FTSE100
- Adapted GOLD
- Adapted DXY / USD Index
- Adapted EURO
- Adapted YUAN
- Adapted LIBRA / GBP
- Adapted SSE Composite
- Added `UPDATE_SQL = False` mode to asset scripts
- Created `run_all_assets.py`
- Validated global runner with 10 scripts
- Created `ASSETS_STATUS.md`

---

## Completed in v0.4.1

- Archive the previous read-only audit automatically before overwrite
- Report stale assets, source and responsible updater
- Diagnose duplicate groups without mutating SQL data
- Classify the historical WTI_OIL negative value for source review
- Report zero-return series and source-frequency risks
- Add correlation overlap, common period, confidence and 95% intervals
- Re-run all financial reference tests: 56/56 passed

## Completed in v0.4.2

- Centralize legacy CSV parsing and in-memory date deduplication
- Disable automatic base imports for EURO, YUAN, LIBRA and SSECOMPOSITE
- Add explicit read-only `--dry-run-import` previews
- Confirm that all 36,732 duplicate groups have matching price and volume values
- Identify 210,364 surplus observations by date without mutating SQL data
- Re-run all reference tests: 62/62 passed

## Completed in v0.4.3

- Compare every column in the four duplicated legacy tables
- Separate base-value equality from exact full-row equality
- Identify 36,729 groups with technical-column variants
- Identify 173,633 exact full-row copies
- Re-run all reference tests: 63/63 passed

## Completed in v0.5.0

- Create one locale-aware market CSV parser and idempotent synchronization planner
- Make dry-run the default and reject bulk SQL writes
- Consolidate EURO, YUAN, LIBRA and SSECOMPOSITE to one daily row
- Correct the SP500 one-day legacy shift from the source CSV
- Add unique daily keys to the seven remediated market tables
- Update BTC, STOXX600 and SSECOMPOSITE from reviewed synchronization plans
- Verify a scoped SQL backup and retain the seven pre-remediation tables
- Re-run the post-remediation audit with zero duplicate assets
- Validate 37/37 market assets, 9/9 Streamlit pages and 78/78 tests

## Completed in v0.5.1

- Create a source registry with provider, identifier, URL, frequency and OHLC contract
- Reclassify Yahoo `^IRX` from the incorrect US2Y label to US3M
- Import the official Federal Reserve H.15 two-year yield as US2Y
- Preserve external SQL/CSV backups and a retained pre-migration SQL table
- Add a dry-run-first official US2Y refresh command
- Expose provider and series identity in the Data Quality outputs

## Completed in v0.5.2

- Register all 11 FED and 17 EURO source files in an executable import manifest
- Replace import-time database writes with safe preview entrypoints
- Require explicit `--update-sql`, exact table confirmation and a verified backup for FED writes
- Block EURO writes pending complete multidimensional mappings and business keys
- Preserve the previous implementations locally as Git-ignored non-executable text
- Validate 28/28 source contracts and importer side-effect safety

## Completed in v0.5.3

- Audit all four blocked FED tables for null and duplicate observation dates
- Create and validate a scoped structure-and-data SQL backup
- Add unique `observation_date` keys without changing source rows
- Validate all 11 FED import contracts as write-ready
- Add dry-run, confirmation, post-check and rollback support to the migration command

## Completed in v0.5.4

- Audit all 17 EURO CSV/SQL contracts without database writes
- Validate source aliases and source-period compatibility with SQL types
- Classify five schemas as ready, six as key-addition candidates and six as rebuilds
- Confirm zero null business keys and isolate ATM/POS duplicate business keys
- Confirm 16/16 configured EURO series and 12/12 active market alignments
- Add reusable audit reports and deterministic safety tests

## Completed in v0.5.5

- Create and validate a scoped structure-and-data backup for six EURO tables
- Rebuild all six historical-loss schemas through isolated shadow tables
- Validate 1,548,900 source rows across every mapped column after SQL storage
- Preserve native textual periods and unique `(key_code, time_period)` contracts
- Swap the six tables atomically and retain every original table for rollback
- Confirm 11 ready schemas, six key candidates and zero remaining rebuilds

## Completed in v0.5.6

- Scan all six remaining EURO CSVs for complete source cardinality
- Rebuild fraud losses, retail interest rates and payment-system transactions
- Preserve 112,559 exact rows with full-row hash validation
- Retain all three former tables and a verified scoped backup for rollback
- Reclassify three incomplete target histories instead of adding misleading keys
- Confirm 14 ready schemas, zero key candidates and three controlled rebuilds

## Completed in v0.6.0

- Normalize rolling market entropy to a documented zero-to-one scale
- Replace raw-volume liquidity stress with a unit-invariant z-score measure
- Disable liquidity stress where meaningful volume is not expected or available
- Expose native versus approximate-synthetic quality for ATR, ADX and CCI
- Replace active spoofing-like labels with high-volume candle rejection terminology
- Preserve compatibility aliases for historical exports and notebooks
- Add financial property and analytical regression tests
- Pass 130 deterministic tests, 38 SQL-only asset recalculations and 9 Streamlit page renders without any database write

## Completed in v0.6.1

- Implement a disk-backed, memory-bounded source-to-SQL validator for the three large EURO sources
- Keep source and target chunks bounded at 50,000 rows during the live audit
- Separate missing rows, extra rows, full-row mismatches, duplicates, null keys and invalid numerics
- Prove through deterministic SQL-capture tests that the target receives read statements only
- Audit all 10,864,513 source rows without changing MySQL or any CSV
- Confirm 9,475,513 missing SQL rows and 313,682 mismatched overlapping rows
- Persist local JSON/CSV evidence under Git-ignored `audit_outputs/`
- Pass 137 deterministic tests and parse 216 active Python files

## High Priority After v0.6.1

- Confirm the seven source contracts still marked as inferred during their next refresh
- Replace the shadow rebuild's remaining in-memory fingerprint dictionary with the v0.6.1 disk-backed store
- Rebuild consumer prices, national accounts and MFI interest rates one at a time
- Build the transactional multidimensional EURO updater with missing-value policy
- Add isolated database-backed synchronization tests
- Confirm the WTI contract/source for 20 April 2020
- Classify YUAN, FINANCIAL_CONDITIONS and TED_SPREAD by native frequency
- Compare every post-update audit with an archived baseline

---

## Documentation

- Add database schema documentation
- Document all market asset tables
- Document FED macro tables
- Document EU / ECB macro tables
- Document event/news tables
- Document `btc_analysis_powerbi`
- Add explanation of synthetic OHLC construction
- Add explanation of manipulation detection logic
- Add explanation of advanced indicators
- Add explanation of event impact scoring
- Add screenshots later
- Add sample data documentation later

---

## SQL / Database

- Review primary keys and unique constraints in FED/EURO macro tables
- Preserve the one-daily-row invariant in market tables
- Check for duplicated observation dates in macro tables
- Prepare future controlled SQL migrations
- Decide which advanced indicators should be stored in SQL
- Add indexes where useful for performance
- Avoid storing unnecessary repeated calculations
- Consider SQLAlchemy migration for cleaner `pd.read_sql()` usage

---

## Asset Processing

Current status:

- Individual asset scripts are standardized and functional
- Fast in-memory calculation mode is implemented
- Market SQL writes use one explicit, reviewed synchronization command

Future tasks:

- Create generic `asset_processor.py`
- Improve `asset_config.py`
- Reduce duplicated logic across asset scripts
- Extend centralized CSV parsing rules to macro importers
- Add optional chart display mode
- Add isolated test-schema support for synchronization tests
- Add optional asset selection in runner

---

## Charts

Future improvements to `charts.py`:

- Add dynamic chart titles
- Add asset name parameter
- Add optional chart display
- Add optional HTML export
- Improve legend layout
- Add date range filters
- Add option to display only recent years
- Improve manipulation marker visibility
- Prepare chart functions for Streamlit rendering

---

## Advanced Indicators

Currently calculated only in DataFrame:

- `volume_zscore`
- `realized_volatility_30d`
- `volatility_of_volatility`
- `liquidity_stress`
- `drawdown_duration`
- `market_entropy`

Future task:

- decide which indicators should be stored in SQL
- create controlled `ALTER TABLE` migration if needed
- update SQL update functions safely
- add selected indicators to Power BI/Streamlit datasets
- evaluate usefulness for anomaly detection and regime classification

---

## Power BI / Reporting Layer

- Review `btc_analysis_powerbi.py`
- Modularize Power BI export logic
- Decide whether Power BI remains a basic reporting layer only
- Add advanced indicators to reporting datasets later
- Decide which metrics belong in SQL vs reporting-only tables
- Create equivalent enriched tables for SP500, GOLD, DXY and other assets
- Consider creating a single multi-asset reporting table

---

## Macro / FED / EU Layer

Future work:

- Complete safe write support for standardized EU / ECB ingestion
- Prevent duplicated EURO macro rows
- Add unique EURO constraints where appropriate
- Create macro feature calculations
- Create macro charts later
- Create macro stress indicators
- Connect macro data to market behaviour analysis

---

## Event / News Layer

- Document `bitcoin_historical_events`
- Document `world_historical_events`
- Document `crypto_news`
- Document `world_news`
- Improve event impact methodology
- Decide whether world events should be mapped by exact date instead of full year
- Add event categories
- Add severity scoring
- Add future sentiment or narrative scoring
- Connect news/event layer to market movement analysis

---

## Intermarket Analysis

Future module:

- rolling correlations
- dynamic beta
- capital flow analysis
- risk-on / risk-off indicators
- BTC vs DXY
- BTC vs GOLD
- BTC vs SP500
- GOLD vs DXY
- cross-market divergence
- correlation breakdown detection
- crisis vs peaceful period comparison

---

## Streamlit

Future platform:

- asset selector
- technical analysis page
- risk signals page
- macro events page
- intermarket page
- ML page
- event timeline
- exportable screenshots for GitHub
- dashboard summary page

---

## Machine Learning

Future phase:

- anomaly detection
- clustering
- regime classification
- feature importance
- temporal validation
- train/test split by time
- avoid data leakage
- compare crisis, war and stable periods
- detect market manipulation patterns
- analyse capital flow behaviour between asset classes

---

## GitHub / Portfolio

Public portfolio follow-up:

- Remove all API keys from code
- Use `.env`
- Create `.env.example`
- Ensure `.gitignore` excludes datasets and credentials
- Move old scripts into `legacy/`
- Add screenshots
- Add clear project status
- Add known limitations
- Add installation instructions
- Add sample data or mock data
- Add database schema only, not full data
- Add portfolio-friendly README
- Add methodology explanation
