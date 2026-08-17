# Public Demo Mode

## Purpose

`demo/streamlit_demo.py` runs the existing Financial Markets Analytics Platform
without MySQL, private CSV files, credentials or local backup/report folders.

The demo deliberately reuses the existing application pages, analytical engine,
charts, event logic, correlations, market regimes and macro feature code.
Only the data boundaries are replaced at runtime.

## Important disclosure

All market and macro values produced by demo mode are **deterministic synthetic
data**. Real historical dates are used for a small set of contextual events,
but the prices, returns, correlations, regimes, drawdowns and event reactions
shown in the demo are illustrative and must not be described as historical
market results.

The application displays this warning visibly at the top of the interface.
Each series is generated from a fixed master calendar and then sliced to the
requested interval, so selecting a different start date cannot rewrite values
inside an overlapping period. Stress indices, yields and spreads use bounded
mean-reverting processes; macro series use explicit frequency, scale and unit
profiles.

## Files added

```text
demo/streamlit_demo.py
demo/demo/data.py
demo/demo/runtime.py
demo/tests/test_demo_mode.py
demo/project_scripts/diagnostics/demo_mode_smoke.py
demo/docs/DEMO_MODE.md
```

The package is intentionally additive: it does not replace `streamlit_app.py`,
the MySQL loaders, the production services, schemas, CSVs or existing tests.

## How it works

```text
demo/streamlit_demo.py
        |
        v
demo/demo/runtime.py
        |
        +-- patches macro_data_loader.get_engine -> None
        +-- patches data_access_service loaders -> synthetic frames
        +-- patches correlation multi-asset loader -> synthetic prices
        +-- patches Data Quality asset/event audit -> demo frames
        +-- disables saved EURO synchronization status in demo
        |
        v
streamlit_app.py (unchanged)
        |
        v
existing pages / services / charts / indicators
```

The patching happens before the normal application is executed. This is
deliberate: pages such as Correlations import their data-loading function at
module import time.

## Run locally

From the project root:

```powershell
.\demo\setup_demo.ps1
.\demo\run_demo.ps1
```

No MySQL/XAMPP process is required.

The normal local platform remains:

```powershell
python -m streamlit run streamlit_app.py
```

## Validate before publishing

Run the complete demo validation:

```powershell
.\demo\validate_demo.ps1
```

The individual cross-platform commands are:

```powershell
python demo/tests/test_demo_mode.py
python demo/project_scripts/diagnostics/demo_mode_smoke.py
```

Then run the complete existing suite:

```powershell
python -m unittest discover -s tests
python -m ruff check .
python -m coverage run -m unittest discover -s tests
python -m coverage report
```

Finally test all nine pages manually with:

```powershell
.\demo\run_demo.ps1
```

## Expected page behaviour

- **Overview**: normal project overview.
- **Asset Explorer**: all configured assets load synthetic OHLCV data and use
  the existing technical-indicator engine.
- **Market Event Analysis**: uses the synthetic market paths plus a small
  contextual event set containing exact and year-only events.
- **Correlations**: uses the existing returns, pair coverage, Fisher confidence,
  scatter, rolling correlation and Base 100 logic.
- **Market Regimes**: uses the existing rule-based classifier on synthetic
  cross-asset paths.
- **FED Macro**: all configured pairs can produce deterministic synthetic macro
  series aligned backward to real demo market observations.
- **EURO Macro**: same demo alignment approach for configured EURO pairs.
- **Data Quality**: audits the synthetic demo frames. EURO synchronization
  status is intentionally unavailable because the demo has no SQL contracts.
- **Project Status**: displays the normal project documentation, while the
  persistent demo banner identifies the execution mode.

## Streamlit Community Cloud

For a public deployment, use:

```text
Main file: demo/streamlit_demo.py
```

No database secret is required for the demo entry point.

The runtime dependencies are the project's normal `requirements.txt`.

## Safety properties

Demo mode:

- never calls the patched MySQL engine factory;
- does not execute SQL;
- does not read private source CSVs;
- does not read `.env` credentials;
- does not promote/update active CSV files;
- does not execute EURO synchronization;
- does not write backups or reports;
- does not modify the existing production code paths.

## Why the demo is synthetic instead of bundled real data

The public repository intentionally excludes the full datasets and MySQL
database. A deterministic synthetic backend keeps the demonstration:
portable, small, reproducible, credential-free and legally simpler while still
exercising the real analytics/UI code.

A future enhancement could add a separately licensed real-data sample mode.
