from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

import pandas as pd


DEMO_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DEMO_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_config import ASSETS  # noqa: E402
from euro_data_loader import load_euro_series  # noqa: E402
from euro_series_config import EURO_SERIES  # noqa: E402
from macro_config import MACRO_ASSETS  # noqa: E402
from macro_data_loader import get_engine, load_macro  # noqa: E402
from services import data_access_service  # noqa: E402


SNAPSHOT_ROOT = DEMO_ROOT / "public_snapshot"
SAFE_ASSET_COLUMNS = [
    "snapped_at",
    "price",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "total_volume",
    "volume",
]
EVENT_TABLES = ("bitcoin_historical_events", "world_historical_events")


def _write_jsonl(frame: pd.DataFrame, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_json(
        path,
        orient="records",
        lines=True,
        date_format="iso",
        date_unit="ms",
        double_precision=15,
        force_ascii=False,
    )
    payload = path.read_bytes()
    return {
        "path": path.relative_to(DEMO_ROOT).as_posix(),
        "rows": int(len(frame)),
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def _normalise_asset_frame(frame: pd.DataFrame) -> pd.DataFrame:
    columns = [column for column in SAFE_ASSET_COLUMNS if column in frame.columns]
    if "snapped_at" not in columns:
        raise ValueError("Asset snapshot is missing snapped_at")
    if "price" not in columns:
        raise ValueError("Asset snapshot is missing price")

    output = frame[columns].copy()
    output["snapped_at"] = pd.to_datetime(output["snapped_at"], errors="coerce")
    output = output.dropna(subset=["snapped_at"]).sort_values("snapped_at")
    output = output.drop_duplicates("snapped_at", keep="last").reset_index(drop=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export an exact read-only public snapshot from the local project database."
    )
    parser.add_argument(
        "--start",
        default="2000-01-01",
        help="Earliest date to publish. Default: 2000-01-01",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Optional final date. Default: all available data",
    )
    args = parser.parse_args()

    print("Creating exact public demo snapshot.")
    print("MySQL/XAMPP must be running for this export only.")
    print(f"Date range: {args.start} -> {args.end or 'latest available'}")
    print(f"Destination: {SNAPSHOT_ROOT}")

    if SNAPSHOT_ROOT.exists():
        shutil.rmtree(SNAPSHOT_ROOT)

    (SNAPSHOT_ROOT / "assets").mkdir(parents=True)
    (SNAPSHOT_ROOT / "fed").mkdir(parents=True)
    (SNAPSHOT_ROOT / "euro").mkdir(parents=True)
    (SNAPSHOT_ROOT / "events").mkdir(parents=True)

    engine = get_engine()
    manifest = {
        "snapshot_format": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "date_start": args.start,
        "date_end": args.end,
        "contains_credentials": False,
        "contains_database_connection_data": False,
        "data_policy": (
            "Read-only static snapshot of the same market/macro observations used "
            "by the local application. Only whitelisted analytical columns are exported."
        ),
        "assets": {},
        "fed": {},
        "euro": {},
        "events": {},
    }

    print("\n[1/4] Market assets")
    for index, asset_key in enumerate(ASSETS, start=1):
        frame = data_access_service.load_asset_data(
            engine=engine,
            assets_config=ASSETS,
            asset_key=asset_key,
            start_date=args.start,
            end_date=args.end,
        )
        frame = _normalise_asset_frame(frame)
        metadata = _write_jsonl(frame, SNAPSHOT_ROOT / "assets" / f"{asset_key}.jsonl")
        manifest["assets"][asset_key] = metadata
        print(f"  {index:02d}/{len(ASSETS)} {asset_key}: {len(frame):,} rows")

    print("\n[2/4] Historical events")
    for table_name in EVENT_TABLES:
        frame = data_access_service.load_events_from_table(
            engine=engine,
            table_name=table_name,
            start_date=None,
            end_date=args.end,
        )
        metadata = _write_jsonl(
            frame,
            SNAPSHOT_ROOT / "events" / f"{table_name}.jsonl",
        )
        manifest["events"][table_name] = metadata
        print(f"  {table_name}: {len(frame):,} rows")

    print("\n[3/4] FED macro")
    for macro_key in MACRO_ASSETS:
        frame = load_macro(
            macro_key=macro_key,
            engine=engine,
            start_date=args.start,
            end_date=args.end,
        )
        metadata = _write_jsonl(frame, SNAPSHOT_ROOT / "fed" / f"{macro_key}.jsonl")
        manifest["fed"][macro_key] = metadata
        print(f"  {macro_key}: {len(frame):,} rows")

    print("\n[4/4] EURO macro")
    enabled_euro = [
        key for key, cfg in EURO_SERIES.items()
        if cfg.get("enabled", True) is True
    ]
    for euro_key in enabled_euro:
        frame = load_euro_series(
            series_key=euro_key,
            engine=engine,
            start_date=args.start,
            end_date=args.end,
        )
        metadata = _write_jsonl(frame, SNAPSHOT_ROOT / "euro" / f"{euro_key}.jsonl")
        manifest["euro"][euro_key] = metadata
        print(f"  {euro_key}: {len(frame):,} rows")

    manifest_path = SNAPSHOT_ROOT / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    total_bytes = sum(
        item["bytes"]
        for section in ("assets", "fed", "euro", "events")
        for item in manifest[section].values()
    )
    print("\nSNAPSHOT EXPORT PASSED")
    print(f"Assets: {len(manifest['assets'])}")
    print(f"FED series: {len(manifest['fed'])}")
    print(f"EURO series: {len(manifest['euro'])}")
    print(f"Event tables: {len(manifest['events'])}")
    print(f"Payload size: {total_bytes / (1024 * 1024):.2f} MiB")
    print("")
    print("Next:")
    print("  1. Turn XAMPP/MySQL OFF.")
    print("  2. Run: .\\demo\\run_demo.ps1")
    print("  3. Compare BTC 2020->today with the normal application.")
    print("  4. Commit demo/public_snapshot to GitHub.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
