# Project Status

Last updated: 24 July 2026

## Current Version

**Macro-Financial Risk & Market Behaviour Analytics Platform v0.3.1**

## Executive Summary

The project is a functional local macro-financial analytics platform built with Python, MySQL, pandas, Plotly and Streamlit.

It combines:

- multi-asset financial market analysis;
- technical indicators;
- macroeconomic data;
- rolling correlations;
- event impact analysis;
- BTC cycle analysis;
- rule-based risk and anomaly screening;
- interactive dashboarding;
- data quality validation.

The Streamlit application is now separated into page modules, analytical services, visualization components and reusable data-access functions. The current priority is consolidation, documentation, testing and portfolio presentation rather than adding additional raw datasets.

## Completed and Functional Modules

### Core Market Assets

Status: **Functional**

Configured coverage includes:

- BTC.
- US equity indices.
- European equity indices.
- Asian and global equity indices.
- Commodities.
- FX and currency indicators.
- Sovereign yields.
- Volatility and financial stress indicators.

A total of 37 configured assets were included in the latest local validation.

### Technical Indicator Engine

Status: **Functional and centralized in `indicators.py`**

Includes:

- RSI.
- Stochastic RSI.
- EMA 9, 12, 20, 26, 50, 100 and 200.
- Bollinger Bands.
- MACD.
- Momentum.
- ATR.
- ADX.
- CCI.
- OBV.
- Price change percentages.
- Realized volatility.
- Volatility of volatility.
- Drawdown duration.
- Volume z-score.
- Liquidity stress.
- Market entropy.

Indicator calculations use `pct_change(fill_method=None)` where appropriate to avoid artificial returns across missing observations.

### Risk and Anomaly Screening

Status: **Functional heuristic layer**

Includes:

- volume spike detection;
- possible pump/dump pattern screening;
- possible spoofing-like behaviour screening;
- RSI context;
- ATR and volatility context;
- abnormal price, volume and candle combinations.

The layer is intended for analytical screening only and does not prove manipulation.

### Data Quality

Status: **Functional**

Includes:

- duplicate checks;
- asset table validation;
- missing-value checks;
- invalid-price checks;
- date-shift detection;
- table consistency checks;
- macro-series validation;
- configured-pair validation.

### Market Analysis

Status: **Functional**

Includes:

- normalized performance;
- group performance;
- correlation matrices;
- rolling correlations;
- returns scatter analysis;
- market regime analysis;
- event overlays;
- macro-market alignment;
- cross-asset event impact;
- risk-on/risk-off snapshots.

### FED Macro Layer

Status: **Functional**

Validated active indicators: **11**

Includes:

- Fed Funds Rate.
- M2 Money Supply.
- Fed Total Assets.
- Reserve Bank Credit.
- Deposits.
- Bank Credit.
- Loans and Leases.
- Securities in Bank Credit.
- Consumer Loans and Credit Cards.
- Credit Card Delinquency Rate.
- Credit Card Charge-Off Rate.

### EURO Macro Layer

Status: **Functional**

- Configured series: 16.
- Active macro-market series: 12.
- Deferred fraud series: 4.
- Current configured validation errors: 0.

The deferred fraud series relate to card fraud, credit transfer fraud, direct debit fraud and e-money fraud losses.

## Streamlit Dashboard

Status: **Functional and modularized**

Current pages:

- Overview.
- Asset Explorer.
- Market Event Analysis.
- Correlations.
- FED Macro.
- EURO Macro.
- Project Status.

### Application Modules

The current architecture includes:

- `app/layout.py` — page configuration.
- `app/navigation.py` — sidebar navigation.
- `app/state.py` — session-state defaults.
- `app_pages/overview.py` — Overview page.
- `app_pages/asset_explorer.py` — Asset Explorer page.
- `app_pages/market_event_analysis.py` — Market Event Analysis page.
- `app_pages/correlations.py` — Correlations page.
- `app_pages/fed_macro.py` — FED Macro page.
- `app_pages/euro_macro.py` — EURO Macro page.
- `app_pages/project_status.py` — Project Status page.
- `services/data_access_service.py` — read-only SQL access and DataFrame normalization.
- `services/event_analysis_service.py` — event-study calculations.
- `services/btc_cycle_service.py` — BTC cycle and halving calculations.
- `services/technical_signal_service.py` — technical signal summaries.
- `services/risk_statistics_service.py` — risk scores and return statistics.
- `services/export_service.py` — reusable export functions.
- `dashboard/asset_view_components.py` — asset KPI, risk and statistics views.
- `dashboard/event_charts.py` — event visualizations.
- `dashboard/event_views.py` — event-analysis Streamlit views.
- `dashboard/btc_cycle_charts.py` — BTC cycle charts.
- `dashboard/btc_cycle_views.py` — BTC cycle views.
- `dashboard/macro_charts.py` — shared FED and EURO chart helpers.

`streamlit_app.py` now focuses primarily on application startup, caching, shared wrappers, dependency composition and page routing.

## Project Launcher

Status: **Functional**

Main file:

- `analysis_launcher.py`

## Latest Documented Validation

Local validation performed with XAMPP and MySQL enabled included:

- Streamlit health check completed successfully.
- 7/7 dashboard pages rendered without exceptions.
- Main dashboard data-loading actions completed successfully.
- Rolling correlation validated with real BTC and SP500 data.
- 37/37 configured assets loaded and calculated technical KPIs successfully.
- 5/5 configured FED market pairs loaded successfully.
- 12/12 active EURO market pairs loaded successfully.
- 37/37 asset SQL tables were present with data.
- 11/11 FED macro tables were present with data.
- 12/12 active EURO loaders completed successfully.
- 21 unit tests passed.
- Active Python files compiled successfully.
- Streamlit imported successfully in bare mode.
- No SQL writes, migrations or table mutations were introduced by the dashboard modularization.
- SQL updates remained opt-in.
- No `.env`, virtual environment folders, raw datasets or SQL dumps were tracked.

The repository history was recreated for the public portfolio release. Validation is therefore documented by project version and date rather than by references to removed local commit hashes.

## GitHub Readiness

Implemented:

- Environment-based database configuration.
- Local `.env` loading.
- Configurable data directories.
- Centralized SQLAlchemy connection URL.
- API credentials loaded from environment variables.
- `.env.example` with placeholders only.
- `.gitignore` coverage for credentials, datasets, dumps, virtual environments, outputs and archives.
- GitHub Actions workflow for syntax compilation and unit tests.
- Public README and project-status documentation.

## Current Limitations

- The production-scale MySQL database is not included in the repository.
- Raw and processed datasets are intentionally excluded.
- The repository does not yet provide a fully reproducible sample-data demo.
- Dashboard screenshots and a short demonstration have not yet been added.
- Some legacy ETL and news scripts still need safer entry points and retry handling.
- Some older scripts and messages still contain mixed Portuguese and English wording.
- The dependency file contains both direct and transitive packages and should be simplified later.
- Some duplicated legacy asset workflows remain, although newer assets use shared wrappers.

## Deferred and Planned Modules

### EURO Fraud Analytics

Status: **Deferred**

Planned work:

- identify and validate the correct fraud series keys;
- analyse fraud losses by payment type;
- analyse semiannual evolution;
- rank payment channels;
- calculate fraud growth by period;
- create a dedicated dashboard page.

### Architecture and Maintainability

Status: **In progress**

Planned work:

- continue centralizing SQL access;
- gradually package the active code under `src/` or a dedicated project package;
- convert remaining ETL and news scripts into explicit functions and `main()` entry points;
- add dry-run options to all scripts capable of writing to SQL;
- expand automated tests for indicators, correlations, event calculations and data access;
- reduce duplicated legacy workflows.

### Public Portfolio Improvements

Planned work:

- add dashboard screenshots;
- add a short demo GIF or video;
- provide anonymized or synthetic sample datasets;
- document a reproducible database schema workflow;
- simplify `requirements.txt`;
- continue reviewing public documentation.

## Current Development Priority

The project already contains a validated multi-asset, FED macro and EURO macro analytical layer.

The current priority is:

1. consolidation;
2. testing;
3. documentation;
4. GitHub presentation;
5. reproducibility;
6. incremental modularization.

Adding further raw datasets is not currently the main priority.
