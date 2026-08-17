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
from services.euro_backup_restore_service import (
    table_fingerprint,
    table_schema_signature,
)
from services.euro_rebuild_service import (
    BUSINESS_KEY,
    HASH_COLUMN,
    SWAP_CONFIRMATION,
    failed_table_name,
    mapped_source_columns,
    retained_table_name,
    swap_validated_shadows,
    validate_scoped_backup,
    validate_existing_shadows,
)
from services.euro_streaming_validation_service import (
    audit_euro_source_against_target,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


IMPORT_KEY = "EURO_BALANCE_SHEET_ITEMS"
SWAP_VERSION = "v086"
VERIFICATION_VERSION = "v084"
SWAP_BSI_CONFIRMATION = "SWAP_EURO_BALANCE_SHEET_ITEMS_V086_ACTIVE"


def canonical_evidence(value):
    """Normalize JSON arrays and runtime tuples before evidence comparison."""
    if isinstance(value, dict):
        return {
            key: canonical_evidence(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [canonical_evidence(item) for item in value]
    return value


def checkpoint_content(checkpoint):
    """Return the table-independent evidence used for the retained table."""
    return {
        "data": checkpoint["data"],
        "schema": checkpoint["schema"],
    }


def _assert_equal(recorded, current, message):
    if canonical_evidence(recorded) != canonical_evidence(current):
        raise ValueError(message)


def _validate_complete_validation(validation, expected_rows, label):
    if validation.get("valid") is not True:
        raise ValueError(f"BSI {label} is not valid")
    exact_counts = (
        "source_rows",
        "shadow_rows",
        "source_unique_business_keys",
        "shadow_unique_business_keys",
    )
    for field in exact_counts:
        if int(validation.get(field, -1)) != expected_rows:
            raise ValueError(f"BSI {label} {field} mismatch")
    zero_counts = (
        "null_business_keys",
        "duplicate_business_key_groups",
        "row_hash_mismatches",
        "source_hash_mismatches",
        "missing_source_rows",
    )
    for field in zero_counts:
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
    if str(payload.get("import_key", "")).upper() != IMPORT_KEY:
        raise ValueError("BSI build report import mismatch")
    if payload.get("readiness_report_file") != readiness_report_file:
        raise ValueError("BSI build readiness-report file mismatch")
    if payload.get("readiness_report_sha256") != readiness_report_sha256:
        raise ValueError("BSI build readiness-report SHA-256 mismatch")
    if payload.get("suffix") != readiness_plan.get("suffix"):
        raise ValueError("BSI build report suffix mismatch")
    planned_shadow = readiness_plan["planned_names"]["shadow_table"]
    if payload.get("shadow_table") != planned_shadow:
        raise ValueError("BSI build report shadow name mismatch")
    expected_rows = int(readiness_plan["audit"]["source_rows"])
    for field in ("initial_validation", "repeated_validation"):
        _validate_complete_validation(payload.get(field, {}), expected_rows, field)
    if payload.get("database_write_scope") != "versioned_shadow_table_only":
        raise ValueError("BSI build report write scope mismatch")
    if payload.get("database_write_performed") is not True:
        raise ValueError("BSI build report does not record its shadow write")
    if payload.get("active_table_changed") is not False:
        raise ValueError("BSI build report does not preserve the active table")
    if payload.get("active_tables_changed") is not False:
        raise ValueError("BSI build report records active-table changes")
    if payload.get("active_csv_write_performed") is not False:
        raise ValueError("BSI build report must preserve the active CSV")
    if payload.get("shadow_ready_for_swap_review") is not True:
        raise ValueError("BSI shadow is not ready for swap review")
    if payload.get("swap_authorized") is not False:
        raise ValueError("BSI build report already authorizes a swap")
    if payload.get("swap_performed") is not False:
        raise ValueError("BSI build report already records a swap")
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


def validate_post_build_report(
    payload,
    build_payload,
    readiness_plan,
    *,
    build_report_file,
    build_report_sha256,
):
    if payload.get("stage") != "post_build_verification":
        raise ValueError("BSI post-build verification stage mismatch")
    if payload.get("version") != VERIFICATION_VERSION:
        raise ValueError("BSI post-build verification version mismatch")
    if payload.get("shadow_version") != PLAN_VERSION:
        raise ValueError("BSI post-build shadow version mismatch")
    if str(payload.get("import_key", "")).upper() != IMPORT_KEY:
        raise ValueError("BSI post-build verification import mismatch")
    if payload.get("source_build_report_file") != build_report_file:
        raise ValueError("BSI post-build build-report file mismatch")
    if payload.get("source_build_report_sha256") != build_report_sha256:
        raise ValueError("BSI post-build build-report SHA-256 mismatch")
    if payload.get("suffix") != readiness_plan.get("suffix"):
        raise ValueError("BSI post-build suffix mismatch")
    if payload.get("database_write_performed") is not False:
        raise ValueError("BSI post-build report must be read-only")
    if payload.get("active_csv_write_performed") is not False:
        raise ValueError("BSI post-build report must preserve the active CSV")
    if payload.get("active_unchanged") is not True:
        raise ValueError("BSI post-build report does not preserve the active table")
    if payload.get("active_table_changed") is not False:
        raise ValueError("BSI post-build report records an active-table change")
    if payload.get("shadow_ready_for_review") is not True:
        raise ValueError("BSI post-build report does not approve shadow review")
    if payload.get("swap_authorized") is not False:
        raise ValueError("BSI post-build report already authorizes a swap")
    if payload.get("swap_performed") is not False:
        raise ValueError("BSI post-build report already records a swap")

    active_table = readiness_plan["active_table"]
    shadow_table = readiness_plan["planned_names"]["shadow_table"]
    expected_rows = int(readiness_plan["audit"]["source_rows"])
    if payload.get("active_table") != active_table:
        raise ValueError("BSI post-build active table mismatch")
    if payload.get("shadow_table") != shadow_table:
        raise ValueError("BSI post-build shadow table mismatch")
    _assert_equal(
        payload.get("source"),
        readiness_plan.get("candidate"),
        "BSI post-build source differs from readiness",
    )
    _assert_equal(
        payload.get("backup"),
        readiness_plan.get("backup"),
        "BSI post-build backup differs from readiness",
    )
    _assert_equal(
        payload.get("active_checkpoint"),
        build_payload.get("active_after"),
        "BSI post-build active checkpoint mismatch",
    )
    _assert_equal(
        payload.get("shadow_evidence"),
        build_payload.get("shadow_evidence"),
        "BSI post-build shadow evidence mismatch",
    )
    summary = payload.get("shadow_summary", {})
    if int(summary.get("rows", -1)) != expected_rows:
        raise ValueError("BSI post-build shadow row count mismatch")
    if int(summary.get("unique_business_keys", -1)) != expected_rows:
        raise ValueError("BSI post-build shadow unique-key count mismatch")
    if int(summary.get("null_business_keys", -1)) != 0:
        raise ValueError("BSI post-build shadow contains null keys")
    _validate_complete_validation(
        payload.get("independent_validation", {}),
        expected_rows,
        "independent_validation",
    )
    return payload


def table_checkpoint(engine, table_name):
    contract = get_macro_import(IMPORT_KEY)
    columns = mapped_source_columns(contract)
    table_name = validate_identifier(table_name)
    return {
        "data": table_fingerprint(engine, table_name, columns),
        "schema": table_schema_signature(engine, table_name),
    }


def final_active_evidence(engine, table_name, expected_rows):
    table_name = validate_identifier(table_name)
    inspector = inspect(engine)
    columns = {
        normalize_column_name(column["name"]): str(column["type"]).upper()
        for column in inspector.get_columns(table_name)
    }
    primary_key = tuple(
        normalize_column_name(column)
        for column in inspector.get_pk_constraint(table_name).get(
            "constrained_columns", ()
        )
    )
    with engine.connect() as connection:
        summary = connection.execute(
            text(
                f"SELECT COUNT(*) AS rows_count, "
                f"COUNT(DISTINCT key_code, time_period) AS unique_keys, "
                f"SUM(key_code IS NULL OR time_period IS NULL) AS null_keys, "
                f"MIN(time_period) AS first_period, "
                f"MAX(time_period) AS last_period "
                f"FROM `{table_name}`"
            )
        ).mappings().one()
    evidence = {
        "rows": int(summary["rows_count"] or 0),
        "unique_business_keys": int(summary["unique_keys"] or 0),
        "null_business_keys": int(summary["null_keys"] or 0),
        "first_period": summary["first_period"],
        "last_period": summary["last_period"],
        "column_count": len(columns),
        "time_period_type": columns.get("time_period"),
        "obs_value_type": columns.get("obs_value"),
        "primary_key": primary_key,
        "hash_column_present": HASH_COLUMN in columns,
    }
    if evidence["rows"] != int(expected_rows):
        raise RuntimeError("Promoted BSI row count differs from source")
    if evidence["unique_business_keys"] != int(expected_rows):
        raise RuntimeError("Promoted BSI business keys are not unique")
    if evidence["null_business_keys"] != 0:
        raise RuntimeError("Promoted BSI contains null business keys")
    if "CHAR" not in evidence["time_period_type"]:
        raise RuntimeError("Promoted BSI time_period type is unsafe")
    if "DECIMAL" not in evidence["obs_value_type"]:
        raise RuntimeError("Promoted BSI obs_value type is not exact decimal")
    if primary_key != BUSINESS_KEY:
        raise RuntimeError("Promoted BSI primary key is incorrect")
    if evidence["hash_column_present"]:
        raise RuntimeError("Promoted BSI still contains the technical hash")
    return evidence


def _validate_pinned_file(path, evidence, label):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    actual = {
        "file_name": path.name,
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }
    for field in ("file_name", "bytes", "sha256"):
        if actual[field] != evidence[field]:
            raise ValueError(f"{label} {field} changed")
    return actual


def _validated_swap_context(
    engine,
    *,
    readiness_payload,
    build_payload,
    post_build_payload,
    readiness_report_file,
    readiness_report_sha256,
    build_report_file,
    build_report_sha256,
    staging_dir,
    backup_dir,
):
    suffix, readiness_plan = validate_readiness_report(
        readiness_payload,
        IMPORT_KEY,
    )
    readiness_plan = {**readiness_plan, "suffix": suffix}
    if build_payload.get("suffix") != suffix:
        raise ValueError("BSI build report suffix mismatch")
    validate_build_report(
        build_payload,
        readiness_plan,
        readiness_report_file=readiness_report_file,
        readiness_report_sha256=readiness_report_sha256,
    )
    validate_post_build_report(
        post_build_payload,
        build_payload,
        readiness_plan,
        build_report_file=build_report_file,
        build_report_sha256=build_report_sha256,
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
    backup_file = _validate_pinned_file(
        backup_path,
        readiness_plan["backup"],
        "BSI backup",
    )
    contract = get_macro_import(IMPORT_KEY)
    active_table = validate_identifier(contract["table_name"])
    backup = validate_scoped_backup(backup_path, (active_table,))
    if backup["sha256"] != backup_file["sha256"]:
        raise ValueError("BSI scoped backup verification changed")

    active_before = active_table_checkpoint(engine, IMPORT_KEY)
    _assert_equal(
        active_before,
        post_build_payload["active_checkpoint"],
        "Active BSI checkpoint changed after shadow validation",
    )
    shadow_table = readiness_plan["planned_names"]["shadow_table"]
    shadow_before = shadow_table_evidence(engine, shadow_table)
    _assert_equal(
        shadow_before,
        post_build_payload["shadow_evidence"],
        "BSI shadow schema changed after validation",
    )
    return {
        "suffix": suffix,
        "readiness_plan": readiness_plan,
        "source_path": source_path,
        "backup_path": backup_path,
        "source": source,
        "backup": backup,
        "active_table": active_table,
        "active_before": active_before,
        "shadow_table": shadow_table,
        "shadow_before": shadow_before,
        "expected_rows": int(readiness_plan["audit"]["source_rows"]),
        "expected_retained": checkpoint_content(active_before),
        "expected_retained_name": readiness_plan["planned_names"][
            "retained_table"
        ],
    }


def preflight_bsi_swap(
    engine,
    *,
    readiness_payload,
    build_payload,
    post_build_payload,
    readiness_report_file,
    readiness_report_sha256,
    build_report_file,
    build_report_sha256,
    staging_dir,
    backup_dir,
    workspace_dir,
    chunk_size=25_000,
):
    context = _validated_swap_context(
        engine,
        readiness_payload=readiness_payload,
        build_payload=build_payload,
        post_build_payload=post_build_payload,
        readiness_report_file=readiness_report_file,
        readiness_report_sha256=readiness_report_sha256,
        build_report_file=build_report_file,
        build_report_sha256=build_report_sha256,
        staging_dir=staging_dir,
        backup_dir=backup_dir,
    )
    validation = validate_existing_shadows(
        engine,
        context["suffix"],
        chunk_size,
        (IMPORT_KEY,),
        version=PLAN_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
        source_path_overrides={IMPORT_KEY: context["source_path"]},
    )[0]
    if not validation.valid:
        raise RuntimeError("BSI shadow failed the preflight source validation")
    if validation.shadow_rows != context["expected_rows"]:
        raise RuntimeError("BSI preflight shadow row count differs from source")

    retained = retained_table_name(
        context["active_table"],
        context["suffix"],
        version=PLAN_VERSION,
    )
    failed = failed_table_name(
        context["active_table"],
        context["suffix"],
        version=PLAN_VERSION,
    )
    if retained != context["expected_retained_name"]:
        raise RuntimeError("BSI retained name differs from readiness plan")
    current_tables = set(inspect(engine).get_table_names())
    if context["active_table"] not in current_tables:
        raise RuntimeError("BSI active table is unavailable")
    if context["shadow_table"] not in current_tables:
        raise RuntimeError("BSI shadow table is unavailable")
    if retained in current_tables:
        raise RuntimeError("BSI retained table name already exists")
    if failed in current_tables:
        raise RuntimeError("BSI failed-table name already exists")

    return {
        "version": SWAP_VERSION,
        "shadow_version": PLAN_VERSION,
        "stage": "swap_preflight",
        "import_key": IMPORT_KEY,
        "suffix": context["suffix"],
        "source": context["source"],
        "backup": context["backup"],
        "active_table": context["active_table"],
        "active_checkpoint": context["active_before"],
        "shadow_table": context["shadow_table"],
        "shadow_evidence": context["shadow_before"],
        "shadow_validation": validation.to_dict(),
        "retained_table": retained,
        "failed_table": failed,
        "database_write_performed": False,
        "active_table_changed": False,
        "active_csv_write_performed": False,
        "swap_authorized": False,
        "swap_performed": False,
        "ready_for_swap_authorization": True,
    }


def swap_bsi_active(
    engine,
    *,
    confirmation,
    readiness_payload,
    build_payload,
    post_build_payload,
    readiness_report_file,
    readiness_report_sha256,
    build_report_file,
    build_report_sha256,
    staging_dir,
    backup_dir,
    workspace_dir,
    chunk_size=25_000,
):
    if confirmation != SWAP_BSI_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {SWAP_BSI_CONFIRMATION}"
        )
    context = _validated_swap_context(
        engine,
        readiness_payload=readiness_payload,
        build_payload=build_payload,
        post_build_payload=post_build_payload,
        readiness_report_file=readiness_report_file,
        readiness_report_sha256=readiness_report_sha256,
        build_report_file=build_report_file,
        build_report_sha256=build_report_sha256,
        staging_dir=staging_dir,
        backup_dir=backup_dir,
    )
    suffix = context["suffix"]
    source_path = context["source_path"]
    backup_path = context["backup_path"]
    active_table = context["active_table"]
    active_before = context["active_before"]
    shadow_before = context["shadow_before"]
    expected_rows = context["expected_rows"]
    expected_retained = context["expected_retained"]
    expected_retained_name = context["expected_retained_name"]
    callback_evidence = {}

    def validate_promoted_state(*, engine, validations, retained_tables):
        validation = validations[0]
        if not validation.valid or validation.shadow_rows != expected_rows:
            raise RuntimeError("BSI shadow lost validation before swap")
        retained = retained_tables[0]
        if retained != expected_retained_name:
            raise RuntimeError("Retained BSI name differs from readiness plan")
        retained_checkpoint = table_checkpoint(engine, retained)
        _assert_equal(
            retained_checkpoint,
            expected_retained,
            "Retained BSI differs from pre-swap active",
        )
        promoted = shadow_table_evidence(engine, active_table)
        _assert_equal(
            promoted,
            shadow_before,
            "Promoted BSI differs from validated shadow schema",
        )
        callback_evidence["retained_checkpoint"] = retained_checkpoint
        callback_evidence["promoted_with_hash"] = promoted

    def validate_final_state(*, engine, validations, retained_tables):
        retained = retained_tables[0]
        retained_checkpoint = table_checkpoint(engine, retained)
        _assert_equal(
            retained_checkpoint,
            expected_retained,
            "Retained BSI changed after promotion",
        )
        audit = audit_euro_source_against_target(
            engine,
            IMPORT_KEY,
            chunk_size=chunk_size,
            workspace_dir=workspace_dir,
            sample_strategy="hash",
            source_path=source_path,
        )
        if not audit.valid:
            raise RuntimeError("Promoted BSI differs from official source")
        active_after = active_table_checkpoint(engine, IMPORT_KEY)
        callback_evidence["retained_after"] = retained_checkpoint
        callback_evidence["active_after"] = active_after
        callback_evidence["source_to_active_audit"] = audit.to_dict()
        callback_evidence["final_active"] = final_active_evidence(
            engine,
            active_table,
            expected_rows,
        )

    result = swap_validated_shadows(
        engine=engine,
        backup_file=backup_path,
        confirmation=SWAP_CONFIRMATION,
        suffix=suffix,
        chunk_size=chunk_size,
        import_keys=(IMPORT_KEY,),
        version=PLAN_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
        drop_hash_before_swap=False,
        post_swap_validator=validate_promoted_state,
        post_hash_drop_validator=validate_final_state,
        source_path_overrides={IMPORT_KEY: source_path},
    )
    return {
        **result,
        "version": SWAP_VERSION,
        "shadow_version": PLAN_VERSION,
        "import_key": IMPORT_KEY,
        "source": context["source"],
        "active_before": active_before,
        "active_after": callback_evidence["active_after"],
        "retained_table": result["retained_tables"][0],
        "retained_checkpoint": callback_evidence["retained_after"],
        "promoted_with_hash_evidence": callback_evidence[
            "promoted_with_hash"
        ],
        "source_to_active_audit": callback_evidence[
            "source_to_active_audit"
        ],
        "final_active_evidence": callback_evidence["final_active"],
        "active_table_changed": True,
        "active_csv_write_performed": False,
        "swap_authorized": True,
        "swap_performed": True,
        "rollback_performed": False,
    }
