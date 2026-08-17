# Demo Integration Checklist

The public demo is maintained under `demo/` and reuses the production
application without changing its SQL-backed execution path.

## Repository layout

```text
demo/
|-- streamlit_demo.py
|-- demo/
|   |-- data.py
|   `-- runtime.py
|-- tests/test_demo_mode.py
|-- project_scripts/diagnostics/demo_mode_smoke.py
|-- setup_demo.ps1
|-- validate_demo.ps1
`-- run_demo.ps1
```

Virtual environments, `__pycache__` directories and compiled Python files must
remain untracked.

## Test order

1. `.\demo\validate_demo.ps1`
2. `python -m unittest discover -s tests`
3. `python -m ruff check .`
4. `.\demo\run_demo.ps1`

The CI workflow separately runs the demo contract tests and smoke test on
Windows and Linux under Python 3.11 and 3.12.

## Manual acceptance

Open every page and confirm:

- the synthetic-data disclosure is visible;
- Asset Explorer loads OHLCV data and technical indicators;
- BTC cycle and halving tabs render;
- Event Analysis renders exact and approximate-date events;
- Correlations loads the default assets and rolling correlation renders;
- Market Regimes reports bounded stress indicators;
- FED and EURO pairs use plausible macro scales;
- Data Quality completes and reports no SQL synchronization contracts;
- Project Status renders;
- the source-code link opens the GitHub repository;
- no browser console errors appear at desktop or mobile widths.

## Normal-mode regression

Close the demo process and start the database-backed application separately:

```powershell
python -m streamlit run streamlit_app.py
```

Demo mode must not execute SQL, read private CSV files or alter the normal
application's data boundaries.

## Deployment

Streamlit Community Cloud main file:

```text
demo/streamlit_demo.py
```

No Streamlit database secret is required.
