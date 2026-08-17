from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.ecb_shadow_build_service import (
    active_table_checkpoint,
    shadow_table_evidence,
    validate_readiness_report,
)
from services.ecb_shadow_readiness_service import PLAN_VERSION, file_sha256
from services.euro_rebuild_service import (
    validate_existing_shadows,
    validate_scoped_backup,
)
from services.market_data_sync_service import validate_identifier


VERIFIABLE_IMPORT_KEYS = ("EURO_BALANCE_SHEET_ITEMS",)
VERIFICATION_VERSION = "v084"


def canonical_evidence(value):
    if isinstance(value, dict):
        return {
            key: canonical_evidence(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [canonical_evidence(item) for item in value]
    return value


def _assert_equal(recorded, current, message):
    if canonical_evidence(recorded) != canonical_evidence(current):
        raise ValueError(message)


def _validate_complete_validation(validation, expected_rows, label):
    if validation.get("valid") is not True:
        raise ValueError(f"BSI {label} is not valid")
    for field in (
        "source_rows",
        "shadow_rows",
        "source_unique_business_keys",
        "shadow_unique_business_keys",
    ):
        if int(validation.get(field, -1)) != expected_rows:
            raise ValueError(f"BSI {label} {field} mismatch")
    for field in (
        "null_business_keys",
        "duplicate_business_key_groups",
        "row_hash_mismatches",
        "source_hash_mismatches",
        "missing_source_rows",
    ):
        if int(validation.get(field, -1)) != 0:
            raise ValueError(f"BSI {label} {field} is not zero")


def validate_build_report(
    payload,
    readiness_plan,
    *,
    readiness_report_file,
    readiness_report_sha256,
):
    if payload.get("stage") != "shadow_build":
        raise ValueError("BSI build report stage is not final")
    if payload.get("version") != PLAN_VERSION:
        raise ValueError("BSI build report version mismatch")
    if payload.get("import_key") != "EURO_BALANCE_SHEET_ITEMS":
        raise ValueError("BSI build report import mismatch")
    if payload.get("readiness_report_file") != readiness_report_file:
        raise ValueError("BSI build readiness-report file mismatch")
    if payload.get("readiness_report_sha256") != readiness_report_sha256:
        raise ValueError("BSI build readiness-report SHA-256 mismatch")
    if payload.get("suffix") != readiness_plan.get("suffix"):
        raise ValueError("BSI build suffix mismatch")
    if payload.get("shadow_table") != readiness_plan["planned_names"][
        "shadow_table"
    ]:
        raise ValueError("BSI build shadow name mismatch")

    expected_rows = int(readiness_plan["audit"]["source_rows"])
    for field in ("initial_validation", "repeated_validation"):
        _validate_complete_validation(payload.get(field, {}), expected_rows, field)
    for field, expected in (
        ("database_write_performed", True),
        ("active_table_changed", False),
        ("active_tables_changed", False),
        ("active_csv_write_performed", False),
        ("shadow_ready_for_swap_review", True),
        ("swap_authorized", False),
        ("swap_performed", False),
    ):
        if payload.get(field) is not expected:
            raise ValueError(f"BSI build report {field} mismatch")
    if payload.get("database_write_scope") != "versioned_shadow_table_only":
        raise ValueError("BSI build report write scope mismatch")
    if payload.get("shadow_evidence", {}).get("hash_column_present") is not True:
        raise ValueError("BSI shadow technical hash is unavailable")
    _assert_equal(
        payload.get("source"),
        readiness_plan.get("candidate"),
        "BSI build source differs from readiness",
    )
    _assert_equal(
        payload.get("backup"),
        readiness_plan.get("backup"),
        "BSI build backup differs from readiness",
    )
    _assert_equal(
        payload.get("active_before"),
        payload.get("active_after"),
        "BSI active checkpoint changed during build",
    )
    return payload


def _validate_pinned_file(path, evidence, label):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    actual = {
        "file_name": path.name,
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }
    _assert_equal(evidence, actual, f"{label} evidence changed")
    return actual


def shadow_summary(engine, table_name):
    table_name = validate_identifier(table_name)
    with engine.connect() as connection:
        row = connection.execute(
            text(
                "SELECT COUNT(*) AS rows_count, "
                "COUNT(DISTINCT key_code, time_period) AS unique_keys, "
                "SUM(key_code IS NULL OR time_period IS NULL) AS null_keys, "
                "MIN(time_period) AS first_period, "
                "MAX(time_period) AS last_period "
                f"FROM `{table_name}`"
            )
        ).mappings().one()
    return {
        "rows": int(row["rows_count"] or 0),
        "unique_business_keys": int(row["unique_keys"] or 0),
        "null_business_keys": int(row["null_keys"] or 0),
        "first_period": row["first_period"],
        "last_period": row["last_period"],
    }


def verify_ecb_shadow_build(
    engine,
    import_key,
    *,
    readiness_payload,
    build_payload,
    readiness_report_file,
    readiness_report_sha256,
    build_report_file,
    build_report_sha256,
    staging_dir,
    backup_dir,
    workspace_dir,
    chunk_size=25_000,
):
    key = str(import_key).upper()
    if key not in VERIFIABLE_IMPORT_KEYS:
        raise ValueError(f"ECB post-build verification is not enabled for {key}")
    suffix, readiness_plan = validate_readiness_report(readiness_payload, key)
    readiness_plan = {**readiness_plan, "suffix": suffix}
    validate_build_report(
        build_payload,
        readiness_plan,
        readiness_report_file=readiness_report_file,
        readiness_report_sha256=readiness_report_sha256,
    )

    source_path = (
        Path(staging_dir).expanduser().resolve()
        / readiness_plan["candidate"]["file_name"]
    )
    backup_path = (
        Path(backup_dir).expanduser().resolve()
        / readiness_plan["backup"]["file_name"]
    )
    source = _validate_pinned_file(
        source_path,
        readiness_plan["candidate"],
        "BSI candidate",
    )
    contract = get_macro_import(key)
    active_table = validate_identifier(contract["table_name"])
    scoped_backup = validate_scoped_backup(backup_path, (active_table,))
    backup = {
        "file_name": backup_path.name,
        "bytes": scoped_backup["bytes"],
        "sha256": scoped_backup["sha256"],
        "structure_and_data_verified": True,
    }
    _assert_equal(
        readiness_plan["backup"],
        backup,
        "BSI scoped backup evidence changed",
    )

    shadow_table = validate_identifier(
        readiness_plan["planned_names"]["shadow_table"]
    )
    tables = set(inspect(engine).get_table_names())
    if active_table not in tables or shadow_table not in tables:
        raise RuntimeError("BSI active or shadow table is unavailable")
    active_before = active_table_checkpoint(engine, key)
    _assert_equal(
        build_payload["active_after"],
        active_before,
        "BSI active checkpoint changed after build",
    )
    shadow_before = shadow_table_evidence(engine, shadow_table)
    _assert_equal(
        build_payload["shadow_evidence"],
        shadow_before,
        "BSI shadow schema changed after build",
    )
    summary = shadow_summary(engine, shadow_table)
    expected_rows = int(readiness_plan["audit"]["source_rows"])
    if summary["rows"] != expected_rows:
        raise RuntimeError("BSI shadow row count differs from source")
    if summary["unique_business_keys"] != expected_rows:
        raise RuntimeError("BSI shadow business keys are not unique")
    if summary["null_business_keys"] != 0:
        raise RuntimeError("BSI shadow contains null business keys")

    validation = validate_existing_shadows(
        engine,
        suffix,
        chunk_size,
        (key,),
        version=PLAN_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
        source_path_overrides={key: source_path},
    )[0]
    validation_payload = validation.to_dict()
    _validate_complete_validation(
        validation_payload,
        expected_rows,
        "independent_validation",
    )
    active_after = active_table_checkpoint(engine, key)
    _assert_equal(
        active_before,
        active_after,
        "BSI active checkpoint changed during post-build verification",
    )

    return {
        "stage": "post_build_verification",
        "version": VERIFICATION_VERSION,
        "shadow_version": PLAN_VERSION,
        "import_key": key,
        "suffix": suffix,
        "source": source,
        "backup": backup,
        "active_table": active_table,
        "active_checkpoint": active_after,
        "active_unchanged": True,
        "shadow_table": shadow_table,
        "shadow_evidence": shadow_before,
        "shadow_summary": summary,
        "independent_validation": validation_payload,
        "source_build_report_file": build_report_file,
        "source_build_report_sha256": build_report_sha256,
        "database_write_performed": False,
        "active_table_changed": False,
        "active_csv_write_performed": False,
        "shadow_ready_for_review": True,
        "swap_authorized": False,
        "swap_performed": False,
    }
