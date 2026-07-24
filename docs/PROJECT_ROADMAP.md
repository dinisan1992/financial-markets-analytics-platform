# Project Roadmap — Macro-Financial Risk & Market Behaviour Analytics Platform

## Roadmap Overview

This roadmap defines the development phases of the Macro-Financial Risk & Market Behaviour Analytics Platform.

The project is being developed progressively, from data ingestion and validation to interactive dashboards, macro-financial analysis, risk detection and future machine learning modules.

---

## Phase 1 — Core Market Data Layer

### Status

Completed

### Objectives

Build the foundation for multi-asset market analysis.

### Completed Work

- Imported historical market data into MySQL
- Created individual asset tables
- Cleaned and normalized price/date fields
- Built core asset configuration
- Created reusable market data loaders
- Added support for multiple asset classes

### Asset Classes Covered

- Crypto
- Equity indices
- Commodities
- FX
- Yields
- Volatility indicators
- Financial stress indicators

---

## Phase 2 — Technical Indicators Layer

### Status

Completed

### Objectives

Create a reusable technical analysis layer for individual assets.

### Completed Work

- Synthetic OHLC construction
- Daily returns
- Price change percentage
- EMAs
- Bollinger Bands
- RSI
- Stochastic RSI
- MACD
- Rolling volatility
- Drawdown
- Volume moving averages
- Volume z-score

### Purpose

This layer supports technical analysis, dashboard visualizations and suspicious behaviour detection.

---

## Phase 3 — Risk and Suspicious Behaviour Detection

### Status

Completed / Improving

### Objectives

Detect abnormal market behaviour using rule-based analytical signals.

### Completed Work

- Volume spike detection
- Possible pump/dump flags
- Possible spoofing-like flags
- Extreme RSI flags
- Human-readable event reasons
- Suspicious events table
- Plotly markers for suspicious events

### Next Improvements

- Tune thresholds by asset class
- Add volatility-adjusted signals
- Add asset-specific risk profiles
- Add event severity scoring
- Compare suspicious events across assets

---

## Phase 4 — Data Quality and Validation

### Status

Completed / Ongoing

### Objectives

Improve reliability of the analytical data layer.

### Completed Work

- Data quality reports
- Duplicate table checks
- SP500 return validation
- Date shift diagnostics
- Macro SQL inventory
- FED config validation
- EURO series validation
- EURO market pair validation

### Next Improvements

- Add Streamlit Data Quality page
- Show missing data by asset
- Show date coverage by asset
- Show invalid values and duplicates
- Add validation status cards

---

## Phase 5 — FED Macro Layer

### Status

Completed and validated

### Objectives

Integrate FED macroeconomic indicators with market assets.

### Completed Work

Validated FED indicators:

- Federal Funds Rate
- M2 Money Supply
- Total Assets
- Reserve Bank Credit
- Deposits
- Bank Credit
- Loans and Leases
- Securities in Bank Credit
- Consumer Loans / Credit Cards
- Credit Card Delinquency Rate
- Credit Card Charge-Off Rate

### Existing Analyses

- M2 vs BTC
- Fed Funds Rate vs NASDAQ 100
- FED Total Assets vs S&P 500
- Credit Card Delinquency vs VIX
- Bank Credit vs S&P 500

### Next Improvements

- Add macro scatter plots
- Add macro rolling correlations inside Streamlit
- Add macro regime classification
- Add macro summary KPIs

---

## Phase 6 — EURO Macro Layer

### Status

v1 completed and validated

### Objectives

Integrate selected EURO macroeconomic indicators with European/global markets.

### Completed Work

Validated active EURO series:

- HICP components
- Inflation indicators
- MFI loan rates
- Corporate loan rates
- Household loan rates
- Deposit rates

### Existing Analyses

- EURO inflation vs STOXX 600
- EURO interest rates vs STOXX 600
- EURO macro indicators vs European market assets

### Next Improvements

- Add more precise EURO filters
- Add macro regimes for inflation and rates
- Add country-level analysis where useful
- Add EURO fraud analytics as a separate module

---

## Phase 7 — Streamlit Dashboard

### Status

In progress

### Objectives

Transform Python scripts into an interactive analytical dashboard.

### Completed / Prepared Pages

- Overview
- Asset Explorer
- Correlations
- FED Macro
- EURO Macro
- Project Status

### Completed / Prepared Features

- Date range calendar
- KPI cards
- Candlestick charts
- Line charts
- Bar charts
- Scatter plots
- Box plots
- Heatmaps
- Rolling correlations
- Base 100 performance
- Suspicious event markers
- Suspicious events table

### Next Improvements

- Test dashboard end-to-end
- Improve layout and visual consistency
- Add sidebar filters
- Add better error handling
- Add loading messages
- Add downloadable tables

---

## Phase 8 — Correlations Module

### Status

Prepared / pending testing

### Objectives

Provide multi-asset relationship analysis.

### Features

- Multi-asset price alignment
- Simple and logarithmic returns
- Correlation matrix
- Correlation heatmap
- Rolling correlation
- Returns scatter plot
- Multi-asset Base 100 chart

### Next Improvements

- Add correlation by regime
- Add correlation by event window
- Add correlation change detection
- Add strongest positive/negative correlation cards

---

## Phase 9 — Market Regimes

### Status

Planned

### Objectives

Classify market environments into interpretable regimes.

### Planned Regimes

- Risk-on
- Risk-off
- Dollar strength
- Yield pressure
- Volatility stress
- Liquidity expansion
- Liquidity tightening
- Commodity shock
- Credit stress

### Planned Features

- Current regime KPI
- Regime timeline
- Returns by regime
- Volatility by regime
- Asset performance by regime
- Regime distribution bar chart
- Box plots by regime

---

## Phase 10 — Event Overlay

### Status

Planned

### Objectives

Analyse market behaviour around crisis and geopolitical events.

### Planned Event Types

- COVID crash
- FED emergency support
- Russia / Ukraine war
- FTX collapse
- Silicon Valley Bank crisis
- Israel / Hamas conflict
- Iran / Israel tensions
- Major rate hike cycles
- Liquidity stress periods

### Planned Features

- Event markers on price charts
- Pre-event and post-event returns
- Event impact tables
- Average event impact by asset
- Event volatility comparison

---

## Phase 11 — Data Quality Dashboard

### Status

Planned

### Objectives

Expose data quality reports directly inside Streamlit.

### Planned Features

- Missing values by asset
- Date coverage by asset
- Duplicate row status
- Invalid price checks
- Last available date by table
- Macro validation status
- SQL table inventory overview

---

## Phase 12 — EURO Fraud Analytics

### Status

Backlog

### Objectives

Develop a separate descriptive fraud analytics module using EURO payments/fraud-related data.

### Planned Features

- Fraud losses by payment type
- Card fraud analysis
- Credit transfer fraud analysis
- Direct debit fraud analysis
- E-money fraud analysis
- Semiannual trend analysis
- Fraud ranking by channel
- Fraud dashboard page

### Notes

This module should be treated separately from macro-market correlation analysis.

---

## Phase 13 — Overview v2

### Status

Planned

### Objectives

Improve the dashboard landing page.

### Planned Features

- Global KPI cards
- Treemap by asset class
- Suspicious events by asset
- Multi-asset Base 100 overview
- Latest market regime
- Latest macro conditions
- Data quality summary

---

## Phase 14 — Advanced Visualizations

### Status

Planned

### Objectives

Add more advanced dashboard visualizations.

### Planned Charts

- Treemap
- Waterfall chart
- Sankey diagram
- Event impact charts
- Regime distribution charts
- Monthly returns heatmap

### Use Cases

- Asset class overview
- Return contribution
- Market regime flows
- Event impact storytelling
- Portfolio-style analysis

---

## Phase 15 — Machine Learning Layer

### Status

Future

### Objectives

Extend the rule-based detection system with machine learning.

### Planned Ideas

- Anomaly detection
- Clustering market regimes
- Suspicious behaviour scoring
- Pattern recognition
- Event similarity analysis
- Crisis-period classification

### Possible Techniques

- Isolation Forest
- DBSCAN
- K-Means
- Random Forest
- Gradient Boosting
- Time series feature engineering

---

## Phase 16 — Portfolio Packaging

### Status

In progress

### Objectives

Prepare the project for professional presentation.

### Completed / Prepared Files

- README.md
- PORTFOLIO_DESCRIPTION.md
- INTERVIEW_NOTES.md
- PROJECT_ROADMAP.md
- PROJECT_STATUS.md

### Planned Improvements

- Add screenshots
- Add architecture diagram
- Add sample dashboard images
- Add public demo with reduced sample data
- Add LinkedIn project summary
- Add CV project bullet points

---

## Current Priority

The current priority is:

1. Test the modular Streamlit dashboard
2. Validate Asset Explorer
3. Validate Correlations page
4. Commit stable dashboard version
5. Add Market Regimes page
6. Add Event Overlay page
7. Add Data Quality page

---

## Development Principle

The project follows this principle:

```text
Validate first.
Then expand.
Then polish.

Each major feature should be tested and committed before adding the next module.

Final Goal

The final goal is to build a portfolio-ready analytical platform that demonstrates:

data engineering
SQL
Python analytics
financial time series analysis
macroeconomic analysis
risk monitoring
anomaly detection
dashboard development
analytical storytelling