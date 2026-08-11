from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.euro_sync_status_service import (
    load_latest_euro_sync_status,
    summarize_euro_sync_status,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Consolidate existing EURO sync reports without scanning data or writing MySQL."
    )
    parser.add_argument("--report-root", type=Path, default=ROOT / "audit_outputs")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "euro_sync_status",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    status = load_latest_euro_sync_status(args.report_root)
    summary = summarize_euro_sync_status(status)

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    status_path = output_dir / "euro_sync_status.csv"
    summary_path = output_dir / "euro_sync_summary.json"
    status.to_csv(status_path, index=False)
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=True))
    print("Database writes: disabled")
    print(f"Status report: {status_path}")
    print(f"Summary report: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
