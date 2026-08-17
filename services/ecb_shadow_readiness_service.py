from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from math import ceil
from pathlib import Path
import json
import shutil

from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.euro_backup_restore_service import table_schema_signature
from services.euro_large_rebuild_service import (
    DEFAULT_OPERATING_RESERVE_BYTES,
    SHADOW_ESTIMATE_SAFETY_FACTOR,
)
from services.euro_rebuild_service import (
    build_rollback_statement,
    build_shadow_schema_statements,
    build_swap_statement,
    retained_table_name,
    shadow_table_name,
    validate_scoped_backup,
)
from services.market_data_sync_service import validate_identifier


ECB_IMPORT_KEYS = (
    "EURO_BANK_LENDING_SURVEY",
    "EURO_CARD_PAYMENTS",
    "EURO_BALANCE_SHEET_ITEMS",
)
PLAN_VERSION = "v079"


def validate_ecb_import_key(import_key):
    key = str(import_key).upper()
    if key not in ECB_IMPORT_KEYS:
        raise ValueError(f"Unsupported ECB shadow import: {key}")
    return key


def build_confirmation(import_key):
    key = validate_ecb_import_key(import_key)
    return f"BUILD_{key}_{PLAN_VERSION.upper()}_SHADOW"


def swap_confirmation(import_key):
    key = validate_ecb_import_key(import_key)
    return f"SWAP_{key}_{PLAN_VERSION.upper()}_SHADOW"


def file_sha256(path, chunk_size=8 * 1024**2):
    path = Path(path).expanduser().resolve()
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_json(path):
    path = Path(path).expanduser().resolve()
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def pinned_plans(payload):
    if payload.get("database_write_performed") is not False:
        raise ValueError("Pinned plan must confirm zero database writes")
    if payload.get("active_csv_write_performed") is not False:
        raise ValueError("Pinned plan must confirm zero active CSV writes")
    if payload.get("statements_executed") is not False:
        raise ValueError("Pinned plan must confirm zero executed statements")
    for plan in payload.get("plans", ()):
        if plan.get("sql_executed") is not False:
            raise ValueError(
                "Every pinned ECB plan must confirm zero executed SQL"
            )
    plans = {
        validate_ecb_import_key(plan["import_key"]): plan
        for plan in payload.get("plans", ())
    }
    missing = sorted(set(ECB_IMPORT_KEYS) - set(plans))
    if missing:
        raise ValueError(f"Pinned ECB plan is incomplete: {missing}")
    return plans


def validate_audit_payload(import_key, payload, candidate_path):
    key = validate_ecb_import_key(import_key)
    candidate_path = Path(candidate_path).expanduser().resolve()
    if str(payload.get("import_key", "")).upper() != key:
        raise ValueError(f"Audit import key mismatch for {key}")
    if payload.get("database_write_performed") is not False:
        raise ValueError(f"Audit does not confirm zero database writes for {key}")
    if Path(payload.get("source_path", "")).expanduser().resolve() != candidate_path:
        raise ValueError(f"Audit source path mismatch for {key}")
    if int(payload.get("source_rows", 0)) < 1:
        raise ValueError(f"Audit contains no source rows for {key}")
    return payload


def database_state_query(table_name):
    table_name = validate_identifier(table_name)
    return text(
        f"""
        SELECT
            @@datadir AS mysql_data_dir,
            (SELECT COUNT(*) FROM `{table_name}`) AS target_rows,
            COALESCE((
                SELECT data_length + index_length
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_name = :table_name
            ), 0) AS active_table_bytes
        """
    )


def collect_database_state(engine, table_name):
    table_name = validate_identifier(table_name)
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        raise ValueError(f"Active ECB table not found: {table_name}")
    with engine.connect() as connection:
        state = dict(
            connection.execute(
                database_state_query(table_name),
                {"table_name": table_name},
            ).mappings().one()
        )
    state["target_rows"] = int(state["target_rows"] or 0)
    state["active_table_bytes"] = int(state["active_table_bytes"] or 0)
    state["schema_signature"] = table_schema_signature(engine, table_name)
    return state


def estimate_capacity(
    database_state,
    *,
    source_rows,
    comparison_store_bytes,
    workspace_dir,
    operating_reserve_bytes=DEFAULT_OPERATING_RESERVE_BYTES,
):
    target_rows = int(database_state["target_rows"])
    active_table_bytes = int(database_state["active_table_bytes"])
    if target_rows < 1 or active_table_bytes < 1:
        raise ValueError("Cannot estimate ECB shadow capacity from an empty table")
    raw_shadow_bytes = ceil(active_table_bytes * int(source_rows) / target_rows)
    estimated_shadow_bytes = ceil(
        raw_shadow_bytes * SHADOW_ESTIMATE_SAFETY_FACTOR
    )
    reserve_bytes = max(0, int(operating_reserve_bytes))
    mysql_dir = Path(database_state["mysql_data_dir"]).expanduser().resolve()
    workspace_dir = Path(workspace_dir).expanduser().resolve()
    if not mysql_dir.is_dir():
        raise FileNotFoundError(f"MySQL data directory not found: {mysql_dir}")
    if not workspace_dir.is_dir():
        raise FileNotFoundError(f"ECB workspace not found: {workspace_dir}")
    mysql_free = shutil.disk_usage(mysql_dir).free
    workspace_free = shutil.disk_usage(workspace_dir).free
    same_volume = mysql_dir.drive.lower() == workspace_dir.drive.lower()
    mysql_required = estimated_shadow_bytes + reserve_bytes
    workspace_required = int(comparison_store_bytes) + reserve_bytes
    combined_required = (
        estimated_shadow_bytes + int(comparison_store_bytes) + reserve_bytes
        if same_volume
        else None
    )
    capacity_pass = (
        mysql_free >= combined_required
        if same_volume
        else mysql_free >= mysql_required and workspace_free >= workspace_required
    )
    return {
        "raw_shadow_estimate_bytes": raw_shadow_bytes,
        "shadow_estimate_safety_factor": SHADOW_ESTIMATE_SAFETY_FACTOR,
        "estimated_shadow_bytes": estimated_shadow_bytes,
        "comparison_store_peak_bytes": int(comparison_store_bytes),
        "operating_reserve_bytes": reserve_bytes,
        "mysql_free_bytes": mysql_free,
        "workspace_free_bytes": workspace_free,
        "workspace_and_mysql_same_volume": same_volume,
        "combined_required_bytes": combined_required,
        "mysql_required_bytes": mysql_required,
        "workspace_required_bytes": workspace_required,
        "capacity_pass": bool(capacity_pass),
        "backup_space_included": False,
        "backup_recommendation": "Keep the verified backup on a separate volume.",
    }


def readiness_blockers(pin, audit, candidate, backup, database, capacity, names):
    blockers = []
    comparisons = (
        (candidate["sha256"] != str(pin["candidate_sha256"]).upper(), "candidate_hash_changed"),
        (backup["sha256"] != str(pin["backup_sha256"]).upper(), "backup_hash_changed"),
        (int(audit["source_rows"]) != int(pin["candidate_rows"]), "candidate_row_count_changed"),
        (int(database["target_rows"]) != int(pin["active_rows"]), "active_row_count_changed"),
        (int(audit["target_rows"]) != int(database["target_rows"]), "audit_target_checkpoint_changed"),
        (audit.get("period_type_safe") is not True, "unsafe_time_period_type"),
        (int(audit.get("source_null_business_keys", 0)) != 0, "source_null_business_keys"),
        (int(audit.get("source_invalid_numeric_rows", 0)) != 0, "source_invalid_numeric_rows"),
        (int(audit.get("source_duplicate_business_key_groups", 0)) != 0, "source_duplicate_business_keys"),
        (int(audit.get("target_null_business_keys", 0)) != 0, "target_null_business_keys"),
        (int(audit.get("target_duplicate_business_key_groups", 0)) != 0, "target_duplicate_business_keys"),
        (names["shadow_exists"], "shadow_table_already_exists"),
        (names["retained_exists"], "retained_table_already_exists"),
        (not capacity["capacity_pass"], "insufficient_capacity"),
    )
    blockers.extend(reason for failed, reason in comparisons if failed)
    return tuple(blockers)


def build_ecb_shadow_readiness(
    engine,
    import_key,
    *,
    pin,
    audit_payload,
    staging_dir,
    backup_dir,
    workspace_dir,
    suffix,
    operating_reserve_bytes=DEFAULT_OPERATING_RESERVE_BYTES,
):
    key = validate_ecb_import_key(import_key)
    contract = get_macro_import(key)
    table_name = validate_identifier(contract["table_name"])
    candidate_path = (
        Path(staging_dir).expanduser().resolve() / pin["candidate_file_name"]
    )
    backup_path = Path(backup_dir).expanduser().resolve() / pin["backup_file_name"]
    if not candidate_path.is_file():
        raise FileNotFoundError(f"ECB candidate not found: {candidate_path}")
    audit = validate_audit_payload(key, audit_payload, candidate_path)
    candidate = {
        "file_name": candidate_path.name,
        "bytes": candidate_path.stat().st_size,
        "sha256": file_sha256(candidate_path),
    }
    verified_backup = validate_scoped_backup(backup_path, (table_name,))
    backup = {
        "file_name": Path(verified_backup["path"]).name,
        "bytes": int(verified_backup["bytes"]),
        "sha256": str(verified_backup["sha256"]).upper(),
        "structure_and_data_verified": True,
    }
    database = collect_database_state(engine, table_name)
    shadow = shadow_table_name(table_name, suffix, version=PLAN_VERSION)
    retained = retained_table_name(table_name, suffix, version=PLAN_VERSION)
    inspector = inspect(engine)
    names = {
        "shadow_table": shadow,
        "retained_table": retained,
        "shadow_exists": bool(inspector.has_table(shadow)),
        "retained_exists": bool(inspector.has_table(retained)),
    }
    capacity = estimate_capacity(
        database,
        source_rows=audit["source_rows"],
        comparison_store_bytes=audit["comparison_store_bytes"],
        workspace_dir=workspace_dir,
        operating_reserve_bytes=operating_reserve_bytes,
    )
    blockers = readiness_blockers(
        pin,
        audit,
        candidate,
        backup,
        database,
        capacity,
        names,
    )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_version": PLAN_VERSION,
        "import_key": key,
        "active_table": table_name,
        "candidate": candidate,
        "backup": backup,
        "audit": audit,
        "active_checkpoint": database,
        "planned_names": names,
        "capacity": capacity,
        "shadow_schema_sql_preview": list(
            build_shadow_schema_statements(
                engine,
                key,
                suffix,
                version=PLAN_VERSION,
            )
        ),
        "atomic_swap_sql_preview": build_swap_statement(
            (key,), suffix, version=PLAN_VERSION
        ),
        "rollback_sql_preview": build_rollback_statement(
            (key,), suffix, version=PLAN_VERSION
        ),
        "retention_policy": "official_snapshot_authoritative",
        "active_only_key_policy": (
            "Omit from the new active snapshot and preserve in the retained table."
        ),
        "build_confirmation": build_confirmation(key),
        "swap_confirmation": swap_confirmation(key),
        "blockers": list(blockers),
        "ready_for_shadow_build_authorization": not blockers,
        "database_write_performed": False,
        "active_csv_write_performed": False,
        "statements_executed": False,
    }
