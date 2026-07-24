# Project Audit

Date: 2026-07-23

## Executive Summary

The project is a local macro-financial analytics platform built with Python, MySQL, pandas, Plotly and Streamlit. It analyses market assets, macroeconomic series, correlations, event reactions, technical indicators and rule-based suspicious market behaviour signals.

The project is functional but still transitional: the dashboard is active, the configs are centralizing coverage, and older ETL scripts remain as standalone import tools. Root-level files are now limited mostly to shared modules and entry points; runnable scripts are organized under `project_scripts/`.

## What The Program Does

The platform supports:

- interactive Streamlit dashboard analysis;
- individual asset technical dashboards;
- suspicious behaviour flags;
- market event impact analysis;
- multi-asset correlations;
- rolling correlations;
- base-100 performance comparisons;
- FED macro vs market analysis;
- EURO macro vs market analysis;
- BTC cycle and halving analysis;
- data quality diagnostics;
- SQL import utilities for FED, EURO and market datasets.

## Markets Analysed

Configured market assets:

- BTC
- SP500
- STOXX600
- FTSE100
- GOLD
- DXY
- EURO
- YUAN
- LIBRA
- SSECOMPOSITE
- NASDAQ100
- DOWJONES
- RUSSELL2000
- EUROSTOXX50
- DAX
- CAC40
- NIKKEI225
- EMERGING_MARKETS
- VIX
- MOVE_INDEX
- BRENT_OIL
- WTI_OIL
- NATURAL_GAS
- COPPER
- SILVER
- WHEAT
- CORN
- YEN
- SWISS_FRANC
- US10Y
- US2Y
- US30Y
- GERMANY10Y
- UK10Y
- JAPAN10Y
- FINANCIAL_CONDITIONS
- TED_SPREAD

FED macro indicators:

- FED_FUNDS_RATE
- FED_M2
- FED_TOTAL_ASSETS
- FED_RESERVE_BANK_CREDIT
- FED_DEPOSITS
- FED_BANK_CREDIT
- FED_LOANS_LEASES
- FED_SECURITIES_BANK_CREDIT
- FED_CONSUMER_LOANS_CREDIT_CARDS
- FED_CREDIT_CARD_DELINQUENCY
- FED_CHARGE_OFF_RATE_CREDIT_CARDS

EURO configured series:

- EURO_HICP_PROCESSED_FOOD
- EURO_HICP_EX_TOBACCO
- EURO_HICP_SERVICES
- EURO_HICP_INDUSTRIAL_GOODS
- EURO_HICP_ADMINISTERED_ENERGY_FOOD
- EURO_MFI_CORPORATE_LOANS_AT
- EURO_MFI_HOUSEHOLD_CONSUMPTION_LOANS_AT
- EURO_MFI_HOUSE_PURCHASE_LOANS_AT
- EURO_MFI_REVOLVING_LOANS_CORPORATE_AT
- EURO_MFI_REVOLVING_LOANS_HOUSEHOLDS_AT
- EURO_MFI_CORPORATE_DEPOSITS_AT
- EURO_MFI_HOUSEHOLD_DEPOSITS_AT
- EURO_CARD_FRAUD_LOSSES
- EURO_CREDIT_TRANSFER_FRAUD_LOSSES
- EURO_DIRECT_DEBIT_FRAUD_LOSSES
- EURO_EMONEY_FRAUD_LOSSES

## Organization Changes Applied

- Moved root-level generated CSV reports into `outputs/reports/`.
- Moved generated project tree text files into `outputs/project_tree/`.
- Moved per-asset runners into `project_scripts/assets/`.
- Moved analysis, selector, validation and reporting scripts into `project_scripts/analysis/`.
- Moved diagnostic and cleanup scripts into `project_scripts/diagnostics/`.
- Moved news scripts into `tools/news/`.
- Moved old standalone import scripts into `tools/legacy/`.
- Kept shared modules and entry points at root to preserve current imports.
- Added `.env.example`.
- Strengthened `.gitignore` for `.env.*`, Streamlit secrets, logs, compressed dumps and Python build/test outputs.
- Added `.github/workflows/python-checks.yml` for syntax compilation in GitHub Actions.
- Updated `README.md` for GitHub presentation.
- Updated `PROJECT_STATUS.md` to reflect the actual dashboard/launcher status.

## Security / GitHub Readiness Changes Applied

- `config.py` now reads database settings from environment variables.
- `config.py` now loads a local `.env` file automatically when present.
- `config.py` now supports configurable data directories.
- SQLAlchemy URL construction is centralized in `get_sqlalchemy_database_url()`.
- `macro_data_loader.py`, `euro_data_loader.py` and `tools/sql/import_new_market_data_to_sql.py` use the centralized SQLAlchemy URL.
- FED and EURO ETL scripts now use `DB_CONFIG`, `FED_SOURCE_DIR` and `EURO_SOURCE_DIR` instead of hardcoded local Desktop paths and MySQL credentials.
- News API keys now use `NEWSDATA_API_KEY` and `CRYPTOPANIC_API_TOKEN` from the local environment.
- Raw datasets, SQL dumps, backups, outputs and local virtual environments are ignored by Git.

## Calculation Changes Already Applied

The previous calculation cleanup remains in place:

- RSI edge cases corrected for constant/up-only/down-only price series.
- `pct_change(fill_method=None)` used to avoid artificial gap returns.
- Dashboard indicators aligned with the central `indicators.py` implementation.
- Suspicious-event counts now focus on pump/dump and spoofing-like signals, with volume spikes and RSI extremes kept as separate context.
- Correlation calculations avoid forward-filling by default when building market return frames.

## Current Risks / Issues

- The active app is still dominated by a large `streamlit_app.py`; this should be split into page modules.
- Some duplicated asset workflows still exist, but they now live under `project_scripts/assets/`.
- Several older ETL scripts write to SQL immediately when executed; they should eventually be converted to functions with explicit `main()` entry points and dry-run options.
- A first unit test file exists for indicator edge cases; broader test coverage is still needed.
- Documentation had outdated information and encoding artifacts; the key public files were cleaned, but older docs can still be improved.
- The local virtual environment exists in the project root but is ignored by Git. For portability, use `.venv` outside Git or recreate it from `requirements.txt`.
- The actual MySQL database is not part of the Git repository. A reproducible schema/export process should be added separately.

## Recommended Next Steps

1. Add unit tests for `indicators.py`, `dashboard/asset_indicators.py` and `dashboard/correlation_data.py`.
2. Refactor `streamlit_app.py` into `dashboard/pages/` modules.
3. Create a reusable `asset_processor.py` that processes any configured asset from `asset_config.py`.
4. Convert ETL scripts under `tools/fed` and `tools/eu` into explicit functions with `if __name__ == "__main__": main()`.
5. Add dry-run modes for every script capable of writing to SQL.
6. Add a documented database schema export workflow that excludes private data.
7. Add sample/synthetic datasets for tests and GitHub demos.
8. Add screenshots or a short demo GIF for the Streamlit dashboard.
9. Clean remaining older docs and remove duplicated/outdated roadmap text.
10. Decide whether the public GitHub repo should be portfolio-only or fully reproducible with anonymized/sample data.

## Safe Refactor Direction

Recommended future layout:

```text
.
|-- streamlit_app.py
|-- src/
|   |-- financial_platform/
|   |   |-- config.py
|   |   |-- database.py
|   |   |-- indicators.py
|   |   |-- risk_detection.py
|   |   |-- asset_processor.py
|   |   |-- macro/
|   |   |-- euro/
|   |   `-- charts/
|-- dashboard/
|   |-- pages/
|   |-- asset_charts.py
|   |-- asset_indicators.py
|   |-- correlation_charts.py
|   `-- correlation_data.py
|-- tools/
|-- tests/
|-- docs/
|-- data/
|-- new_market_data/
`-- outputs/
```

This should be done gradually, with tests comparing old and new calculation outputs before removing or moving active scripts.
