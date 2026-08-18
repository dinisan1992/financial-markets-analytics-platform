# Exact public snapshot demo

This patch removes synthetic market paths from the public execution path.

## Why

The normal app and the demo already share the same Streamlit pages, Plotly
charts and indicator engine. The visible difference came from the synthetic
market generator. An identical chart requires the identical observations.

## One-time export

With XAMPP/MySQL ON, from the project root:

```powershell
.\demo\.venv\Scripts\python.exe .\demo\export_public_snapshot.py
```

This creates:

```text
demo/public_snapshot/
  manifest.json
  assets/*.jsonl
  events/*.jsonl
  fed/*.jsonl
  euro/*.jsonl
```

Only whitelisted market columns are exported. No database hostname, username,
password, `.env` content or SQL connection string is written to the snapshot.

## Prove BTC is the same before publishing

Keep MySQL ON and run:

```powershell
.\demo\.venv\Scripts\python.exe .\demo\compare_live_snapshot_btc.py
```

Expected:

```text
LIVE VS SNAPSHOT BTC COMPARISON PASSED
```

That compares the live MySQL BTC data with the snapshot and then recalculates
the chart-critical indicators through the same `prepare_asset_technical_data`
function used by Asset Explorer.

## Prove independence from MySQL

Turn XAMPP/MySQL OFF and run:

```powershell
.\demo\validate_demo.ps1
.\demo\run_demo.ps1
```

The demo must still work.

## Publish

Commit the generated `demo/public_snapshot/` directory together with this patch.
The Streamlit Cloud app will redeploy automatically.

The public banner changes from "synthetic data" to "static read-only snapshot".
The snapshot is intentionally frozen: the local platform can continue updating
without changing the public demo until the exporter is run again.

## Important

The snapshot contains historical market/macro observations. Before publishing,
ensure the underlying data-source licences/terms permit redistribution of the
chosen observations. If a source does not permit redistribution, exclude that
series or use a separately licensed/public source for the public snapshot.
