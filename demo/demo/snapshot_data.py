from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from services.macro_analytics_service import align_macro_to_market_calendar


SNAPSHOT_ROOT = Path(__file__).resolve().parents[1] / "public_snapshot"
ASSET_ROOT = SNAPSHOT_ROOT / "assets"
FED_ROOT = SNAPSHOT_ROOT / "fed"
EURO_ROOT = SNAPSHOT_ROOT / "euro"
EVENT_ROOT = SNAPSHOT_ROOT / "events"
MANIFEST_PATH = SNAPSHOT_ROOT / "manifest.json"

EVENT_COLUMNS = [
    "event_date",
    "date_precision",
    "event_title",
    "event_category",
    "event_description",
    "event_source_table",
]


def _require_file(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(
            f"Public demo snapshot is missing: {path}. "
            "Run demo/export_public_snapshot.py locally with MySQL/XAMPP enabled, "
            "then commit demo/public_snapshot to GitHub."
        )
    return path


def snapshot_manifest() -> dict:
    path = _require_file(MANIFEST_PATH)
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> pd.DataFrame:
    path = _require_file(path)
    frame = pd.read_json(path, orient="records", lines=True)
    if "snapped_at" in frame.columns:
        frame["snapped_at"] = pd.to_datetime(frame["snapped_at"], errors="coerce")
    if "event_date" in frame.columns:
        frame["event_date"] = pd.to_datetime(frame["event_date"], errors="coerce")
    return frame


def _filter_dates(frame: pd.DataFrame, column: str, start_date=None, end_date=None) -> pd.DataFrame:
    output = frame.copy()
    if column not in output.columns:
        return output
    output[column] = pd.to_datetime(output[column], errors="coerce")
    output = output.dropna(subset=[column])
    if start_date is not None:
        output = output[output[column] >= pd.to_datetime(start_date)]
    if end_date is not None:
        output = output[output[column] <= pd.to_datetime(end_date)]
    return output.sort_values(column).reset_index(drop=True)


def load_snapshot_asset_data(
    assets_config: dict,
    asset_key: str,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    if asset_key not in assets_config:
        raise KeyError(f"Asset is not configured: {asset_key}")

    frame = _read_jsonl(ASSET_ROOT / f"{asset_key}.jsonl")
    frame = _filter_dates(frame, "snapped_at", start_date, end_date)
    return frame


def load_snapshot_events(start_date=None, end_date=None) -> pd.DataFrame:
    frames = []
    for table_name in ("bitcoin_historical_events", "world_historical_events"):
        path = EVENT_ROOT / f"{table_name}.jsonl"
        if path.exists():
            frames.append(_read_jsonl(path))
    if not frames:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    frame = pd.concat(frames, ignore_index=True)
    frame = _filter_dates(frame, "event_date", start_date, end_date)
    existing = [column for column in EVENT_COLUMNS if column in frame.columns]
    for column in EVENT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame[EVENT_COLUMNS].sort_values("event_date").reset_index(drop=True)


def load_snapshot_events_from_table(
    table_name: str,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    if table_name not in {"bitcoin_historical_events", "world_historical_events"}:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    path = EVENT_ROOT / f"{table_name}.jsonl"
    if not path.exists():
        return pd.DataFrame(columns=EVENT_COLUMNS)

    frame = _read_jsonl(path)
    frame = _filter_dates(frame, "event_date", start_date, end_date)
    for column in EVENT_COLUMNS:
        if column not in frame.columns:
            frame[column] = ""
    return frame[EVENT_COLUMNS].sort_values("event_date").reset_index(drop=True)


def _load_macro_series(macro_key: str, start_date=None, end_date=None) -> pd.DataFrame:
    fed_path = FED_ROOT / f"{macro_key}.jsonl"
    euro_path = EURO_ROOT / f"{macro_key}.jsonl"

    if fed_path.exists():
        path = fed_path
    elif euro_path.exists():
        path = euro_path
    else:
        raise FileNotFoundError(
            f"Snapshot macro series not found: {macro_key}. "
            "Regenerate demo/public_snapshot."
        )

    frame = _read_jsonl(path)
    frame = _filter_dates(frame, "snapped_at", start_date, end_date)
    if macro_key not in frame.columns:
        raise ValueError(f"Snapshot file {path} does not contain {macro_key}")
    return frame[["snapped_at", macro_key]].copy()


def load_snapshot_macro_pair(
    assets_config: dict,
    macro_key: str,
    market_asset: str,
    start_date=None,
    end_date=None,
) -> pd.DataFrame:
    macro = _load_macro_series(macro_key, start_date=start_date, end_date=end_date)

    market_raw = load_snapshot_asset_data(
        assets_config=assets_config,
        asset_key=market_asset,
        start_date=start_date,
        end_date=end_date,
    )
    market = market_raw[["snapped_at", "price"]].copy()
    market["price"] = pd.to_numeric(market["price"], errors="coerce")
    market = market.rename(columns={"price": market_asset})

    return align_macro_to_market_calendar(
        macro_df=macro,
        market_df=market,
        macro_column=macro_key,
        market_column=market_asset,
    )


def build_snapshot_multi_asset_price_frame(
    assets_config: dict,
    selected_assets: list,
    start_date=None,
    end_date=None,
    forward_fill: bool = False,
    return_load_report: bool = False,
):
    frames = []
    load_rows = []

    for asset_key in selected_assets:
        if asset_key not in assets_config:
            load_rows.append(
                {
                    "asset": asset_key,
                    "status": "failed",
                    "rows": 0,
                    "reason": "Asset is not configured",
                }
            )
            continue

        try:
            asset = load_snapshot_asset_data(
                assets_config,
                asset_key,
                start_date=start_date,
                end_date=end_date,
            )
            if asset.empty:
                load_rows.append(
                    {
                        "asset": asset_key,
                        "status": "empty",
                        "rows": 0,
                        "reason": "No valid price rows",
                    }
                )
                continue

            series = asset[["snapped_at", "price"]].copy()
            series["price"] = pd.to_numeric(series["price"], errors="coerce")
            series = series.dropna(subset=["snapped_at", "price"])
            series = (
                series.sort_values("snapped_at")
                .drop_duplicates("snapped_at", keep="last")
                .rename(columns={"price": asset_key})
                .reset_index(drop=True)
            )
            frames.append(series)
            load_rows.append(
                {
                    "asset": asset_key,
                    "status": "loaded",
                    "rows": len(series),
                    "reason": "",
                }
            )
        except Exception as exc:
            load_rows.append(
                {
                    "asset": asset_key,
                    "status": "failed",
                    "rows": 0,
                    "reason": str(exc),
                }
            )

    report = pd.DataFrame(load_rows)
    if not frames:
        empty = pd.DataFrame()
        return (empty, report) if return_load_report else empty

    merged = frames[0]
    for frame in frames[1:]:
        merged = pd.merge(merged, frame, on="snapped_at", how="outer")

    merged = merged.sort_values("snapped_at").reset_index(drop=True)
    if forward_fill:
        columns = [column for column in merged.columns if column != "snapped_at"]
        merged[columns] = merged[columns].ffill()

    return (merged, report) if return_load_report else merged


def snapshot_table_exists(table_name: str, assets_config: dict) -> bool:
    if table_name in {"bitcoin_historical_events", "world_historical_events"}:
        return (EVENT_ROOT / f"{table_name}.jsonl").exists()

    for asset_key, cfg in assets_config.items():
        if cfg.get("table_name") == table_name:
            return (ASSET_ROOT / f"{asset_key}.jsonl").exists()
    return False


def snapshot_table_columns(table_name: str, assets_config: dict) -> list[str]:
    if table_name in {"bitcoin_historical_events", "world_historical_events"}:
        path = EVENT_ROOT / f"{table_name}.jsonl"
        if not path.exists():
            return []
        return list(_read_jsonl(path).columns)

    for asset_key, cfg in assets_config.items():
        if cfg.get("table_name") == table_name:
            path = ASSET_ROOT / f"{asset_key}.jsonl"
            if not path.exists():
                return []
            return list(_read_jsonl(path).columns)
    return []
