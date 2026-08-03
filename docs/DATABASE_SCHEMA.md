# Database Schema

Current version: v0.5.0

## Overview

This document describes the current MySQL database structure used by the Macro-Financial Risk & Market Behaviour Analytics Platform.

The database supports several analytical layers:

- market asset analysis;
- technical indicators;
- risk/manipulation signal detection;
- Power BI / reporting datasets;
- historical events;
- current news;
- FED macroeconomic data;
- EU / ECB macro-financial data.

The main database currently used by the project is:

```text
btc_data


Database Layers

The database can be divided into six main groups:

1. Market asset analysis tables
2. Power BI / reporting tables
3. Historical event tables
4. News tables
5. FED macroeconomic tables
6. EU / ECB macro-financial tables
1. Market Asset Analysis Tables

These tables store the main financial market data and technical indicators.

Main Tables
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
us3m_analysis
us2y_analysis
Common Purpose

These tables are used to store:

timestamp/date;
asset price;
market cap where available;
total volume;
technical indicators;
manipulation/anomaly flags;
price change percentage.

They are the main source for the asset scripts and Plotly dashboards.

Common Columns

Most market asset tables follow a similar structure:

snapped_at
price
market_cap
total_volume
rsi
ema_9
ema_12
ema_26
ema_50
ema_100
ema_200
volume_sma_9
bb_middle
bb_upper
bb_lower
stoch_rsi
macd
macd_signal
momentum_10
atr
adx
cci
obv
macd_percent
manipulation
price_change_pct

Some tables may not contain all columns or may differ slightly depending on when they were created.

Treasury source identity in v0.5.1:

- `us3m_analysis` stores Yahoo `^IRX`, identified by Yahoo as the 13-week Treasury bill yield, including native OHLC;
- `us2y_analysis` stores Federal Reserve H.15 `RIFLGFCY02_N.B` / FRED `DGS2`; source OHLC is null and is synthesized only inside the analytical engine;
- `us2y_analysis__pre_v051_20260803_172148` is a retained local recovery copy of the pre-correction table and is not used by the application.

Table: btc_analysis

Purpose:

Stores Bitcoin market data, technical indicators and manipulation/anomaly flags.

Main usage:

BTC core pipeline;
Plotly BTC dashboard;
Power BI dataset generation;
event impact enrichment;
future machine learning features.

Important characteristics:

snapped_at is used as the main time key.
This table is the most developed market table.
It acts as the reference structure for other market assets.
Table: sp500_analysis

Purpose:

Stores SP500 data and calculated indicators.

Main usage:

SP500 dashboard;
future intermarket analysis;
comparison with BTC, GOLD and DXY.

Current note:

This table follows the same analytical logic as BTC but should later be checked for unique constraints on snapped_at.

Table: stoxx600_analysis

Purpose:

Stores STOXX600 data and calculated indicators.

Main usage:

European equity market analysis;
comparison with SP500 and FTSE100;
future regional risk analysis.

Current note:

This table is part of the main adapted multi-asset pipeline.

Table: ftse100_analysis

Purpose:

Stores FTSE100 data and calculated indicators.

Main usage:

UK equity market analysis;
comparison with STOXX600 and SP500;
future GBP/UK market context.
Table: gold_analysis

Purpose:

Stores Gold market data and calculated indicators.

Main usage:

risk-off analysis;
inflation regime comparison;
BTC vs GOLD analysis;
GOLD vs DXY analysis.

Gold is important as a defensive or safe-haven asset in future intermarket analysis.

Table: dxy_analysis

Purpose:

Stores DXY / USD Index data and calculated indicators.

Main usage:

USD strength analysis;
BTC vs DXY;
GOLD vs DXY;
SP500 vs DXY;
liquidity and risk-off analysis.

This table is central to the future capital-flow and macro-financial behaviour layer.

Table: euro_analysis

Purpose:

Stores Euro-related market data and calculated indicators.

Main usage:

currency behaviour analysis;
comparison with DXY;
European macro-financial context.
Table: yuan_analysis

Purpose:

Stores Yuan-related market data and calculated indicators.

Main usage:

currency behaviour analysis;
China-related macro-financial context;
comparison with DXY and SSE Composite.
Table: libra_analysis

Purpose:

Stores GBP / Libra-related market data and calculated indicators.

Main usage:

currency behaviour analysis;
UK market context;
comparison with FTSE100 and DXY.
Table: ssecomposite_analysis

Purpose:

Stores SSE Composite market data and calculated indicators.

Main usage:

Chinese equity market analysis;
comparison with Yuan;
global equity market comparison;
future crisis/regime analysis.
Current Asset Processing Mode

All adapted asset scripts currently use:

UPDATE_SQL = False

This means:

data is loaded from SQL;
indicators are calculated in memory;
manipulation/anomaly flags are calculated in memory;
charts are generated quickly;
SQL indicators are not updated unless explicitly enabled.

To persist indicators and manipulation flags into SQL for a specific asset, set:

UPDATE_SQL = True

inside that asset script.

2. Power BI / Reporting Tables
Table: btc_analysis_powerbi

Purpose:

This table acts as an enriched analytical/reporting dataset for Bitcoin.

Although originally designed for Power BI, it also works as a feature-rich analytical table.

Main Metrics

The table includes several advanced metrics such as:

return_1d
return_7d
return_30d
return_60d
return_90d
return_360d
rolling_volatility_30d
drawdown_pct
max_drawdown_pct
sharpe_ratio_30d
sharpe_ratio_90d
sharpe_ratio_360d
sortino_ratio_30d
sortino_ratio_90d
sortino_ratio_360d
turnover_ratio
price_vs_ema_200
volatility_flag
market_cap_adj
impact_score_market_adj
impact_score_world_adj
price_usd_log
trend_strength_index
cagr
impact_type_market
impact_type_world
risk_regime
Event Enrichment

This table also includes event-related columns such as:

btc_event_flag
btc_event_title
btc_event_impact
btc_event_category
world_event_flag
world_event_title
world_event_impact
affected_markets
Current Limitations
Currently BTC-specific.
World events are currently mapped broadly by year.
Future improvement should map events by exact date where possible.
Similar reporting tables may later be created for other assets.
A unified multi-asset reporting table may be preferable in the future.
3. Historical Event Tables
Table: bitcoin_historical_events

Purpose:

Stores important historical Bitcoin-related events.

Main columns include:

year
event_date
event_title
description
impact
price_reaction
category
Usage

This table is used to contextualize Bitcoin market movements around major events.

Possible future uses:

event window analysis;
before/after return calculation;
volatility impact;
event severity scoring;
ML event features.
Table: world_historical_events

Purpose:

Stores important macro/geopolitical/world events.

Main columns include:

year
event
macro_impact
affected_markets
Usage

This table is used to provide macro context for market behaviour.

Current limitation:

events are currently stored mainly by year;
this makes daily event impact analysis approximate.

Future improvement:

event_date
event_start_date
event_end_date
severity
category
affected_markets
source
4. News Tables
Table: crypto_news

Purpose:

Stores current cryptocurrency-related news.

Main columns include:

news_id
snapped_at
title
description
source
original_url
panic_score
inserted_at

Depending on API response availability, some fields may be null.

Usage

Potential uses:

crypto news timeline;
BTC event context;
future sentiment scoring;
anomaly explanation;
news-event correlation.
Notes

This table has protection against duplicated news through fields such as URL/title/date combinations.

Important:

API keys must never be stored directly in the repository.

Table: world_news

Purpose:

Stores broader world/current news.

Main columns include:

article_id
snapped_at
title
description
content
original_url
source_name
source_url
country
category
language
inserted_at
link
Usage

Potential uses:

macro news timeline;
geopolitical context;
event classification;
future sentiment or narrative analysis;
connection between news and market moves.
5. FED Macroeconomic Tables

The database includes several FED-related tables.

These tables support the macro-financial layer of the project.

FED Tables
fed_bank_credit
fed_charge_off_rate_credit_cards
fed_consumer_loans_credit_cards
fed_credit_card_delinquency
fed_deposits
fed_federal_funds_rate
fed_loans_leases
fed_m2
fed_reserve_bank_credit
fed_securities_bank_credit
fed_total_assets
Purpose

These tables provide macroeconomic and financial context related to:

bank credit;
deposits;
consumer credit;
credit card delinquency;
charge-off rates;
M2 money supply;
federal funds rate;
reserve bank credit;
total assets;
loans and leases;
securities bank credit.
Typical Structure

Most FED tables follow a simple time-series structure:

observation_date
value

or:

id
observation_date
metric_value

The value column name differs by dataset.

Current Limitations

Some FED tables use observation_date as primary key or unique date field.

Other FED tables may use an auto-increment id, which can allow duplicated observation dates if ingestion scripts are run multiple times without duplicate checks.

Tables that should be reviewed for unique date protection include:

fed_bank_credit
fed_charge_off_rate_credit_cards
fed_consumer_loans_credit_cards
fed_total_assets
Future Improvements

Recommended improvements:

standardize FED ingestion scripts;
prevent duplicate observation dates;
add unique constraints where appropriate;
document each FED table individually;
create macro feature calculations;
create macro charts;
create macro stress indicators.

Possible future macro indicators:

pct_change
rolling_mean
rolling_std
z_score
trend_deviation
macro_stress_flag
6. EU / ECB Macro-Financial Tables

The database also contains a large EU / ECB macro-financial data layer.

EU / ECB Tables
euro_atm_pos_transactions
euro_balance_sheet_items
euro_bank_lending_survey
euro_card_payments
euro_card_payments_by_merchant_category
euro_composite_indicator_stress
euro_country_level_financial_stress
euro_credit_transfers
euro_direct_debits
euro_emoney_payment_transactions
euro_government_finance_statistics
euro_indices_consumer_prices
euro_losses_due_to_fraud
euro_main_aggregates_national_accounts
euro_mfi_interest_rate_statistics
euro_retail_interest_rates
euro_transactions_payments_systems
Purpose

These tables support European macro-financial analysis.

They include data related to:

payment systems;
card payments;
ATM/POS transactions;
fraud losses;
financial stress;
consumer prices;
bank lending;
credit transfers;
direct debits;
e-money transactions;
balance sheet items;
interest rates;
government finance;
national accounts.
Analytical Value

This layer is important because it allows the project to connect market behaviour with:

macroeconomic cycles;
financial stress;
payment activity;
credit conditions;
inflation;
fraud/payment risk;
banking sector behaviour;
European financial system indicators.
Current Limitations

EU / ECB tables are heterogeneous.

They often contain different combinations of:

date
country
sector
instrument
frequency
unit
value
category
indicator

This means they should not be processed like market asset tables.

Future Improvements

Recommended improvements:

standardize EU/ECB ingestion scripts;
document each table;
identify key useful indicators;
create macro feature tables;
normalize date fields;
create country/region filters;
create stress indicators;
connect macro features to market regimes.
7. Suggested Logical Architecture

The database should be understood as three separate analytical engines.

Engine 1 — Market Assets

Tables:

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

Purpose:

technical indicators;
risk signals;
asset dashboards;
intermarket analysis;
future ML features.

Main modules:

indicators.py
risk_detection.py
charts.py
asset_config.py
future asset_processor.py
Engine 2 — Macro / FED / EU

Tables:

FED tables
EU / ECB tables

Purpose:

macro-financial context;
stress regimes;
liquidity conditions;
credit cycle analysis;
fraud/payment system indicators;
macro overlays.

Future modules:

macro_ingestion.py
macro_analysis.py
macro_charts.py
macro_features.py
Engine 3 — Events / News

Tables:

bitcoin_historical_events
world_historical_events
crypto_news
world_news

Purpose:

event timelines;
historical context;
news context;
anomaly explanation;
event impact analysis;
future sentiment/narrative scoring.

Future modules:

event_analysis.py
news_analysis.py
sentiment_analysis.py
8. Current Known Issues
1. Market Daily-Key Constraints

The v0.5.0 remediation cycle consolidated EURO, YUAN, LIBRA and SSECOMPOSITE to one row per date and added unique `snapped_at` keys to SP500, GOLD, DXY and those four legacy tables. BTC, STOXX600 and the newer market tables already use unique daily keys.

The migration was performed through validated shadow tables and an atomic rename. The seven previous tables remain available locally under `__pre_v050_20260803` names for rollback and are not part of the public repository.

2. Row-by-Row SQL Updates

Current optional SQL update mode updates indicators row by row.

This works, but may be slow for larger datasets.

Future improvements:

update only rows with null indicators;
use batch updates;
use temporary tables;
use SQLAlchemy more consistently.
3. Raw MySQL Connector Warnings

Some scripts still use:

pd.read_sql(query, conn)

with raw MySQL connector connections.

This causes pandas warnings.

Future improvement:

from sqlalchemy import create_engine
from config import get_sqlalchemy_database_url

engine = create_engine(get_sqlalchemy_database_url())
df = pd.read_sql(query, engine)
4. Advanced Indicators Not Persisted

The following indicators are currently calculated only in memory:

volume_zscore
realized_volatility_30d
volatility_of_volatility
liquidity_stress
drawdown_duration
market_entropy

Future decision required:

persist selected indicators to SQL;
keep them as reporting-only features;
use them only for ML/Streamlit.
5. Event Mapping Needs Improvement

Current event mapping is useful but still basic.

Future improvements:

exact event dates;
event windows;
severity scores;
source references;
category standardization;
event-market relationship scoring.
9. Recommended Future SQL Improvements
Market Tables

Keep the v0.5.0 daily-key invariant and route future market CSV refreshes through `project_scripts/assets/sync_market_data.py`. Each write must begin with a reviewed dry-run and a scoped backup. Do not restore the legacy import loops that performed unconditional inserts.

FED Tables

Completed in v0.5.3 after duplicate/null checks and a scoped SQL backup:

ALTER TABLE fed_bank_credit ADD UNIQUE KEY unique_observation_date (observation_date);
ALTER TABLE fed_charge_off_rate_credit_cards ADD UNIQUE KEY unique_observation_date (observation_date);
ALTER TABLE fed_consumer_loans_credit_cards ADD UNIQUE KEY unique_observation_date (observation_date);
ALTER TABLE fed_total_assets ADD UNIQUE KEY unique_observation_date (observation_date);

All four tables retained their original row counts and date ranges. Future FED
refreshes must continue through the backup-gated macro import service.

Reporting Tables

For btc_analysis_powerbi, future indexing may improve performance:

ALTER TABLE btc_analysis_powerbi ADD INDEX idx_date (date);

If the table becomes multi-asset:

ALTER TABLE btc_analysis_powerbi ADD INDEX idx_market_date (market, date);
10. Future Documentation Tasks

Each table group should eventually have deeper documentation.

Market Tables

Document:

source;
date range;
frequency;
price field;
volume field;
indicator fields;
known limitations.
Macro Tables

Document:

source;
frequency;
value column;
country/region;
unit;
transformation logic;
economic interpretation.
Event / News Tables

Document:

source;
date logic;
category;
event type;
impact logic;
limitations.
11. Current Database Status

Current status:

Functional local analytical database

Strengths:

strong market coverage;
multi-asset analytical structure;
historical event layer;
current news layer;
FED macro layer;
EU/ECB macro layer;
Power BI/reporting layer;
suitable for future Streamlit and ML work.

Weaknesses:

some table structures are inconsistent;
some unique constraints need review;
macro tables need standardization;
event mapping needs improvement;
advanced indicators are not yet persisted;
documentation is still being expanded.
12. Portfolio Interpretation

This database shows that the project is not only a charting script.

It supports a broader analytical platform involving:

data ingestion;
SQL database design;
financial feature engineering;
risk signal detection;
macro-financial context;
event/news enrichment;
reporting datasets;
future ML readiness.

This database is one of the strongest parts of the project and is documented here for the public portfolio version.

13. Public Repository Notes

The public repository should not include:

raw CSV datasets
full SQL dumps
API keys
database credentials
large local exports
Power BI private files

The repository may include:

schema documentation
sample/mock data
README
methodology
screenshots
code
requirements
roadmap
known limitations
14. Disclaimer

This database and project are for educational, analytical and portfolio purposes only.

The risk/manipulation signals are heuristic indicators and should not be interpreted as definitive proof of market manipulation or as financial advice.
