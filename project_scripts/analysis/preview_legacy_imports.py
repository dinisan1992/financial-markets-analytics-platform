from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = next(
    parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_config import ASSETS
from macro_data_loader import get_engine
from services.legacy_import_service import (
    build_duplicate_group_preview,
    build_existing_duplicate_summary,
    preview_legacy_csv_import,
)


DEFAULT_ASSETS = ["EURO", "YUAN", "LIBRA", "SSECOMPOSITE"]


def build_parser():
    parser = argparse.ArgumentParser(
        description="Preview legacy market imports and duplicate remediation without SQL writes."
    )
    parser.add_argument(
        "--assets",
        nargs="+",
        default=DEFAULT_ASSETS,
        choices=DEFAULT_ASSETS,
        help="Legacy assets to inspect. Default: all four affected assets.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "audit_outputs" / "import_dry_runs"),
        help="Local Git-ignored directory for aggregated previews.",
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="Print the summary without writing local preview files.",
    )
    return parser


def load_existing_frame(engine, table_name):
    query = f"""
    SELECT snapped_at, price, total_volume
    FROM `{table_name}`
    ORDER BY snapped_at
    """
    return pd.read_sql(query, engine)


def inspect_asset(engine, asset_key):
    asset = ASSETS[asset_key]
    table_name = asset["table_name"]
    csv_path = Path(asset["csv_path"])
    existing = load_existing_frame(engine, table_name)

    summary = build_existing_duplicate_summary(asset_key, table_name, existing)
    summary.update(
        {
            "csv_path": csv_path.name,
            "csv_available": csv_path.exists(),
            "source_status": "available" if csv_path.exists() else "missing",
        }
    )

    duplicate_preview = build_duplicate_group_preview(existing)
    duplicate_preview.insert(0, "asset", asset_key)
    action_preview = pd.DataFrame()

    if csv_path.exists():
        report, action_preview = preview_legacy_csv_import(
            asset=asset_key,
            table=table_name,
            csv_path=csv_path,
            existing_frame=existing,
        )
        summary.update(report.to_dict())
        action_preview.insert(0, "asset", asset_key)

    return summary, duplicate_preview, action_preview


def write_outputs(output_dir, summary_frame, duplicate_frame, action_frame):
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_frame.to_csv(output_dir / "legacy_import_summary.csv", index=False)
    duplicate_frame.to_csv(output_dir / "legacy_duplicate_groups.csv", index=False)
    action_frame.to_csv(output_dir / "legacy_import_actions.csv", index=False)
    (output_dir / "legacy_import_summary.json").write_text(
        json.dumps(summary_frame.to_dict(orient="records"), indent=2, default=str),
        encoding="utf-8",
    )


def main(argv=None):
    args = build_parser().parse_args(argv)
    engine = get_engine()
    summaries = []
    duplicate_previews = []
    action_previews = []

    for asset_key in args.assets:
        summary, duplicate_preview, action_preview = inspect_asset(engine, asset_key)
        summaries.append(summary)
        duplicate_previews.append(duplicate_preview)
        if not action_preview.empty:
            action_previews.append(action_preview)

    summary_frame = pd.DataFrame(summaries)
    duplicate_frame = pd.concat(duplicate_previews, ignore_index=True)
    action_frame = (
        pd.concat(action_previews, ignore_index=True)
        if action_previews
        else pd.DataFrame()
    )

    print(summary_frame.to_string(index=False))
    print("Database write performed: False")

    if not args.no_output:
        output_dir = Path(args.output_dir).resolve()
        write_outputs(output_dir, summary_frame, duplicate_frame, action_frame)
        print(f"Preview outputs: {output_dir}")


if __name__ == "__main__":
    main()
