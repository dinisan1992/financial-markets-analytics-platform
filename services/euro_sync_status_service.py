from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from macro_import_manifest import get_macro_import, get_macro_import_keys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_ROOT = PROJECT_ROOT / "audit_outputs"

STATUS_COLUMNS = (
    "import_key",
    "table_name",
    "status",
    "source_rows",
    "target_rows",
    "planned_inserts",
    "planned_updates",
    "target_only_rows",
    "unchanged_rows",
    "write_ready",
    "idempotent",
    "blockers",
    "source_file",
    "source_bytes",
    "source_modified_utc",
    "source_age_days",
    "report_generated_utc",
    "report_file",
    "source_provider",
    "source_reference",
    "database_write_performed",
)


def _as_utc_timestamp(value=None):
    if value is None:
        return pd.Timestamp.now(tz="UTC")
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _infer_import_key(path: Path, import_keys):
    filename = path.name.lower()
    for import_key in import_keys:
        if filename.startswith(f"{import_key.lower()}_sync_"):
            return import_key
    return None


def _latest_report_candidates(report_root: Path, import_keys):
    candidates = {}
    if not report_root.exists():
        return candidates

    for path in report_root.rglob("*_sync_*.json"):
        payload = None
        parse_error = False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            parse_error = True

        import_key = None
        if isinstance(payload, dict):
            import_key = str(payload.get("import_key", "")).upper() or None
        if import_key not in import_keys:
            import_key = _infer_import_key(path, import_keys)
        if import_key is None:
            continue

        modified_ns = path.stat().st_mtime_ns
        current = candidates.get(import_key)
        if current is None or modified_ns > current[0]:
            candidates[import_key] = (modified_ns, path, payload, parse_error)

    return candidates


def _safe_int(value):
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _empty_status_row(import_key, contract):
    return {
        "import_key": import_key,
        "table_name": contract["table_name"],
        "status": "NOT_AUDITED",
        "source_rows": 0,
        "target_rows": 0,
        "planned_inserts": 0,
        "planned_updates": 0,
        "target_only_rows": 0,
        "unchanged_rows": 0,
        "write_ready": False,
        "idempotent": False,
        "blockers": "",
        "source_file": Path(contract["csv_path"]).name,
        "source_bytes": 0,
        "source_modified_utc": pd.NaT,
        "source_age_days": pd.NA,
        "report_generated_utc": pd.NaT,
        "report_file": "",
        "source_provider": contract["source_provider"],
        "source_reference": contract["source_reference"],
        "database_write_performed": False,
    }


def load_latest_euro_sync_status(report_root=None, as_of=None):
    """Load the latest saved sync plan for every EURO import contract.

    This function only reads small JSON reports. It never scans source CSVs,
    connects to MySQL or executes a synchronization.
    """
    report_root = Path(report_root or DEFAULT_REPORT_ROOT).expanduser().resolve()
    as_of = _as_utc_timestamp(as_of)
    import_keys = tuple(get_macro_import_keys("EURO"))
    candidates = _latest_report_candidates(report_root, import_keys)
    rows = []

    for import_key in import_keys:
        contract = get_macro_import(import_key)
        row = _empty_status_row(import_key, contract)
        candidate = candidates.get(import_key)
        if candidate is None:
            rows.append(row)
            continue

        modified_ns, path, payload, parse_error = candidate
        row["report_generated_utc"] = pd.Timestamp(modified_ns, unit="ns", tz="UTC")
        row["report_file"] = path.relative_to(report_root).as_posix()
        if parse_error or not isinstance(payload, dict):
            row["blockers"] = "report_parse_error"
            rows.append(row)
            continue

        plan = payload.get("plan")
        if not isinstance(plan, dict):
            plan = payload.get("result", {}).get("plan", {})
        if not isinstance(plan, dict) or not plan:
            row["blockers"] = "sync_plan_missing"
            rows.append(row)
            continue

        blockers = plan.get("blockers") or []
        if isinstance(blockers, str):
            blockers = [blockers]
        planned_inserts = _safe_int(plan.get("planned_inserts"))
        planned_updates = _safe_int(plan.get("planned_updates"))
        target_only_rows = _safe_int(plan.get("target_only_rows"))
        idempotent = bool(plan.get("idempotent", False))

        if blockers:
            status = "BLOCKED"
        elif idempotent:
            status = "EXACT"
        else:
            status = "CHANGES"

        source_modified_ns = _safe_int(plan.get("source_modified_ns"))
        source_modified_utc = (
            pd.Timestamp(source_modified_ns, unit="ns", tz="UTC")
            if source_modified_ns > 0
            else pd.NaT
        )
        source_age_days = pd.NA
        if not pd.isna(source_modified_utc):
            source_age_days = max(0, int((as_of - source_modified_utc).total_seconds() // 86400))

        source_path = str(plan.get("source_path", ""))
        database_write_performed = bool(
            payload.get("database_write_performed", False)
            or plan.get("database_write_performed", False)
        )
        row.update(
            {
                "table_name": plan.get("table_name") or contract["table_name"],
                "status": status,
                "source_rows": _safe_int(plan.get("source_rows")),
                "target_rows": _safe_int(plan.get("target_rows")),
                "planned_inserts": planned_inserts,
                "planned_updates": planned_updates,
                "target_only_rows": target_only_rows,
                "unchanged_rows": _safe_int(plan.get("unchanged_rows")),
                "write_ready": bool(plan.get("write_ready", False)),
                "idempotent": idempotent,
                "blockers": ", ".join(str(item) for item in blockers),
                "source_file": Path(source_path).name or Path(contract["csv_path"]).name,
                "source_bytes": _safe_int(plan.get("source_bytes")),
                "source_modified_utc": source_modified_utc,
                "source_age_days": source_age_days,
                "source_provider": contract["source_provider"],
                "source_reference": contract["source_reference"],
                "database_write_performed": database_write_performed,
            }
        )
        rows.append(row)

    frame = pd.DataFrame(rows, columns=STATUS_COLUMNS)
    frame["source_age_days"] = frame["source_age_days"].astype("Int64")
    return frame


def summarize_euro_sync_status(status_frame: pd.DataFrame):
    statuses = status_frame.get("status", pd.Series(dtype=str))
    writes = status_frame.get(
        "database_write_performed",
        pd.Series(dtype=bool),
    ).fillna(False)
    numeric = lambda name: pd.to_numeric(
        status_frame.get(name, pd.Series(dtype=float)), errors="coerce"
    ).fillna(0)

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Latest saved read-only EURO synchronization plans",
        "contracts": len(status_frame),
        "exact": int(statuses.eq("EXACT").sum()),
        "changes": int(statuses.eq("CHANGES").sum()),
        "blocked": int(statuses.eq("BLOCKED").sum()),
        "not_audited": int(statuses.eq("NOT_AUDITED").sum()),
        "planned_inserts": int(numeric("planned_inserts").sum()),
        "planned_updates": int(numeric("planned_updates").sum()),
        "target_only_rows": int(numeric("target_only_rows").sum()),
        "database_writes_reported": int(writes.sum()),
    }
