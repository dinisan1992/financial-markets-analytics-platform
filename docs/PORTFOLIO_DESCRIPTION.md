# Macro-Financial Risk & Market Behaviour Analytics Platform

## Project Overview

This project is a macro-financial analytics platform built with Python, MySQL, Plotly and Streamlit.

The goal is to analyse market behaviour across multiple asset classes, combine technical indicators with macroeconomic data, detect suspicious market activity patterns, and provide an interactive dashboard for exploratory financial analysis.

The platform integrates crypto, equity indices, commodities, FX, volatility indices, bond yields, FED indicators and selected EURO macroeconomic series.

It was designed as a portfolio project to demonstrate practical skills in data engineering, data analysis, financial analytics, risk monitoring, dashboard development and analytical storytelling.

---

## Business Problem

Financial markets are influenced by multiple layers of information:

- price behaviour
- liquidity conditions
- interest rates
- inflation
- credit stress
- volatility regimes
- macroeconomic cycles
- geopolitical and crisis events
- abnormal trading behaviour

Traditional single-asset analysis often misses the broader context.

This project aims to answer questions such as:

- How do different assets behave during liquidity expansion or tightening?
- How do BTC, equities, gold, DXY, volatility and yields interact over time?
- Do correlations change during crisis periods?
- Can abnormal market behaviour be flagged using price, volume and technical indicators?
- How do FED and EURO macro indicators relate to market performance?
- Which assets react more strongly during risk-off regimes?
- Can suspicious events such as potential pump/dump, spoofing-like behaviour or volume spikes be identified?

---

## Technical Architecture

The project follows a modular architecture:

```text
CSV / API / SQL data
        ↓
Python data ingestion
        ↓
MySQL database
        ↓
Data cleaning and validation
        ↓
Technical indicators
        ↓
Risk and manipulation detection
        ↓
Macro-financial analysis
        ↓
Plotly visualizations
        ↓
Streamlit dashboard


Main components:

asset_config.py
    Central configuration for market assets

macro_config.py
    FED macroeconomic configuration

euro_series_config.py
    EURO macroeconomic configuration

database.py
    Database connection and SQL helpers

indicators.py
    Technical indicator calculations

risk_detection.py
    Market behaviour and manipulation heuristics

charts.py
    Plotly charting functions

macro_data_loader.py
    FED macro and market alignment

euro_data_loader.py
    EURO macro and market alignment

dashboard/
    Streamlit dashboard modules
Data Pipeline

The project uses a local MySQL database as the analytical data store.

The general process is:

Import raw CSV files and API data
Clean date, price and volume fields
Normalize asset tables
Store structured time series in MySQL
Load data into Python using pandas and SQLAlchemy
Calculate indicators and analytical features
Generate visualizations with Plotly
Display results in Streamlit

The database includes historical data for crypto, equity indices, commodities, currencies, yields, volatility indicators and macroeconomic indicators.

Market Data Layer

The platform supports multiple asset classes, including:

Crypto
Bitcoin
Equity Indices
S&P 500
NASDAQ 100
STOXX 600
FTSE 100
DAX
CAC 40
Dow Jones
Nikkei 225
Russell 2000
SSE Composite
Commodities
Gold
Silver
Copper
Wheat
Corn
Brent Oil
WTI Oil
Natural Gas
FX / Currency Indicators
DXY / US Dollar Index
Euro
British Pound
Chinese Yuan
Japanese Yen
Swiss Franc
Rates / Yields
US 2Y
US 10Y
US 30Y
Germany 10Y
UK 10Y
Japan 10Y
Volatility / Stress Indicators
VIX
MOVE Index
TED Spread
Financial Conditions indicators
Technical Indicators

The platform calculates a broad range of technical indicators and market behaviour metrics:

Synthetic OHLC construction
Daily returns
Price change percentage
EMAs: 9, 20, 50, 100, 200
Bollinger Bands
RSI
Stochastic RSI
MACD
MACD signal
MACD histogram
Rolling volatility
Drawdown
Rolling maximum
Volume moving average
Volume z-score
Candle body ratio
Body-to-range ratio

These indicators support both visual analysis and suspicious event detection.

Risk and Manipulation Detection

One of the key features of the project is the detection of abnormal or suspicious market behaviour.

The current rule-based detection layer flags:

Volume Spikes

A volume spike is detected when volume is significantly above its recent average.

Example logic:

volume_zscore > 2.5
Possible Pump/Dump

A possible pump/dump event is flagged when there is:

high volume spike
large price movement
large candle body relative to range

Example logic:

volume_zscore > 2.5
absolute price change > 5%
body_to_range > 0.5
Possible Spoofing-Like Behaviour

A possible spoofing-like event is flagged when there is:

high volume spike
small price movement
small candle body relative to range

Example logic:

volume_zscore > 2.5
absolute price change < 0.5%
body_to_range < 0.3
Extreme RSI Context

The platform also flags extreme RSI conditions:

RSI > 80
RSI < 20

Each suspicious event receives a human-readable explanation such as:

Possible pump/dump
Possible spoofing
Volume spike
RSI very high
RSI very low

This layer is not intended to prove manipulation. It is an analytical screening tool designed to highlight unusual market behaviour for further investigation.

Macro-Financial Layer

The project includes two macroeconomic layers:

FED Macro Layer

The FED macro layer is validated and functional.

Active FED indicators include:

Federal Funds Rate
M2 Money Supply
Total Assets
Reserve Bank Credit
Deposits
Bank Credit
Loans and Leases
Securities in Bank Credit
Consumer Loans / Credit Cards
Credit Card Delinquency Rate
Credit Card Charge-Off Rate

The FED layer allows analysis such as:

M2 vs BTC
Fed Funds Rate vs NASDAQ 100
FED Total Assets vs S&P 500
Credit Card Delinquency vs VIX
Bank Credit vs S&P 500

Charts include:

dual-axis macro vs market analysis
base 100 comparisons
rolling correlations
macro-market alignment
EURO Macro Layer

The EURO macro layer v1 is validated and functional.

Active EURO series include:

Inflation
HICP Processed Food
HICP excluding Tobacco
HICP Services
HICP Industrial Goods
HICP Administered Energy/Food
Interest Rates
MFI Corporate Loans
MFI Household Consumption Loans
MFI House Purchase Loans
MFI Revolving Loans to Corporates
MFI Revolving Loans to Households
MFI Corporate Deposits
MFI Household Deposits

The EURO layer supports analysis against market assets such as:

STOXX 600
DAX
CAC 40
EUR
financial conditions indicators

A dedicated EURO fraud analytics layer is planned separately.

Streamlit Dashboard

The project includes an interactive Streamlit dashboard.

Current dashboard pages:

Overview
Asset Explorer
Correlations
FED Macro
EURO Macro
Project Status
Dashboard Features
Overview

The overview page summarizes the current state of the platform:

number of FED indicators
number of active EURO series
number of EURO market pairs
number of market assets
current validated modules
included chart types
Asset Explorer

The Asset Explorer allows individual asset analysis with:

asset selector
date range calendar
KPI cards
technical dashboard
candlestick chart
EMAs
Bollinger Bands
volume chart
RSI
Stochastic RSI
MACD
suspicious event markers
pump/dump flags
spoofing flags
volume spike detection
suspicious events table

Available chart types:

Technical Dashboard
Line Chart
Scatter Plot: Volume Z-Score vs Price Change
Box Plot: Returns Normal vs Suspicious Events
Bar Chart: Event Counts
Correlations

The Correlations page provides multi-asset analysis with:

multi-asset selector
calendar date filter
simple or logarithmic returns
correlation heatmap
rolling correlation
returns scatter plot
multi-asset base 100 performance

This page helps analyse how asset relationships change over time.

FED Macro

The FED Macro page compares FED indicators against market assets.

Examples:

M2 Money Supply vs BTC
Fed Funds Rate vs NASDAQ 100
FED Total Assets vs S&P 500
Credit Card Delinquency vs VIX
Bank Credit vs S&P 500
EURO Macro

The EURO Macro page compares selected EURO macroeconomic indicators against European and global market assets.

It supports:

inflation vs equity markets
interest rates vs equity markets
macro-market visual comparison
base 100 comparison where appropriate
Chart Types Used

The dashboard currently includes:

KPI Cards
Candlestick Charts
Line Charts
Bar Charts
Scatter Plots
Box Plots
Heatmaps
Rolling Correlation Charts
Multi-Asset Base 100 Performance Charts
Tables

Planned future chart types:

Treemap
Waterfall Chart
Sankey Diagram
Event Impact Charts
Market Regime Distribution Charts
Data Quality and Validation

The project includes several validation and diagnostic scripts to improve data reliability.

Examples:

asset data quality validation
duplicate table detection
date shift diagnosis
SP500 return validation
macro SQL inventory
macro config validation
FED macro summary report
EURO series validation
EURO market pair validation

The project separates experimental, archived and production-ready modules to reduce operational risk.

Technologies Used
Programming and Data
Python
pandas
numpy
SQLAlchemy
mysql-connector-python
Database
MySQL
phpMyAdmin
XAMPP
Visualization
Plotly
Streamlit
Analytics
technical indicators
rolling correlations
volatility analysis
drawdown analysis
z-score analysis
macro-market alignment
rule-based anomaly detection
Development Tools
PyCharm
PowerShell
Git
Git local repository
requirements.txt
Current Status

Completed:

multi-asset market data layer
core technical indicators
risk and manipulation heuristics
FED macro layer
EURO macro layer v1
Streamlit dashboard v1/v2 structure
Asset Explorer
Correlations module
SQL database backup
Git version control setup

In progress:

Streamlit modularization
dashboard testing
chart refinement
portfolio documentation

Planned:

Market Regimes page
Event Overlay page
Data Quality page
EURO Fraud Analytics page
Overview v2 with treemap and global suspicious event counts
advanced macro scatter plots
ML-based anomaly detection
Power BI executive dashboard layer
Skills Demonstrated

This project demonstrates practical experience in:

data cleaning
data ingestion
SQL database management
financial time series analysis
feature engineering
technical indicator calculation
macroeconomic data analysis
risk monitoring
anomaly detection
dashboard development
data visualization
modular Python architecture
Git version control
analytical storytelling
Relevance for Data / Risk / Fraud Analytics Roles

The project is relevant for roles such as:

Data Analyst
Financial Data Analyst
Risk Analyst
Fraud Analyst
Business Analyst
BI Analyst
Operations Analytics
Compliance Analytics

It demonstrates the ability to combine technical, financial and analytical reasoning into a structured data product.

The project is especially aligned with environments where market behaviour, risk indicators, anomaly detection, macroeconomic context and data-driven decision-making are relevant.

Next Steps

Planned next development phases:

Phase 1 — Streamlit Testing
test Asset Explorer
test suspicious event detection
test correlations page
validate date filters
validate SQL compatibility
Phase 2 — Market Regimes
classify market regimes
risk-on / risk-off states
dollar strength
yield pressure
volatility stress
commodity shock
Phase 3 — Event Overlay
add crisis and geopolitical event markers
compare market behaviour around events
analyse pre-event and post-event returns
Phase 4 — Data Quality Dashboard
expose validation reports inside Streamlit
missing data overview
duplicate table status
coverage by asset
Phase 5 — Fraud Analytics
develop separate EURO payments/fraud analytics module
analyse fraud losses by payment type
build descriptive fraud dashboards
Phase 6 — Machine Learning
anomaly detection
clustering market regimes
predictive risk scoring
suspicious behaviour classification
Disclaimer

This project is for educational, analytical and portfolio purposes.

It does not provide investment advice.

Suspicious event flags are rule-based analytical signals and should not be interpreted as proof of market manipulation.