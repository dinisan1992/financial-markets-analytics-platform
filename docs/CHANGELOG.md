# Changelog

All notable changes to this project will be documented here.

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
