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
from services.euro_field_difference_service import (
    DEFAULT_CHUNK_SIZE,
    audit_euro_field_differences,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Compare sampled EURO CSV and MySQL rows field by field. "
            "The command issues SELECT statements only."
        )
    )
    parser.add_argument(
        "plan_files",
        nargs="+",
        type=Path,
        metavar="PLAN_JSON",
        help="Plan or streaming-audit JSON containing mismatch_key_samples.",
    )
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--sample-limit", type=int, default=None)
    parser.add_argument("--example-limit", type=int, default=3)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "euro_field_differences",
    )
    return parser.parse_args()


def _read_sample(path, sample_limit):
    path = path.expanduser().resolve()
    payload = json.loads(path.read_text(encoding="utf-8"))
    plan = payload.get("plan", payload)
    import_key = str(plan.get("import_key", "")).upper()
    sample_keys = list(plan.get("mismatch_key_samples") or ())
    if not import_key:
        raise ValueError(f"Missing import_key in {path.name}")
    if not sample_keys:
        raise ValueError(f"No mismatch_key_samples in {path.name}")
    if sample_limit is not None:
        sample_keys = sample_keys[:max(1, int(sample_limit))]
    return import_key, sample_keys, path.name


def main():
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    results = []
    errors = []

    print(
        "EURO field-difference audit: read-only MySQL access; "
        "no SQL writes are issued.",
        flush=True,
    )
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        for plan_file in args.plan_files:
            try:
                import_key, sample_keys, report_name = _read_sample(
                    plan_file,
                    args.sample_limit,
                )
                print(
                    f"Auditing {import_key}: {len(sample_keys)} sampled rows...",
                    flush=True,
                )
                audit = audit_euro_field_differences(
                    engine,
                    import_key,
                    sample_keys,
                    chunk_size=args.chunk_size,
                    example_limit=args.example_limit,
                )
                result = audit.to_dict()
                result["input_report_file"] = report_name
                results.append(result)
                report_path = output_dir / f"{import_key.lower()}.json"
                report_path.write_text(
                    json.dumps(result, indent=2, ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
                print(
                    f"  compared={audit.compared_rows} | "
                    f"differing={audit.differing_rows} | "
                    f"fields={len(audit.column_differences)}",
                    flush=True,
                )
            except Exception as exc:
                errors.append({
                    "input_report_file": Path(plan_file).name,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "database_write_performed": False,
                })
                print(f"  ERROR: {type(exc).__name__}: {exc}", flush=True)
    finally:
        engine.dispose()

    completed = datetime.now(timezone.utc)
    summary = {
        "started_at_utc": started.isoformat(),
        "completed_at_utc": completed.isoformat(),
        "elapsed_seconds": round((completed - started).total_seconds(), 3),
        "completed_imports": len(results),
        "error_count": len(errors),
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
    digest = sha256(summary_bytes).hexdigest().upper()
    (output_dir / "summary.sha256").write_text(
        f"{digest}  summary.json\n",
        encoding="ascii",
    )
    if results:
        rows = []
        for result in results:
            for column in result["column_differences"]:
                rows.append({
                    "import_key": result["import_key"],
                    **{
                        key: value
                        for key, value in column.items()
                        if key != "examples"
                    },
                })
        pd.DataFrame(rows).to_csv(
            output_dir / "column_differences.csv",
            index=False,
            lineterminator="\r\n",
        )

    print(f"Report: {summary_path}")
    print(f"SHA-256: {digest}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
