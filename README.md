# Macro-Financial Risk & Market Behaviour Analytics Platform

A Python, MySQL, pandas, Plotly and Streamlit platform for analysing financial markets, macroeconomic indicators, correlations, event impact, technical indicators and rule-based market risk and anomaly signals.

The project was developed as a local analytics platform and professional portfolio project. Raw datasets, SQL dumps and private credentials are intentionally excluded from Git.

## Current Status

Functional local platform with:

- Interactive Streamlit dashboard.
- Multi-asset market analysis.
- Technical indicator engine.
- Rule-based risk and anomaly screening.
- FED macro-market analysis.
- EURO macro-market analysis.
- Multi-asset correlation analysis.
- Market event impact analysis.
- BTC cycle and halving analysis.
- Data quality and validation tools.
- Automated syntax checks and unit tests through GitHub Actions.

Current project version: **v0.4.1**

## Main Analytical Capabilities

### Multi-Asset Analysis

The platform is configured to analyse:

- Crypto: BTC.
- US equity indices: SP500, NASDAQ100, DOWJONES and RUSSELL2000.
- European equity indices: STOXX600, EUROSTOXX50, FTSE100, DAX and CAC40.
- Asian and global equity indices: NIKKEI225, SSECOMPOSITE and EMERGING_MARKETS.
- Commodities: GOLD, SILVER, COPPER, BRENT_OIL, WTI_OIL, NATURAL_GAS, WHEAT and CORN.
- FX and currency indicators: DXY, EURO, YUAN, LIBRA, YEN and SWISS_FRANC.
- Sovereign yields: US2Y, US10Y, US30Y, GERMANY10Y, UK10Y and JAPAN10Y.
- Volatility and stress indicators: VIX, MOVE_INDEX, FINANCIAL_CONDITIONS and TED_SPREAD.

### FED Macro Layer

Configured indicators include:

- Federal Funds Effective Rate.
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

Configured series include:

- HICP processed food.
- HICP all-items excluding tobacco.
- HICP services.
- HICP industrial goods.
- HICP administered energy and food.
- MFI corporate loans.
- MFI household consumption loans.
- MFI house purchase loans.
- MFI revolving loans to corporations.
- MFI revolving loans to households.
- MFI corporate deposits.
- MFI household deposits.

A future fraud analytics layer is planned for card fraud, credit transfer fraud, direct debit fraud and e-money fraud losses.

## Dashboard Pages

- **Overview** - project scope and module summary.
- **Asset Explorer** - centralized technical analysis, OHLC provenance, KPIs, risk indicators and event overlays.
- **Market Event Analysis** - cross-asset reactions, date precision, event detail and recovery analysis.
- **Correlations** - pairwise-valid matrices, observation-based rolling correlations, common-period coverage, confidence intervals and normalized performance.
- **Market Regimes** - rule-based regime classification and regime-conditioned performance.
- **FED Macro** - all configured FED/market pairs aligned on real market observations.
- **EURO Macro** - European macroeconomic series aligned on real market observations.
- **Data Quality** - read-only freshness, duplicate, price-review, remediation, pair-confidence and event-coverage audit with aggregated ZIP export.
- **Project Status** - current implementation and validation status.

## Application Screenshots

| Overview | Asset Explorer |
| --- | --- |
| ![Overview dashboard](docs/images/overview.png) | ![Asset Explorer](docs/images/asset_explorer.png) |

| Market Event Analysis | Correlations |
| --- | --- |
| ![Market Event Analysis](docs/images/market_event_analysis.png) | ![Correlation analysis](docs/images/correlations.png) |

| Market Regimes | Data Quality |
| --- | --- |
| ![Market Regimes](docs/images/market_regimes.png) | ![Data Quality audit](docs/images/data_quality.png) |

| FED Macro | EURO Macro |
| --- | --- |
| ![FED macro analysis](docs/images/fed_macro.png) | ![EURO macro analysis](docs/images/euro_macro.png) |

![Project Status](docs/images/project_status.png)

## Technical Indicators

The central indicator engine calculates:

- Native OHLC preservation when valid, with synthetic OHLC only for missing or invalid rows.
- Row-level `ohlc_source` provenance and candle-signal eligibility.
- Daily returns and price change percentages.
- EMA 9, 12, 20, 26, 50, 100 and 200.
- Bollinger Bands.
- RSI.
- Stochastic RSI.
- MACD, signal and histogram-related metrics.
- Momentum.
- ATR.
- ADX.
- CCI.
- OBV.
- Rolling and realized volatility.
- Drawdown and drawdown duration.
- Volume moving averages and volume z-score.
- Liquidity stress.
- Market entropy.

## Risk and Anomaly Screening

The project includes a heuristic screening layer for:

- Abnormal volume spikes.
- Possible pump/dump patterns.
- Possible spoofing-like behaviour.
- Extreme RSI conditions.
- Abnormal price, volume, candle and volatility combinations.

These signals are analytical alerts only. They do not prove market manipulation and are not trading recommendations.

## Architecture

The application is separated into configuration, data access, analytical services, dashboard components and page modules.

- `streamlit_app.py` acts as the application entry point, cache wrapper and page router.
- `app/` contains layout, navigation and session-state helpers.
- `app_pages/` contains the main Streamlit page modules.
- `services/` contains reusable business and analytical logic.
- `dashboard/` contains visualization and Streamlit view components.
- `project_scripts/` contains asset processing, analysis and diagnostic scripts.
- `tools/` contains FED, EURO, news, SQL and legacy utilities.
- `tests/` contains automated unit tests.

## Project Structure

```text
.
|-- streamlit_app.py
|-- analysis_launcher.py
|-- config.py
|-- asset_config.py
|-- macro_config.py
|-- euro_series_config.py
|-- indicators.py
|-- risk_detection.py
|-- database.py
|-- app/
|   |-- layout.py
|   |-- navigation.py
|   `-- state.py
|-- app_pages/
|   |-- overview.py
|   |-- asset_explorer.py
|   |-- market_event_analysis.py
|   |-- correlations.py
|   |-- market_regimes.py
|   |-- fed_macro.py
|   |-- euro_macro.py
|   |-- data_quality.py
|   `-- project_status.py
|-- services/
|   |-- data_access_service.py
|   |-- event_analysis_service.py
|   |-- data_quality_service.py
|   |-- macro_analytics_service.py
|   |-- market_regime_service.py
|   |-- btc_cycle_service.py
|   |-- technical_signal_service.py
|   |-- risk_statistics_service.py
|   |-- export_service.py
|   `-- project_status_service.py
|-- dashboard/
|-- project_scripts/
|   |-- assets/
|   |-- analysis/
|   `-- diagnostics/
|-- tools/
|   |-- fed/
|   |-- eu/
|   |-- news/
|   |-- legacy/
|   `-- sql/
|-- tests/
|-- docs/
|-- data/              # ignored by Git
|-- new_market_data/   # ignored by Git
|-- outputs/           # ignored by Git
|-- archive/           # ignored by Git
|-- requirements.txt
|-- .env.example
`-- .gitignore
```

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create a private `.env` file:

```powershell
copy .env.example .env
```

Fill in the local database credentials and any optional API keys.

Run the dashboard:

```powershell
python -m streamlit run streamlit_app.py
```

## Environment Variables

Supported variables:

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `PROJECT_DATA_DIR`
- `PROJECT_NEW_MARKET_DATA_DIR`
- `PROJECT_SOURCE_DATA_DIR`
- `FED_SOURCE_DIR`
- `EURO_SOURCE_DIR`
- `NEWSDATA_API_KEY`
- `CRYPTOPANIC_API_TOKEN`
- `DEFAULT_UPDATE_SQL`

The default local database is `btc_data` on `localhost:3306`. SQL writes are disabled by default through `DEFAULT_UPDATE_SQL=false`.

## Validation Snapshot

The v0.4.1 validation includes:

- 9/9 Streamlit pages rendered without uncaught exceptions, including graceful database-offline handling.
- 48 deterministic unit tests passed.
- Active Python files compiled successfully.
- Native/synthetic OHLC, 252/365 annualization, rolling correlation, pair confidence, events, recovery, macro alignment, data quality and regimes covered by 56 tests.
- News modules import without starting network loops or SQL activity.
- No SQL writes, migrations, CSV importers or database mutations were executed during this upgrade.
- The read-only database audit loaded 37 assets, evaluated 666 pairs and 66 events, and produced `audit_outputs/audit_outputs.zip`.

The previous database-enabled validation covered 37/37 configured assets, 11/11 FED series and 12/12 active EURO loaders. See `PROJECT_STATUS.md` for details.

## Data and Reproducibility

The production-scale local database and raw datasets are not included in the repository.

The public repository focuses on:

- source code;
- analytical methodology;
- project architecture;
- tests;
- configuration examples;
- documentation.

The local database remains intentionally separate from the public source repository.

## GitHub Safety

The repository is configured to exclude:

- `.env` files and private credentials.
- Streamlit secrets.
- Raw CSV and Excel datasets.
- SQL and database dumps.
- Local virtual environments.
- Generated outputs and reports.
- Local backups and archives.

## Roadmap

Planned improvements include:

- Calibrate risk thresholds by asset class and data provenance.
- Replace important year-only world events with verified exact dates.
- Add dry-run and explicit entry points to the remaining SQL-capable ETL scripts.
- Extend reference tests with database-backed snapshots when MySQL is available.
- Simplify the dependency file to direct project dependencies.
- Develop the deferred EURO fraud analytics layer.
- Start machine-learning experiments only after feature and label governance is stable.

## Disclaimer

This project is for educational, analytical and portfolio purposes only. It does not provide financial advice.
