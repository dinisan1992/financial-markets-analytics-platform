# Assets Status

Current version: v0.2.0

## Overview

This document tracks the current status of the financial asset processing scripts.

The main objective of this phase was to refactor the original individual asset scripts into a more stable, modular and faster structure.

Each adapted asset script now follows the same processing logic:

```text
CSV
→ Base SQL import/update
→ Data loading from MySQL
→ Synthetic OHLC construction
→ Indicator calculation in memory
→ Manipulation/anomaly detection in memory
→ Optional SQL update
→ Plotly dashboard

By default, all adapted scripts use:

UPDATE_SQL = False

This means indicators and manipulation flags are calculated in memory and SQL is not updated unless explicitly enabled.

Adapted Asset Scripts
Asset	Script	SQL Table	Status
Bitcoin	main.py	btc_analysis	Completed
SP500	sp500.py	sp500_analysis	Completed
STOXX600	stoxx600.py	stoxx600_analysis	Completed
FTSE100	ftse100.py	ftse100_analysis	Completed
Gold	gold.py	gold_analysis	Completed
DXY / USD Index	dollaramericano.py	dxy_analysis	Completed
Euro	euro.py	euro_analysis	Completed
Yuan	yuan.py	yuan_analysis	Completed
Libra / GBP	libra.py	libra_analysis	Completed
SSE Composite	ssecomposite.py	ssecomposite_analysis	Completed
Global Runner

A global runner was created:

run_all_assets.py

This script executes all adapted asset scripts sequentially and returns a final summary.

Latest validation result:

Total scripts: 10
Success: 10
Errors: 0
Missing: 0
Current Processing Mode

The current preferred mode is:

UPDATE_SQL = False

Reason:

avoids unnecessary mass SQL updates;
improves execution speed significantly;
keeps visual analysis fast;
prevents repeated writes to MySQL;
allows indicators and manipulation flags to be recalculated dynamically.

To force SQL updates for a specific asset, change inside that script:

UPDATE_SQL = True
SQL Update Mode

SQL updates are still available per asset.

To activate them, open the desired asset script and change:

UPDATE_SQL = False

to:

UPDATE_SQL = True

This will update:

RSI;
EMAs;
Bollinger Bands;
Stoch RSI;
MACD;
Momentum;
ATR;
ADX;
CCI;
OBV;
MACD Percent;
Price Change Percent;
Manipulation flags.

Advanced indicators calculated in indicators.py are still not stored in SQL.

Advanced Indicators

The following advanced indicators are currently calculated only in memory:

volume_zscore
realized_volatility_30d
volatility_of_volatility
liquidity_stress
drawdown_duration
market_entropy

These are not yet written to SQL.

Future decision required:

decide which advanced indicators should be persisted;
create controlled SQL migrations;
update SQL export/reporting layers;
add selected indicators to Power BI/Streamlit datasets.
Known Warnings

Some scripts may show this warning:

pandas only supports SQLAlchemy connectable...

This is not a critical error.

Future improvement:

migrate all pd.read_sql(..., conn) calls to SQLAlchemy engines.
Current Limitations
Asset scripts are still duplicated structurally.
CSV cleaning logic is still asset-specific.
charts.py is shared but not yet fully customizable by asset.
run_all_assets.py opens each script independently.
SQL update mode still uses row-by-row updates.
Advanced indicators are not persisted to SQL.
Intermarket analysis is not yet implemented.
Streamlit interface is not yet implemented.
Next Technical Improvements
1. Improve Chart Layer

Future improvements to charts.py:

dynamic chart titles;
asset name parameter;
optional chart display;
optional HTML export;
better legend layout;
date range filters;
cleaner visual style;
support for Streamlit rendering.
2. Create Generic Asset Processor

Future file:

asset_processor.py

Objective:

reduce duplicated code;
centralize common asset logic;
process assets based on configuration;
simplify future maintenance.
3. Create Asset Configuration Layer

Future improvement to:

asset_config.py

Objective:

centralize asset name;
CSV path;
SQL table;
parsing rules;
asset category;
display name.
4. Build Intermarket Analysis

Future file:

intermarket.py

Potential features:

rolling correlations;
BTC vs DXY;
BTC vs Gold;
BTC vs SP500;
Gold vs DXY;
risk-on / risk-off behaviour;
crisis-period comparisons;
capital flow analysis.
5. Create Streamlit Dashboard

Future application:

app.py

Main pages:

Overview;
Technical Indicators;
Risk Signals;
Macro Events;
Intermarket Analysis;
Machine Learning.
Current Project Status

The project has moved from:

individual duplicated asset scripts

to:

standardized multi-asset analytical pipeline

Current milestone:

v0.2.0 — Multi-asset scripts stabilized

This version is suitable as a public portfolio/interview demonstration. Remaining work is tracked as future improvements rather than release blockers.
