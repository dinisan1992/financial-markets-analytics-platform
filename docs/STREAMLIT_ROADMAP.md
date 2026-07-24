# Streamlit Roadmap

## Objective

Build an interactive analytical platform using Streamlit, Plotly and MySQL to explore market behaviour, technical indicators, risk signals, macro-financial regimes, event impact and future anomaly detection.

The Streamlit layer will act as the interactive front-end of the project, while the current Python/MySQL pipeline remains the data processing backbone.

---

## Core Stack

- Python
- Streamlit
- Plotly
- Pandas
- NumPy
- MySQL
- SQLAlchemy
- Future ML models

---

## Current Project Context

The project currently has a functional multi-asset pipeline for:

- Bitcoin
- SP500
- STOXX600
- FTSE100
- Gold
- DXY / USD Index
- Euro
- Yuan
- Libra / GBP
- SSE Composite

Each asset script currently supports:

- CSV import/update
- MySQL loading
- synthetic OHLC construction
- technical indicators
- manipulation/anomaly heuristics
- Plotly dashboard generation
- optional SQL update mode through `UPDATE_SQL`

The Streamlit application should not replace the current scripts immediately. It should first consume the processed data and gradually become the main user interface.

---

## Planned App Structure

```text
app.py

pages/
├── 01_Overview.py
├── 02_Technical_Indicators.py
├── 03_Risk_Signals.py
├── 04_Macro_Events.py
├── 05_Intermarket_Analysis.py
├── 06_News_Events.py
├── 07_PowerBI_Reporting.py
└── 08_Machine_Learning.py


Page 1 — Overview

Purpose:

provide a high-level view of all tracked assets;
show latest price values;
show recent returns;
show volatility status;
show risk regime summary;
show manipulation/anomaly signal count.

Possible elements:

asset selector;
latest price cards;
market overview table;
recent performance chart;
volatility ranking;
signal summary.

Assets included:

BTC
SP500
STOXX600
FTSE100
GOLD
DXY
EURO
YUAN
LIBRA
SSE COMPOSITE

Page 2 — Technical Indicators

Purpose:

recreate the current Plotly dashboard inside Streamlit;
allow the user to select one asset;
display technical indicators interactively.

Features:

asset dropdown;
date range selector;
candlestick chart;
EMAs;
Bollinger Bands;
volume;
RSI;
Stochastic RSI;
MACD;
manipulation markers.

Future improvements:

toggle indicators on/off;
compare multiple assets;
export chart as HTML;
show only selected time period.

Page 3 — Risk Signals

Purpose:

focus on manipulation/anomaly detection;
display days flagged by the heuristic model;
help interpret abnormal market behaviour.

Features:

table of detected signals;
filter by asset;
filter by signal type;
Pump/Dump probable events;
Spoofing probable events;
RSI extreme tags;
ATR high tags;
volume anomaly context.

Possible metrics:

total signals by asset;
signals by year;
strongest abnormal volume days;
largest price-change days;
overlap between RSI extremes and volatility spikes.

Important note:

The current system detects heuristic risk signals. These should be presented as possible anomaly signals, not as proof of manipulation.

Page 4 — Macro Events

Purpose:

connect market behaviour with macro and historical events.

Data sources:

bitcoin_historical_events
world_historical_events
FED tables
EU / ECB tables

Possible features:

event timeline;
market movement around event dates;
BTC historical events;
world macro events;
affected markets;
event category;
event impact classification.

Future improvements:

event severity score;
exact event dates for world events;
event window analysis;
before/after returns;
volatility change around events.

Page 5 — Intermarket Analysis

Purpose:

study relationships between assets;
identify risk-on/risk-off behaviour;
analyse correlation changes across time.

Potential features:

rolling correlations;
BTC vs DXY;
BTC vs GOLD;
BTC vs SP500;
GOLD vs DXY;
SP500 vs DXY;
crisis-period comparison;
correlation breakdown detection;
divergence signals.

Possible metrics:

30-day rolling correlation;
90-day rolling correlation;
dynamic beta;
relative strength;
drawdown comparison;
volatility comparison.

Future objective:

Build a capital-flow analysis layer that helps understand how markets behave during stress periods versus stable periods.

Page 6 — News & Events

Purpose:

display current and historical news/events relevant to market behaviour.

Data sources:

crypto_news
world_news
bitcoin_historical_events
world_historical_events

Possible features:

searchable news table;
filter by source;
filter by country;
filter by category;
filter by asset;
event/news timeline;
link news to market movement;
show market reaction after publication date.

Future improvements:

sentiment scoring;
topic classification;
event clustering;
anomaly explanation using news context.

Page 7 — Power BI / Reporting Layer

Purpose:

document and inspect the reporting datasets created for Power BI or alternative BI tools.

Initial dataset:

btc_analysis_powerbi

Possible features:

show enriched BTC dataset;
returns over multiple windows;
rolling volatility;
drawdown;
Sharpe ratio;
Sortino ratio;
CAGR;
risk regime;
event flags;
impact scores.

Future direction:

create equivalent reporting datasets for other assets;
create a unified multi-asset reporting table;
decide which outputs remain in Power BI and which move to Streamlit.

Page 8 — Machine Learning

Purpose:

future machine learning layer for anomaly detection and regime classification.

Future models:

anomaly detection;
clustering;
regime classification;
feature importance;
time-series validation.

Potential features:

feature selection;
model output dashboard;
anomaly score by date;
regime label by period;
explainable indicators;
train/test split by time;
avoid data leakage.

Candidate features:

returns;
volatility;
drawdown;
RSI;
MACD percent;
ATR;
ADX;
CCI;
OBV;
volume z-score;
liquidity stress;
market entropy;
macro indicators;
event flags.


Development Phases
Phase 1 — Basic Streamlit Skeleton
create app.py;
create pages/ folder;
connect to MySQL;
load one asset;
display simple line chart;
add asset selector.

Phase 2 — Technical Dashboard
reuse logic from charts.py;
embed Plotly charts in Streamlit;
add date filters;
add indicator toggles;
add manipulation markers.

Phase 3 — Multi-Asset Overview
load all market asset tables;
create asset summary cards;
compare recent returns;
compare volatility;
compare risk signals.

Phase 4 — Macro/Event Layer
display historical events;
display macro tables;
connect events to asset movements;
create event timeline.

Phase 5 — Intermarket Analysis
rolling correlations;
asset pair comparison;
crisis-period comparison;
risk-on/risk-off indicators.

Phase 6 — ML Preparation
create feature datasets;
normalize data;
handle missing values;
create training windows;
avoid leakage;
run first anomaly detection models.


Required Refactors Before Streamlit

Before building the full Streamlit app, the following improvements are recommended:

improve charts.py to accept asset name as parameter;
add optional show_chart argument;
add optional HTML export;
create reusable data loading functions;
improve asset_config.py;
create asset_processor.py;
standardize table metadata;
document database schema;
clean duplicated asset script logic.
Streamlit Design Principles

The dashboard should be:

simple;
fast;
modular;
data-driven;
suitable for portfolio presentation;
honest about limitations;
focused on analysis, not trading advice.
Portfolio Value

The Streamlit version will make the project easier to demonstrate in interviews because it will show:

data engineering;
SQL integration;
financial analytics;
technical indicators;
risk logic;
macro-financial context;
visual analytics;
future ML readiness.


Current Status

Current status:

Planned

The project is not yet in Streamlit implementation phase.

Current priority before Streamlit:

1. Finish documentation
2. Create DATABASE_SCHEMA.md
3. Improve charts.py
4. Create asset_processor.py
5. Clean macro/FED/EU ingestion scripts
Target Milestone

Future milestone:

v0.5.0 — Streamlit Interactive Dashboard
