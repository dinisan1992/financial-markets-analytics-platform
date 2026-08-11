# Continuous Integration

The GitHub Actions workflow is defined in
`.github/workflows/python-checks.yml` and runs on every push and pull request.

## Dependency Contracts

- `requirements.txt` contains only pinned packages imported directly by the
  runtime application and active data tools.
- `requirements-dev.txt` includes the runtime contract and adds only pinned
  Ruff and Coverage tooling.
- `python -m pip check` verifies that the resolved environment is internally
  consistent.

## Static Checks

The Linux/Python 3.12 static job:

1. installs `requirements-dev.txt`;
2. runs `pip check`;
3. runs Ruff over the active Python tree;
4. compiles the active Python files;
5. proves that macro importer entry points do not connect to MySQL at import
   time.

## Test Matrix

The unit-test job covers four environments:

- Ubuntu with Python 3.11;
- Ubuntu with Python 3.12;
- Windows with Python 3.11;
- Windows with Python 3.12.

Each environment installs the development contract, runs `pip check`, executes
the complete deterministic `unittest` suite under branch coverage and enforces
the configured minimum.

Coverage currently measures `app`, `app_pages`, `dashboard` and `services`.
The v0.7.2 baseline is 41%, and `.coveragerc` blocks regressions below 40%.
The Ubuntu/Python 3.12 run also publishes `coverage.xml` as a workflow artifact.

## Local Validation

```powershell
python -m pip install -r requirements-dev.txt
python -m pip check
python -m ruff check .
python -m coverage run -m unittest discover -s tests
python -m coverage report
```

These CI paths do not apply CSV synchronization plans, run remediation commands
or write to the production database.
