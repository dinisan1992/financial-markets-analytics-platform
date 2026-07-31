from pathlib import Path
import argparse
import json
import sys
import zipfile

import pandas as pd


PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_config import ASSETS
from macro_data_loader import get_engine
from services.data_quality_service import (
    audit_event_coverage,
    build_audit_summary,
    build_pair_coverage_audit,
    run_asset_audit,
)


def build_parser():
    parser = argparse.ArgumentParser(description="Run a read-only financial data audit.")
    parser.add_argument(
        "--output-dir",
        default=str(PROJECT_ROOT / "audit_outputs"),
        help="Directory for aggregated audit files.",
    )
    parser.add_argument(
        "--skip-pairs",
        action="store_true",
        help="Skip the all-pairs correlation coverage report.",
    )
    return parser


def write_outputs(output_dir: Path, audit_tables):
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, frame in audit_tables.items():
        frame.to_csv(output_dir / f"{name}.csv", index=False, encoding="utf-8")

    summary = build_audit_summary(audit_tables)
    (output_dir / "audit_summary.json").write_text(
        json.dumps(summary, indent=2, default=str),
        encoding="utf-8",
    )

    zip_path = output_dir / "audit_outputs.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in output_dir.glob("*.csv"):
            archive.write(path, arcname=path.name)
        archive.write(output_dir / "audit_summary.json", arcname="audit_summary.json")

    return summary, zip_path


def main(argv=None):
    args = build_parser().parse_args(argv)
    output_dir = Path(args.output_dir).resolve()
    engine = get_engine()

    asset_audit, asset_frames = run_asset_audit(engine, ASSETS)
    audit_tables = {"asset_audit": asset_audit}

    if not args.skip_pairs:
        audit_tables["correlation_coverage"] = build_pair_coverage_audit(asset_frames)

    try:
        audit_tables["event_coverage"] = audit_event_coverage(engine, asset_frames)
    except Exception as exc:
        audit_tables["event_coverage"] = pd.DataFrame(
            [{"status": "ERROR", "error": str(exc)}]
        )

    summary, zip_path = write_outputs(output_dir, audit_tables)
    print(json.dumps(summary, indent=2, default=str))
    print(f"Audit ZIP: {zip_path}")


if __name__ == "__main__":
    main()
