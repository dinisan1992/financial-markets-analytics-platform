# Macro-Financial Risk & Market Behaviour Analytics Platform

Current Version: v0.2.1

## Overview

This project is a multi-source financial analytics platform designed to study market behaviour, macroeconomic regimes, capital flow dynamics and potential market manipulation/anomaly patterns through quantitative analysis, feature engineering and future machine learning integration.

The system integrates:

- financial market data;
- cryptocurrency data;
- equity indices;
- precious metals;
- currency/FX-related assets;
- macroeconomic indicators;
- historical events;
- news data;
- Power BI-ready analytical datasets;
- future Streamlit and machine learning layers.

The objective is to identify behavioural patterns across different market conditions such as:

- financial crises;
- inflationary periods;
- high volatility regimes;
- geopolitical instability;
- bull/bear markets;
- liquidity shifts;
- risk-on / risk-off environments.

The platform also focuses on detecting possible anomaly signals such as:

- Pump/Dump-like patterns;
- Spoofing-like behaviour;
- abnormal volume;
- abnormal volatility;
- RSI extremes;
- ATR spikes;
- cross-market divergences;
- potential market manipulation signals.

> Important: the current detection logic is heuristic and should be interpreted as possible risk/anomaly signalling, not as definitive proof of market manipulation.

---

## Main Objectives

### 1. Market Regime Detection

Identify different macro-financial environments through quantitative indicators and historical market behaviour.

Examples:

- stable market regimes;
- high volatility regimes;
- bearish periods;
- crisis periods;
- risk-off environments;
- liquidity stress periods.

---

### 2. Capital Flow Analysis

Study how capital may move across different asset classes during different economic conditions.

Examples:

- Bitcoin;
- Gold;
- USD / DXY;
- equity indices;
- major currencies;
- liquidity-sensitive assets.

---

### 3. Market Behaviour Analysis

Analyse relationships between:

- volatility;
- momentum;
- liquidity;
- volume;
- macroeconomic indicators;
- market stress;
- historical events;
- news context.

---

### 4. Anomaly & Manipulation Signal Detection

Detect abnormal market behaviour using:

- volume anomalies;
- ATR spikes;
- RSI extremes;
- candle structure analysis;
- statistical deviations;
- liquidity stress indicators;
- market entropy;
- heuristic Pump/Dump and Spoofing-like rules.

---

## Current Architecture

The project currently contains a functional multi-asset analytical layer and a broader macro-financial database layer.

### Current Asset Coverage

The main adapted asset scripts are:

| Asset | Script | SQL Table | Status |
|---|---|---|---|
| Bitcoin | `main.py` | `btc_analysis` | Completed |
| SP500 | `sp500.py` | `sp500_analysis` | Completed |
| STOXX600 | `stoxx600.py` | `stoxx600_analysis` | Completed |
| FTSE100 | `ftse100.py` | `ftse100_analysis` | Completed |
| Gold | `gold.py` | `gold_analysis` | Completed |
| DXY / USD Index | `dollaramericano.py` | `dxy_analysis` | Completed |
| Euro | `euro.py` | `euro_analysis` | Completed |
| Yuan | `yuan.py` | `yuan_analysis` | Completed |
| Libra / GBP | `libra.py` | `libra_analysis` | Completed |
| SSE Composite | `ssecomposite.py` | `ssecomposite_analysis` | Completed |

---

## Current Processing Pipeline

Each adapted asset script follows this logic:

```text
CSV
→ Base SQL import/update
→ Data loading from MySQL
→ Synthetic OHLC construction
→ Indicator calculation in memory
→ Manipulation/anomaly detection in memory
→ Optional SQL update
→ Plotly dashboard


By default, the adapted asset scripts use:

UPDATE_SQL = False

This means:

indicators are calculated in memory;
manipulation/anomaly flags are calculated in memory;
charts are generated quickly;
SQL is not updated with indicators unless explicitly enabled.

To force SQL updates for a specific asset, change inside that script:

UPDATE_SQL = True
Global Runner

The project includes a global runner:

run_all_assets.py

This script executes all adapted asset scripts sequentially and returns a summary.

Latest validation result:

Total scripts: 10
Success: 10
Errors: 0
Missing: 0
Main Technologies
Python
Pandas
NumPy
MySQL
SQLAlchemy
Plotly
Power BI
Future Streamlit
Future machine learning models
Main Features
Technical Indicators

The project calculates common technical indicators, including:

RSI
Stochastic RSI
MACD
MACD Percent
EMA 9
EMA 12
EMA 26
EMA 50
EMA 100
EMA 200
ATR
ADX
CCI
OBV
Bollinger Bands
Momentum
Price Change Percentage
Advanced Behavioural Indicators

The project also calculates advanced indicators in memory:

Volume Z-Score
Realized Volatility
Volatility of Volatility
Liquidity Stress
Drawdown Duration
Market Entropy

These advanced indicators are not yet persisted to SQL.

Risk Indicators

The broader analytical layer includes or plans to include:

volatility regimes;
drawdown analysis;
max drawdown;
Sharpe Ratio;
Sortino Ratio;
CAGR;
turnover ratio;
price vs EMA 200;
liquidity stress;
event impact scores;
macro-financial regime classification.
Behavioural Signals

The current heuristic risk detection layer includes:

Pump/Dump-like detection;
Spoofing-like detection;
abnormal volume detection;
RSI extreme tagging;
ATR high tagging;
volatility anomaly context.
Database Structure

The project stores processed analytical data inside a local MySQL database.

Main market tables include:

btc_analysis
sp500_analysis
stoxx600_analysis
ftse100_analysis
gold_analysis
dxy_analysis
euro_analysis
yuan_analysis
libra_analysis
ssecomposite_analysis

Additional analytical/reporting tables include:

btc_analysis_powerbi
bitcoin_historical_events
world_historical_events
crypto_news
world_news

The database also contains multiple FED, EU and ECB macro-financial tables related to:

credit;
deposits;
money supply;
interest rates;
financial stress;
consumer prices;
payment systems;
fraud losses;
balance sheet items;
national accounts;
government finance statistics.

Detailed database documentation will be maintained in:

DATABASE_SCHEMA.md
Visual Analytics

The system includes TradingView-style Plotly dashboards for the adapted assets.

Current chart components include:

synthetic candlestick charts;
EMAs;
Bollinger Bands;
volume bars;
RSI;
Stochastic RSI;
MACD;
MACD Percent;
manipulation/anomaly markers.

Future chart improvements planned:

dynamic asset titles;
optional chart display;
HTML export;
better legend layout;
date range filters;
recent-period view;
Streamlit integration.
Power BI / Reporting Layer

The project includes an enriched BTC dataset for Power BI-style reporting:

btc_analysis_powerbi

This table includes deeper analytical metrics such as:

multi-window returns;
rolling volatility;
drawdown;
max drawdown;
Sharpe Ratio;
Sortino Ratio;
CAGR;
turnover ratio;
price vs EMA 200;
event flags;
impact scores;
risk regime.

Future work may include:

equivalent reporting tables for other assets;
a unified multi-asset reporting table;
deciding which outputs remain in Power BI and which move to Streamlit.
Events and News Layer

The project contains historical and current event/news tables, including:

bitcoin_historical_events
world_historical_events
crypto_news
world_news

These are intended to support:

event timelines;
market reaction analysis;
macro context;
future sentiment scoring;
anomaly explanation;
crisis-period comparison.
Future Development
Generic Asset Processor

A future asset_processor.py module is planned to reduce repeated code across asset scripts.

Planned objectives:

centralize asset loading;
centralize common processing logic;
use asset_config.py for metadata;
reduce duplicated CSV/SQL/chart code;
simplify adding new assets.
Intermarket Analysis

Planned future development includes:

rolling correlations;
BTC vs DXY;
BTC vs Gold;
BTC vs SP500;
Gold vs DXY;
risk-on / risk-off behaviour;
capital flow analysis;
cross-market divergence;
crisis-period comparison.
Streamlit Platform

A future Streamlit application will serve as the main analytical interface.

Planned pages:

Overview;
Technical Indicators;
Risk Signals;
Macro Events;
News & Events;
Intermarket Analysis;
Power BI / Reporting Layer;
Machine Learning.
Machine Learning

Planned future development includes:

anomaly detection models;
regime classification;
clustering;
behavioural pattern detection;
feature importance;
temporal train/test validation;
leakage prevention;
model output dashboards.
Project Status

Current stage:

v0.2.1 — Multi-Asset Script Stabilization

Completed:

Core BTC modular pipeline validated;
main technical indicator module created;
risk detection module created;
chart module created;
10 main asset scripts adapted;
fast in-memory processing mode implemented;
optional SQL update mode implemented;
global runner created;
all 10 adapted asset scripts executed successfully;
database structure reviewed at high level;
documentation update in progress.

Still in progress:

database schema documentation;
chart improvements;
generic asset processor;
asset configuration improvements;
macro/FED/EU ingestion cleanup;
Streamlit implementation;
intermarket analysis;
machine learning layer.
Repository / Portfolio Notes

This repository is intended as a portfolio-oriented version of a local macro-financial analytics platform.

Database credentials, raw datasets, API keys and full local data exports are not included.

For public portfolio sharing, the following safeguards are in place:

no API keys in code;
.env used for secrets;
.env.example included;
raw CSV files excluded;
SQL database dumps excluded;
screenshots added;
database schema documented;
limitations clearly stated.
Disclaimer

This project is for educational, analytical and portfolio purposes only.

It does not provide financial advice.

Detected risk/manipulation signals are heuristic indicators and should not be interpreted as definitive proof of market manipulation or as trading recommendations.
