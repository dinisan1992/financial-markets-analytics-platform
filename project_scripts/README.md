# Project Scripts

Runnable scripts that used to live in the repository root are organized here.

## Folders

- `assets/` - per-asset processing scripts and `run_all_assets.py`.
- `analysis/` - selectors, macro analysis, correlation analysis, validation and reporting scripts.
- `diagnostics/` - one-off diagnosis and cleanup scripts.
- `ingestion/` - explicit source probes, staging downloads and guarded import entry points.

## Usage

Prefer running scripts from the repository root:

```powershell
python project_scripts/assets/run_all_assets.py
python project_scripts/analysis/asset_chart_selector.py
python project_scripts/ingestion/refresh_ecb_sources.py
```

The root `analysis_launcher.py` already points to these paths.

Each script includes a small import bootstrap so shared root modules such as `config.py`, `asset_config.py` and `indicators.py` remain importable after the move.

## Current Asset Update Coverage

`asset_config.py` defines one script path for each configured market asset.

The original core assets still have dedicated scripts. The newer market assets use the shared
`project_scripts/assets/new_market_asset.py` runner through small per-asset wrappers.

By default, those new-market wrappers read SQL and calculate indicators in memory. They only import/upsert
CSV data into SQL when explicitly called with `--update-sql`.
