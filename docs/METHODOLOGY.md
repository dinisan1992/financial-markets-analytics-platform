# Methodology

Current version: v0.2.1

## Overview

This document explains the analytical methodology used in the Macro-Financial Risk & Market Behaviour Analytics Platform.

The project combines financial market data, macroeconomic indicators, historical events and news data to study market behaviour across different regimes.

The current methodology focuses on:

- multi-asset technical analysis;
- volatility and momentum behaviour;
- risk/anomaly signal detection;
- macro-financial context;
- event/news enrichment;
- future intermarket and machine learning analysis.

The current system should be interpreted as an analytical and educational framework, not as a trading system or a source of financial advice.

---

# 1. Data Sources

The project currently integrates several types of data.

## 1.1 Market Data

Market data includes assets such as:

- Bitcoin;
- SP500;
- STOXX600;
- FTSE100;
- Gold;
- DXY / US Dollar Index;
- Euro;
- Yuan;
- Libra / GBP;
- SSE Composite.

Each asset is processed through a Python script and stored in a MySQL table.

The core market tables include:

```text
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


1.2 Macroeconomic Data

The project also contains macroeconomic and financial system data from FED and EU/ECB sources.

These datasets include themes such as:

interest rates;
credit;
deposits;
M2 money supply;
financial stress;
card payments;
fraud losses;
consumer prices;
banking data;
government finance statistics;
payment systems.

This data is intended to provide macro-financial context for market movements.

1.3 Historical Events

The project includes historical event tables such as:

bitcoin_historical_events
world_historical_events

These tables are used to contextualize market behaviour around important events such as:

Bitcoin-specific events;
financial crises;
geopolitical events;
macroeconomic shocks;
regulatory events;
liquidity stress periods.
1.4 News Data

The project also contains current news tables such as:

crypto_news
world_news

These tables are intended to support:

news timelines;
anomaly explanation;
event-market relationship analysis;
future sentiment or narrative analysis.
2. Market Data Processing

Each adapted market asset follows a standardized processing pipeline:

CSV
→ Base SQL import/update
→ Data loading from MySQL
→ Synthetic OHLC construction
→ Indicator calculation in memory
→ Manipulation/anomaly detection in memory
→ Optional SQL update
→ Plotly dashboard

By default, the current processing mode is:

UPDATE_SQL = False

This means that indicators and anomaly flags are calculated in memory and are not written back to SQL unless explicitly enabled.

This approach was chosen because it:

avoids unnecessary repeated SQL updates;
improves execution speed;
keeps analysis flexible;
allows indicators to be recalculated dynamically;
reduces the risk of corrupting stored data during development.
3. Synthetic OHLC Construction

Some datasets only provide one price value per date.

To create candlestick-style charts and calculate technical indicators that require high, low, open and close values, the project creates synthetic OHLC values.

The current approximation is:

open = previous_day_price
close = current_day_price
high = max(open, close) * 1.01
low = min(open, close) * 0.99

This allows the project to build approximate candlestick charts even when full OHLC market data is not available.

3.1 Why Synthetic OHLC Is Used

Synthetic OHLC construction allows the project to:

visualize price movement in candlestick format;
calculate ATR;
calculate ADX;
calculate CCI;
estimate candle structure;
apply anomaly heuristics based on candle body and candle range.
3.2 Limitations of Synthetic OHLC

This method is an approximation.

It does not represent real intraday high and low prices.

Therefore:

ATR is approximate;
ADX is approximate;
CCI is approximate;
candle body/range logic is approximate;
manipulation/anomaly detection is heuristic, not definitive.

Future improvement:

replace synthetic OHLC with real OHLC data where available;
keep synthetic OHLC only for assets where detailed OHLC data is unavailable;
clearly flag synthetic OHLC usage in dashboards and documentation.
4. Technical Indicators

The project calculates a set of technical indicators for each asset.

These indicators are used to study:

trend;
momentum;
volatility;
price strength;
abnormal movements;
market stress.
4.1 RSI

The Relative Strength Index is used to detect overbought or oversold conditions.

Current thresholds used in charts and signal logic:

RSI > 80 → very high RSI
RSI < 20 → very low RSI

Additional reference levels are also displayed:

70 → overbought reference
30 → oversold reference
4.2 Stochastic RSI

Stochastic RSI is used to measure the position of RSI relative to its recent range.

The project calculates:

%K
%D

This provides a more sensitive momentum signal than RSI alone.

4.3 Exponential Moving Averages

The project calculates several EMAs:

EMA 9
EMA 12
EMA 26
EMA 50
EMA 100
EMA 200

These are used for:

short-term trend;
medium-term trend;
long-term trend;
trend alignment;
future price vs EMA analysis.
4.4 Bollinger Bands

Bollinger Bands are calculated using:

20-period moving average
± 2 standard deviations

They are used to analyze:

volatility expansion;
volatility compression;
price deviation from recent average;
possible stress or breakout conditions.
4.5 MACD

The MACD is calculated using:

EMA 12 - EMA 26

The MACD signal line is calculated using:

EMA 9 of MACD

The project also calculates:

MACD Percent = 100 * MACD / close

This helps normalize MACD relative to the asset price.

4.6 Momentum

The project calculates 10-period momentum:

momentum_10 = close - close.shift(10)

This helps identify short-term directional strength.

4.7 ATR

ATR is used to estimate volatility based on the synthetic high, low and close series.

Because OHLC is currently synthetic for several assets, ATR should be interpreted as an approximate volatility measure.

4.8 ADX

ADX is used to estimate trend strength.

Because high and low values are synthetic in several assets, ADX should be interpreted with caution.

4.9 CCI

CCI is used to identify deviation from typical price behaviour.

As with ATR and ADX, CCI depends on high, low and close values and is therefore approximate when synthetic OHLC is used.

4.10 OBV

On-Balance Volume is used to estimate volume flow direction based on price movement.

It is calculated using:

if price increases → add volume
if price decreases → subtract volume
if price unchanged → neutral
5. Advanced Behavioural Indicators

The project also calculates advanced indicators in memory.

These indicators are not yet persisted to SQL.

Current advanced indicators include:

volume_zscore
realized_volatility_30d
volatility_of_volatility
liquidity_stress
drawdown_duration
market_entropy
5.1 Volume Z-Score

Volume z-score measures how abnormal the current volume is compared to its recent history.

It is calculated using a rolling 20-period mean and standard deviation.

Purpose:

detect abnormal volume;
support anomaly detection;
identify unusual market activity.
5.2 Realized Volatility

Realized volatility is calculated using rolling standard deviation of returns.

Current window:

30 periods

Annualization currently uses:

sqrt(365)

This was originally chosen for Bitcoin/crypto, which trades continuously.

Future improvement:

use asset-specific annualization factors;
for crypto: 365;
for traditional markets: approximately 252.
5.3 Volatility of Volatility

Volatility of volatility measures instability in the volatility itself.

It is calculated as a rolling standard deviation of realized volatility.

Purpose:

identify unstable volatility regimes;
detect stress periods;
support future regime classification.
5.4 Liquidity Stress

Liquidity stress is calculated as:

realized_volatility_30d / rolling average volume

The intuition is that high volatility combined with weak liquidity may indicate stress.

Current limitation:

raw volume scales differ across assets;
this metric may need normalization before intermarket comparison.
5.5 Drawdown Duration

Drawdown duration counts how many consecutive periods an asset remains below its previous peak.

Purpose:

identify prolonged stress;
distinguish temporary drops from persistent weakness;
support future regime classification.
5.6 Market Entropy

Market entropy measures the dispersion/uncertainty of recent returns.

Higher entropy may suggest more unstable or less predictable market behaviour.

Current method:

calculate returns;
divide recent returns into histogram bins;
calculate entropy from the probability distribution.

Future improvement:

test different rolling windows;
test different bin counts;
compare entropy behaviour across assets and crisis periods.
6. Anomaly and Manipulation Signal Detection

The current project includes a heuristic risk detection layer.

This layer identifies possible abnormal behaviour using:

abnormal volume;
candle body/range structure;
price variation;
RSI extremes;
ATR spikes.

Important note:

These are not definitive manipulation labels.

They are risk/anomaly signals intended to highlight periods that deserve further investigation.

6.1 Abnormal Volume

The project identifies abnormal volume using:

volume > rolling_mean_20 + 2.5 * rolling_std_20

This means volume must be significantly above recent normal behaviour before any Pump/Dump or Spoofing-like signal is considered.

6.2 Pump/Dump-Like Signal

A Pump/Dump-like signal is flagged when:

abnormal volume
+
large candle body relative to total candle range
+
large price variation

Current logic:

volume_anormal = True
candle_ratio > 0.5
price_change_abs > 5%

The output label is:

Pump/Dump likely

Interpretation:

This indicates a strong abnormal movement with high volume and significant price displacement.

It does not prove manipulation.

6.3 Spoofing-Like Signal

A Spoofing-like signal is flagged when:

abnormal volume
+
small candle body
+
small price variation

Current logic:

volume_anormal = True
candle_ratio < 0.3
price_change_abs < 0.5%

The output label is:

Spoofing likely

Interpretation:

This indicates abnormal volume without meaningful price movement.

It may represent unusual market activity, but it does not prove spoofing.

6.4 RSI Context

If a risk signal is detected, the system adds RSI context.

Current rules:

RSI > 80 → RSI muito alto
RSI < 20 → RSI muito baixo

This helps distinguish whether a signal occurred during extreme momentum conditions.

6.5 ATR Context

If a risk signal is detected, the system checks whether ATR is unusually high.

Current rule:

ATR > 1.5 * rolling_mean_ATR_20

If true, the signal receives:

ATR alto

This indicates that the signal occurred during a high-volatility context.

7. Risk Regime and Reporting Metrics

The Power BI/reporting layer includes deeper metrics such as:

return_1d
return_7d
return_30d
return_60d
return_90d
return_360d
rolling_volatility_30d
drawdown_pct
max_drawdown_pct
sharpe_ratio
sortino_ratio
turnover_ratio
price_vs_ema_200
cagr
risk_regime

These metrics are mainly used in:

btc_analysis_powerbi

Future development may extend similar reporting logic to other assets.

8. Event Impact Methodology

The project includes historical Bitcoin events and broader world events.

Current event impact logic connects event dates or event years to market behaviour.

8.1 Bitcoin Events

Bitcoin events are mapped by event date.

Potential event-related fields include:

event_date
event_title
impact
category
price_reaction

These events can be used to analyze:

price movement on event day;
volatility around event date;
drawdown after event;
event severity;
regime changes.
8.2 World Events

World events are currently more approximate because some are mapped by year rather than exact date.

This allows broad contextual analysis but limits daily precision.

Current limitation:

year-level mapping is too broad for precise event impact analysis

Future improvement:

add exact event dates where possible
add event windows
add event severity
add affected markets
add source references
8.3 Impact Scores

The current reporting logic includes experimental impact score calculations.

These are based on relationships between:

return;
volatility;
market cap adjustment;
event flags.

These scores are useful for exploratory analysis but should not yet be interpreted as final causal measures.

Future improvements:

use event windows;
compare pre-event and post-event volatility;
measure abnormal returns;
normalize across assets;
separate market events from macro/geopolitical events.
9. Intermarket Analysis Methodology

The intermarket analysis layer is planned but not yet implemented.

Future methodology will include:

rolling correlations;
dynamic beta;
relative strength;
risk-on/risk-off behaviour;
capital flow analysis;
crisis-period comparison.
9.1 Rolling Correlations

Potential asset pairs:

BTC vs DXY
BTC vs GOLD
BTC vs SP500
GOLD vs DXY
SP500 vs DXY
FTSE100 vs GBP
SSE Composite vs Yuan

Purpose:

detect changing market relationships;
identify correlation breakdowns;
compare stress vs stable periods.
9.2 Risk-On / Risk-Off Analysis

Future risk-on/risk-off logic may combine:

equity performance;
DXY strength;
gold behaviour;
Bitcoin behaviour;
volatility regimes;
macro stress indicators.

Possible interpretation:

Equities up + DXY down → risk-on tendency
Gold up + DXY up + equities down → risk-off/stress tendency
BTC correlation shift → speculative/liquidity regime change
9.3 Capital Flow Analysis

Capital flow analysis will attempt to understand how money may rotate between:

equities;
crypto;
gold;
currencies;
liquidity-sensitive assets.

This will likely require normalization and relative performance metrics.

10. Machine Learning Methodology

The machine learning layer is planned for a later phase.

Potential objectives:

anomaly detection;
regime classification;
clustering;
feature importance;
behavioural pattern detection.
10.1 Candidate Features

Potential ML features include:

returns
rolling volatility
drawdown
drawdown duration
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
macro indicators
news features
10.2 Data Leakage Prevention

Future ML work must avoid data leakage.

Important principles:

use time-based train/test split;
never use future values to predict past events;
calculate rolling features only from past data;
avoid random shuffling for time-series validation;
keep event features aligned with publication/event dates.
10.3 Model Types

Potential model families:

Isolation Forest
One-Class SVM
K-Means / clustering
HDBSCAN
Random Forest
Gradient Boosting
LSTM or sequence models later

The first ML phase should likely focus on unsupervised anomaly detection and regime clustering.

11. Visualization Methodology

The current visualization layer uses Plotly.

Each asset dashboard includes:

price/candlestick panel;
volume panel;
RSI/Stoch RSI panel;
MACD panel;
manipulation/anomaly markers.

The goal is to create a TradingView-style analytical interface while keeping the logic transparent and reproducible.

Future improvements:

Streamlit integration;
date range filters;
indicator toggles;
export to HTML;
comparison charts;
intermarket dashboards;
macro overlays.
12. Current Limitations

The current methodology has important limitations.

12.1 Synthetic OHLC

Several assets use synthetic OHLC data rather than real OHLC.

This limits the precision of:

candlestick interpretation;
ATR;
ADX;
CCI;
candle body/range anomaly logic.
12.2 Heuristic Signals

Manipulation/anomaly signals are heuristic.

They should not be interpreted as definitive proof of market manipulation.

They are useful for identifying dates that deserve further investigation.

12.3 Macro Data Standardization

FED and EU/ECB tables are not yet standardized.

Future work is required to:

normalize date fields;
prevent duplicated observations;
create macro features;
align macro data with market data.
12.4 Event Mapping

Some world events are mapped by year rather than exact date.

This is useful for broad context but not precise enough for event-window analysis.

12.5 Asset Comparability

Different assets have different:

trading calendars;
volume scales;
liquidity profiles;
volatility structures;
data availability.

Future intermarket analysis must normalize these differences carefully.

13. Future Methodology Improvements

Planned improvements include:

real OHLC data where possible;
asset-specific volatility annualization;
generic asset processor;
standardized macro ingestion;
exact event date mapping;
event window analysis;
rolling correlation engine;
intermarket dashboards;
Streamlit platform;
anomaly detection models;
regime classification models;
explainable feature importance.
14. Disclaimer

This project is for educational, analytical and portfolio purposes only.

It does not provide financial advice.

The risk/manipulation signals generated by the system are heuristic indicators and should not be interpreted as definitive proof of manipulation, fraud or unlawful market activity.

All results should be interpreted with caution and validated with additional data, methodology and domain knowledge.