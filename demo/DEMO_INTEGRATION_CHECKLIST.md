# Demo Integration Checklist

The delivered demo package only ADDS files. It does not overwrite the current
v0.7.4 production application.

## Copy

Extract the ZIP into the project root so that these paths exist:

- `streamlit_demo.py`
- `demo/data.py`
- `demo/runtime.py`
- `tests/test_demo_mode.py`
- `project_scripts/diagnostics/demo_mode_smoke.py`
- `docs/DEMO_MODE.md`

## Test order

1. `python -m unittest tests.test_demo_mode`
2. `python project_scripts/diagnostics/demo_mode_smoke.py`
3. `python -m unittest discover -s tests`
4. `python -m ruff check .`
5. `python -m streamlit run streamlit_demo.py`

## Manual acceptance

Open every page and confirm:

- no MySQL/XAMPP is running;
- no connection error appears;
- synthetic-data banner is visible;
- Asset Explorer loads;
- BTC cycle/halving tabs render;
- Event Analysis renders;
- Correlations load at least eight default assets;
- Market Regimes renders;
- FED and EURO pairs render;
- Data Quality runs and shows no EURO sync contracts;
- Project Status renders.

## Normal-mode regression

Close the demo process and start:

`python -m streamlit run streamlit_app.py`

with MySQL available. Confirm normal mode still behaves exactly as before.

## Git recommendation

After local acceptance, add the six new files in a dedicated commit, for
example:

`Add public synthetic demo mode`

The demo implementation does not require a database migration.
