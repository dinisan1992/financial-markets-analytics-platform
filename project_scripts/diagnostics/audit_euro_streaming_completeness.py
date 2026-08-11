from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import pandas as pd
from sqlalchemy import create_engine


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import get_sqlalchemy_database_url
from services.euro_streaming_validation_service import (
    DEFAULT_CHUNK_SIZE,
    TARGET_IMPORT_KEYS,
    audit_euro_source_against_target,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Read-only, memory-bounded comparison of EURO CSV sources with MySQL."
        )
    )
    parser.add_argument(
        "import_keys",
        nargs="*",
        default=None,
        metavar="IMPORT_KEY",
    )
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--sample-limit", type=int, default=10)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "euro_streaming_validation",
    )
    parser.add_argument(
        "--workspace-dir",
        type=Path,
        default=None,
        help="Existing directory for the temporary SQLite comparison store.",
    )
    parser.add_argument(
        "--fail-on-difference",
        action="store_true",
        help="Return exit code 2 when a completed comparison finds differences.",
    )
    args = parser.parse_args()
    if not args.import_keys:
        args.import_keys = list(TARGET_IMPORT_KEYS)
    invalid = sorted(set(args.import_keys) - set(TARGET_IMPORT_KEYS))
    if invalid:
        parser.error(
            "unsupported import key(s): "
            + ", ".join(invalid)
            + "; choose from "
            + ", ".join(TARGET_IMPORT_KEYS)
        )
    return args


def main():
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace_dir = (
        args.workspace_dir.expanduser().resolve()
        if args.workspace_dir is not None
        else None
    )
    if workspace_dir is not None:
        workspace_dir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc)
    results = []
    errors = []
    last_progress = {}

    def progress(stage, import_key, rows):
        marker = (stage, import_key)
        previous = last_progress.get(marker, 0)
        if rows - previous >= 250_000:
            print(f"  {import_key} {stage}: {rows:,} rows", flush=True)
            last_progress[marker] = rows

    print(
        "EURO streaming audit: read-only MySQL access; no SQL writes are issued.",
        flush=True,
    )
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        for import_key in args.import_keys:
            print(f"Auditing {import_key}...", flush=True)
            try:
                validation = audit_euro_source_against_target(
                    engine,
                    import_key,
                    chunk_size=args.chunk_size,
                    workspace_dir=workspace_dir,
                    sample_limit=args.sample_limit,
                    progress_callback=progress,
                )
            except Exception as exc:
                error = {
                    "import_key": import_key,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "database_write_performed": False,
                }
                errors.append(error)
                print(f"  ERROR: {type(exc).__name__}: {exc}", flush=True)
                continue

            payload = validation.to_dict()
            results.append(payload)
            table_report = output_dir / f"{import_key.lower()}.json"
            table_report.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
            print(
                f"  complete: source={validation.source_rows:,} | "
                f"target={validation.target_rows:,} | "
                f"missing={validation.source_rows_missing_from_target:,} | "
                f"mismatches={validation.row_hash_mismatches:,} | "
                f"valid={validation.valid}",
                flush=True,
            )
    finally:
        engine.dispose()

    completed = datetime.now(timezone.utc)
    summary = {
        "started_at_utc": started.isoformat(),
        "completed_at_utc": completed.isoformat(),
        "elapsed_seconds": round((completed - started).total_seconds(), 3),
        "requested_imports": list(args.import_keys),
        "completed_imports": len(results),
        "error_count": len(errors),
        "valid_count": sum(bool(result["valid"]) for result in results),
        "difference_count": sum(not bool(result["valid"]) for result in results),
        "database_write_performed": False,
        "results": results,
        "errors": errors,
    }
    summary_path = output_dir / "summary.json"
    summary_bytes = json.dumps(
        summary,
        indent=2,
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")
    summary_path.write_bytes(summary_bytes)
    summary_digest = sha256(summary_bytes).hexdigest().upper()
    (output_dir / "summary.sha256").write_text(
        f"{summary_digest}  summary.json\n",
        encoding="ascii",
    )
    if results:
        scalar_rows = []
        for result in results:
            scalar_rows.append({
                key: value
                for key, value in result.items()
                if not isinstance(value, (list, tuple, dict))
            })
        pd.DataFrame(scalar_rows).to_csv(output_dir / "summary.csv", index=False)

    print(f"Report: {summary_path}")
    print(f"SHA-256: {summary_digest}")
    if errors:
        return 1
    if args.fail_on_difference and any(not result["valid"] for result in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
