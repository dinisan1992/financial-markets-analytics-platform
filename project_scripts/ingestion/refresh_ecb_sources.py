from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from macro_import_manifest import get_macro_import, get_macro_import_keys
from services.official_euro_source_service import (
    compare_euro_source_files,
    download_official_euro_source,
    probe_official_euro_source,
)


DEFAULT_IMPORT_KEYS = (
    "EURO_CARD_PAYMENTS",
    "EURO_BANK_LENDING_SURVEY",
    "EURO_BALANCE_SHEET_ITEMS",
)


def _supported_import_keys():
    return tuple(
        key
        for key in get_macro_import_keys("EURO")
        if get_macro_import(key).get("source_dataflow")
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Probe or stage complete official ECB CSV datasets. This command "
            "never replaces active CSVs and never writes to SQL."
        )
    )
    parser.add_argument("import_keys", nargs="*", metavar="IMPORT_KEY")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download complete datasets into the staging directory.",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Compare staged datasets with active CSVs using a disk-backed index.",
    )
    parser.add_argument("--staging-dir", type=Path)
    parser.add_argument("--workspace-dir", type=Path)
    parser.add_argument("--chunk-size", type=int, default=25_000)
    args = parser.parse_args(argv)
    supported = set(_supported_import_keys())
    args.import_keys = args.import_keys or list(DEFAULT_IMPORT_KEYS)
    invalid = sorted(set(args.import_keys) - supported)
    if invalid:
        parser.error(
            "unsupported import key(s): "
            + ", ".join(invalid)
            + "; choose from "
            + ", ".join(sorted(supported))
        )
    if (args.download or args.compare) and args.staging_dir is None:
        parser.error("--staging-dir is required with --download or --compare")
    return args


def _print_probe(probe):
    print(
        f"{probe.import_key}: HTTP {probe.status_code} | "
        f"{probe.dataflow} | latest sample={probe.time_period} | "
        f"columns={len(probe.columns)}",
        flush=True,
    )


def main(argv=None):
    args = parse_args(argv)
    started = datetime.now(timezone.utc)
    payload = {
        "started_at_utc": started.isoformat(),
        "requested_imports": list(args.import_keys),
        "mode": "download" if args.download else "probe",
        "database_write_performed": False,
        "active_csv_write_performed": False,
        "results": [],
        "errors": [],
    }
    progress_markers = {}

    def download_progress(import_key, downloaded):
        marker = downloaded // (256 * 1024**2)
        if marker > progress_markers.get(import_key, 0):
            progress_markers[import_key] = marker
            print(
                f"  {import_key}: {downloaded / 1024**3:.2f} GiB downloaded",
                flush=True,
            )

    def compare_progress(dataset, rows):
        marker = rows // 500_000
        key = f"{dataset}"
        if marker > progress_markers.get(key, 0):
            progress_markers[key] = marker
            print(f"  {dataset}: {rows:,} rows indexed", flush=True)

    staging_dir = args.staging_dir.expanduser().resolve() if args.staging_dir else None
    workspace_dir = (
        args.workspace_dir.expanduser().resolve()
        if args.workspace_dir
        else staging_dir
    )

    for import_key in args.import_keys:
        progress_markers.pop("source_rows", None)
        progress_markers.pop("target_rows", None)
        print(f"ECB source: {import_key}", flush=True)
        result = {"import_key": import_key}
        try:
            probe = probe_official_euro_source(import_key)
            result["probe"] = probe.to_dict()
            _print_probe(probe)
            if args.download:
                download = download_official_euro_source(
                    import_key,
                    staging_dir,
                    progress_callback=download_progress,
                )
                result["download"] = download.to_dict()
                print(
                    f"  staged: {download.bytes / 1024**3:.2f} GiB | "
                    f"SHA-256 {download.sha256}",
                    flush=True,
                )
            if args.compare:
                contract = get_macro_import(import_key)
                candidate_path = staging_dir / Path(contract["csv_path"]).name
                comparison = compare_euro_source_files(
                    import_key,
                    candidate_path,
                    workspace_dir=workspace_dir,
                    chunk_size=args.chunk_size,
                    progress_callback=compare_progress,
                )
                result["comparison"] = comparison.to_dict()
                print(
                    f"  compared: candidate={comparison.candidate_rows:,} | "
                    f"active={comparison.active_rows:,} | "
                    f"new={comparison.new_keys:,} | "
                    f"removed={comparison.removed_keys:,} | "
                    f"changed={comparison.changed_rows:,}",
                    flush=True,
                )
            payload["results"].append(result)
        except Exception as exc:
            payload["errors"].append(
                {
                    "import_key": import_key,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "database_write_performed": False,
                    "active_csv_write_performed": False,
                }
            )
            print(f"  ERROR: {type(exc).__name__}: {exc}", flush=True)

    completed = datetime.now(timezone.utc)
    payload["completed_at_utc"] = completed.isoformat()
    payload["elapsed_seconds"] = round((completed - started).total_seconds(), 3)
    if staging_dir is not None:
        staging_dir.mkdir(parents=True, exist_ok=True)
        report_path = staging_dir / "ecb_source_refresh.json"
        report_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        print(f"Report: {report_path}")
    print("SQL writes: 0 | active CSV writes: 0")
    return 1 if payload["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
