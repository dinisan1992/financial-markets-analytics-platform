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
- Confirm that all 36,732 duplicate groups are identical and none are conflicting
- Identify 210,364 surplus rows without mutating SQL data
- Re-run all reference tests: 62/62 passed

## High Priority After v0.4.2

- Validate stale asset sources and updater behaviour one asset at a time
- Apply the reviewed duplicate cleanup and unique date constraints only after explicit approval
- Confirm the WTI contract/source for 20 April 2020
- Classify YUAN, FINANCIAL_CONDITIONS and TED_SPREAD by native frequency
- Extend read-only previews to the remaining SQL-capable importers
- Apply database changes only after explicit approval and backup
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

- Review all table primary keys and unique constraints
- Identify tables without unique date constraints
- Check for duplicated dates in market tables
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
- SQL updates are optional through `UPDATE_SQL`

Future tasks:

- Create generic `asset_processor.py`
- Improve `asset_config.py`
- Reduce duplicated logic across asset scripts
- Centralize CSV parsing rules
- Add optional chart display mode
- Add optional SQL update mode from command line
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

- Standardize FED ingestion scripts
- Standardize EU / ECB ingestion scripts
- Prevent duplicated macro rows
- Add unique constraints where appropriate
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
