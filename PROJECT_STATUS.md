# Project Status

Last updated: 3 August 2026

## Current Version

**Macro-Financial Risk & Market Behaviour Analytics Platform v0.5.0**

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

The Streamlit application is separated into page modules, analytical services, visualization components and reusable data-access functions. Version 0.5.0 adds a controlled CSV-to-SQL synchronization layer, enforces one daily observation in the analytical path and completes the first reversible market-table remediation cycle.

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

Status: **Functional and centralized through `prepare_asset_technical_data()` and `indicators.py`**

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

Indicator calculations use `pct_change(fill_method=None)` where appropriate to avoid artificial returns across missing observations. Valid native OHLC is preserved row by row; synthetic OHLC is created only where required and recorded in `ohlc_source`. Volatility uses asset metadata: 365 observations for crypto, 252 for market-session assets, and no market-style annualization for macro features.

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

Status: **Functional with a read-only Streamlit audit**

Includes:

- duplicate checks;
- asset table validation;
- missing-value checks;
- invalid-price checks;
- date-shift detection;
- table consistency checks;
- macro-series validation;
- configured-pair validation;
- first/last dates and staleness;
- calendar coverage and longest gaps;
- zero-return and forward-fill risk indicators;
- native OHLC and volume coverage;
- pairwise correlation coverage and potential bias;
- common correlation observations, aligned period, coverage ratio and Fisher 95% confidence interval;
- freshness limits, overdue days, configured source and responsible updater;
- duplicate-date group counts and affected date range;
- prioritized non-destructive remediation actions;
- event coverage and event-date precision;
- aggregated CSV/ZIP export with no raw prices or credentials.

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
- Market Regimes.
- FED Macro.
- EURO Macro.
- Data Quality.
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
- `app_pages/market_regimes.py` — Market Regimes page.
- `app_pages/fed_macro.py` — FED Macro page.
- `app_pages/euro_macro.py` — EURO Macro page.
- `app_pages/data_quality.py` — read-only Data Quality page.
- `app_pages/project_status.py` — Project Status page.
- `services/data_access_service.py` — read-only SQL access and DataFrame normalization.
- `services/event_analysis_service.py` — event-study calculations.
- `services/data_quality_service.py` — aggregated asset, pair and event auditing.
- `services/correlation_quality_service.py` — pair coverage, confidence classification and confidence intervals.
- `services/macro_analytics_service.py` — market-calendar macro alignment and observation-based features.
- `services/market_regime_service.py` — rule-based regime features and classification.
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

Version 0.5.0 local validation included:

- 78/78 deterministic unit tests passed.
- 187 active Python files parsed successfully and `pip check` reported no broken requirements.
- 37/37 configured asset tables loaded and recalculated through a SQL-only runner with database writes disabled.
- 9/9 Streamlit pages rendered without uncaught exceptions.
- BTC Asset Explorer, Data Quality and BTC/SP500 rolling correlation were exercised in a real browser session.
- The browser and Streamlit logs contained no runtime errors.
- A 47,022,488-byte scoped SQL backup containing nine market tables was verified before remediation.
- EURO, YUAN, LIBRA and SSECOMPOSITE were consolidated to one row per date.
- SP500 was rebuilt from its CSV after confirming a one-day legacy date shift in 13,803 matching observations.
- Unique `snapped_at` keys were added to SP500, GOLD, DXY, EURO, YUAN, LIBRA and SSECOMPOSITE.
- 158 missing STOXX600 observations were imported, 80 missing BTC market-cap values were restored and 4,679 misparsed SSE volume values were corrected.
- All nine reviewed market tables are now idempotent against their current CSV sources.
- The seven pre-remediation SQL tables remain retained locally with `__pre_v050_20260803` suffixes.

Previous v0.4.3 code-only validation included:

- 9/9 dashboard pages rendered without uncaught exceptions.
- Database-offline handling validated with MySQL/XAMPP stopped.
- 63/63 deterministic unit tests passed.
- Active Python files compiled successfully.
- Custom event horizons, event recovery and year-only exclusion validated.
- OHLC preservation/fallback and 252/365 annualization validated against controlled series.
- Rolling correlations validated on pairwise observations.
- Macro alignment validated to prevent future-value leakage and artificial market dates.
- News modules imported without network loops or SQL execution.
- Four legacy import commands validated as disabled by default with an explicit read-only preview mode.
- No SQL writes, migrations, CSV imports or database mutations were executed.

### Data Audit Snapshots

The post-remediation audit generated on 3 August 2026 reports:

- 37 assets audited with no load errors;
- zero assets with duplicate dates;
- zero automatically invalidated price series and one WTI historical price-review case;
- 666 correlation pairs, of which 148 have low-overlap bias warnings;
- 66 historical events, including 35 year-only approximate dates;
- all 37 assets marked stale relative to the audit date because freshness is a separate source-download concern.

The 31 July 2026 v0.4.0 baseline loaded all 37 configured asset tables without load errors. Its recorded SHA-256 is `8BF5A15AC44043E567442E7522626B15F4321B5CB4C449CA081E5ABD9C656531`. Version 0.4.1 archives the previous local ZIP under `audit_outputs/baselines/` before generating a new Git-ignored audit.

- 37 assets audited; all were stale relative to the audit date.
- 27 assets had measurable native OHLC coverage; 10 required synthetic fallback.
- 666 correlation pairs evaluated; 149 were flagged for low overlap or insufficient observations.
- Confidence distribution: 457 high, 60 moderate, 148 low and 1 insufficient pair.
- 66 historical events audited; 35 had year-only date precision and 31 had exact dates.
- Duplicate dates were found in EURO, YUAN, LIBRA and SSECOMPOSITE. A dedicated read-only preview confirmed 36,732 duplicate-date groups and 210,364 surplus observations when preserving one row per date.
- Price and volume match in all duplicate groups, but 36,729 groups differ in one or more technical columns. A total of 173,633 rows are exact full-row copies.
- The four affected tables have no indexes, so the former `ON DUPLICATE KEY UPDATE` statements could not prevent repeated CSV imports.
- The negative WTI_OIL observation on 20 April 2020 is retained and flagged for source review rather than automatic correction.
- Excess zero returns were found in YUAN, FINANCIAL_CONDITIONS and TED_SPREAD.
- No database rows or schemas were changed by the audit.

The latest database-enabled validation before v0.4.0 included:

- Streamlit health check completed successfully.
- 7/7 then-existing dashboard pages rendered without exceptions.
- Main dashboard data-loading actions completed successfully.
- Rolling correlation validated with real BTC and SP500 data.
- 37/37 configured assets loaded and calculated technical KPIs successfully.
- 5/5 then-exposed FED market pairs loaded successfully; the current page exposes all 15 configured pairs.
- 12/12 active EURO market pairs loaded successfully.
- 37/37 asset SQL tables were present with data.
- 11/11 FED macro tables were present with data.
- 12/12 active EURO loaders completed successfully.
- 21 then-existing unit tests passed.
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
- The public repository intentionally excludes the local production-scale database and datasets.
- FED, EURO and some archived ETL scripts still need the same dry-run and explicit-write contract as the market synchronizer.
- Some legacy-only scripts and comments still contain mixed Portuguese and English wording.
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

The current priority is the second controlled data-engineering cycle:

1. formalize source-download manifests with source URL, expected filename, frequency and last successful refresh;
2. migrate FED and EURO importers to explicit `dry-run`/`--update-sql` entry points without import-time execution;
3. add a freshness dashboard action that identifies which CSV must be downloaded next without performing network access;
4. confirm the WTI_OIL source contract for 20 April 2020 without changing the valid historical negative value automatically;
5. classify YUAN, FINANCIAL_CONDITIONS and TED_SPREAD by native source frequency;
6. add database-backed synchronization tests in an isolated test schema;
7. begin machine-learning experiments only after data freshness and feature governance are stable.
