# Refactor Plan

Current version: v0.5.0

## Purpose

This document describes the planned refactor strategy for the Macro-Financial Risk & Market Behaviour Analytics Platform.

The project currently contains multiple working asset scripts. Each script processes a specific market asset, calculates indicators, detects anomaly/risk signals and generates a Plotly dashboard.

The current priority is to preserve stability while gradually reducing code duplication and preparing the project for a more scalable multi-asset architecture.

---

# 1. Current Architecture

The current system is based on individual scripts for each asset:

```text
main.py
sp500.py
stoxx600.py
ftse100.py
gold.py
dollaramericano.py
euro.py
yuan.py
libra.py
ssecomposite.py

Each script follows a similar workflow:

CSV import
→ SQL update/load
→ Data preparation
→ Synthetic OHLC construction
→ Indicator calculation
→ Risk/anomaly signal detection
→ Plotly dashboard generation

This structure works and has already been validated across the current asset set.

2. Why Refactor?

The current scripts are functional but contain repeated logic.

The main reasons to refactor are:

reduce duplicated code;
make it easier to add new assets;
centralize common processing logic;
reduce maintenance effort;
avoid fixing the same issue in multiple scripts;
prepare the project for Streamlit;
prepare the project for future intermarket analysis;
prepare the project for machine learning workflows.

The refactor should not break the existing scripts.

The current working version should remain available as a stable fallback.

3. Refactor Principles

The refactor should follow these principles:

3.1 Stability First

The current scripts already work.

No script should be deleted or replaced until the new generic processor is tested and validated.

3.2 Parallel Development

New architecture should be developed in parallel.

Example:

existing scripts remain unchanged
asset_processor.py is created separately
one asset is tested first
results are compared
only then should migration be considered
3.3 Small Iterations

The project should evolve in small steps.

Avoid large changes that affect many files at once.

Preferred approach:

change one thing
test one asset
test all assets
document result
move to next step
3.4 Configuration-Driven Processing

Asset-specific details should be stored in:

asset_config.py

This includes:

asset key;
display name;
script name;
CSV path;
SQL table name;
market type;
symbol.

The processing logic should not be duplicated across scripts.

4. Target Architecture

The future architecture should move gradually towards this model:

asset_config.py
        ↓
asset_processor.py
        ↓
indicators.py
risk_detection.py
charts.py
database.py
        ↓
asset dashboards / reports / Streamlit

The objective is to make each asset processable with a single command such as:

process_asset("BTC")
process_asset("SP500")
process_asset("GOLD")
5. Planned asset_processor.py

The future asset_processor.py should contain the generic logic for processing any configured asset.

Expected function:

process_asset(asset_key)

Expected workflow:

1. load asset configuration
2. connect to database
3. import/update CSV data if needed
4. load asset table from SQL
5. prepare datetime column
6. construct synthetic OHLC if needed
7. calculate indicators
8. detect anomaly/risk signals
9. optionally update SQL
10. generate dashboard
11. return processed DataFrame
6. Migration Strategy

The migration should be done carefully.

Phase 1 — Create asset_processor.py

Create a new file without changing the existing scripts.

The first version should support only one test asset, for example:

SP500
Phase 2 — Compare Results

Compare the output of:

sp500.py

with:

process_asset("SP500")

Check:

number of rows;
date range;
price values;
indicators;
manipulation/anomaly flags;
dashboard output.
Phase 3 — Expand to More Assets

After SP500 works, test with:

GOLD
DXY
BTC

Then expand to all configured assets.

Phase 4 — Create Thin Asset Scripts

After validation, individual scripts may become simple wrappers.

Example:

from asset_processor import process_asset

process_asset("SP500")

This keeps the old entry points but removes duplicated logic.

Phase 5 — Update run_all_assets.py

Once asset_processor.py is stable, run_all_assets.py can process assets directly from asset_config.py.

Instead of running separate scripts, it may eventually do:

for asset_key in ASSETS:
    process_asset(asset_key)

This is a later step and should not be rushed.

7. Files to Keep Stable

The following files are considered part of the current stable core:

config.py
database.py
indicators.py
risk_detection.py
charts.py
asset_config.py
run_all_assets.py

These should only be changed with clear purpose and after backup/testing.

8. Files to Create Later

Potential future files:

asset_processor.py
asset_processor_test.py
intermarket_analysis.py
macro_processor.py
news_processor.py
streamlit_app.py
feature_engineering.py
ml_anomaly_detection.py

These should be added progressively.

9. Streamlit Preparation

The refactor should prepare the project for Streamlit.

A future Streamlit app may include:

Overview
Asset Dashboard
Technical Indicators
Risk Signals
Macro Context
News & Events
Intermarket Analysis
ML Experiments

To support this, processing functions should return DataFrames instead of only showing charts.

This means future functions should be reusable by:

scripts;
notebooks;
Streamlit pages;
Power BI export logic;
ML pipelines.
10. Machine Learning Preparation

The future ML layer will require clean and reusable features.

Potential features include:

returns
rolling volatility
drawdown
RSI
MACD percent
ATR
ADX
CCI
OBV
volume z-score
liquidity stress
market entropy
event flags
macro variables
news features

The refactor should make it easier to generate these features consistently across assets.

11. Risks of Refactoring

Refactoring can introduce problems if done too aggressively.

Main risks:

breaking currently working scripts;
changing indicator values unintentionally;
creating import/path errors;
creating SQL update mistakes;
mixing asset-specific logic incorrectly;
making debugging harder.

To reduce these risks:

do not delete working scripts
test one asset at a time
keep UPDATE_SQL=False during tests
compare outputs
commit stable versions
document changes
12. Recommended Next Steps

Recommended technical sequence:

1. keep current v0.2.1 stable
2. create asset_processor.py in parallel
3. test only SP500
4. compare against sp500.py
5. test GOLD and DXY
6. test BTC
7. test all assets
8. simplify individual scripts later
9. prepare Streamlit integration
13. Current Refactor Status

Current status:

v0.2.1 stable multi-asset scripts
asset_config.py prepared
indicators.py modularized
risk_detection.py modularized
charts.py modularized
run_all_assets.py available
generic asset_processor.py not yet implemented

The project is ready for the next architectural step, but the current working version should remain preserved.

14. Final Note

The purpose of this refactor is not to make the project more complex.

The purpose is to make the project easier to maintain, easier to explain and easier to expand.

A successful refactor should result in:

less duplicated code
clearer asset configuration
more reusable functions
safer testing
better preparation for Streamlit and ML
