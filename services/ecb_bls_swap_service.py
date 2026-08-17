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
    mapped_source_columns,
    swap_validated_shadows,
    validate_scoped_backup,
)
from services.euro_streaming_validation_service import (
    audit_euro_source_against_target,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


IMPORT_KEY = "EURO_BANK_LENDING_SURVEY"
SWAP_VERSION = "v081"
SWAP_BLS_CONFIRMATION = "SWAP_EURO_BANK_LENDING_SURVEY_V081_ACTIVE"


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
    """Return the table-independent parts used to verify retained data."""
    return {
        "data": checkpoint["data"],
        "schema": checkpoint["schema"],
    }


def validate_build_report(payload, readiness_plan):
    if payload.get("stage") != "shadow_hash_repair_and_validation":
        raise ValueError("BLS build report stage is not final")
    if payload.get("version") != PLAN_VERSION:
        raise ValueError("BLS build report version mismatch")
    if str(payload.get("import_key", "")).upper() != IMPORT_KEY:
        raise ValueError("BLS build report import mismatch")
    if payload.get("shadow_table") != readiness_plan["planned_names"][
        "shadow_table"
    ]:
        raise ValueError("BLS build report shadow name mismatch")
    for field in ("first_validation", "second_validation"):
        validation = payload.get(field, {})
        if validation.get("valid") is not True:
            raise ValueError(f"BLS {field} is not valid")
        if int(validation.get("shadow_rows", 0)) != int(
            readiness_plan["audit"]["source_rows"]
        ):
            raise ValueError(f"BLS {field} row count mismatch")
    if payload.get("active_table_changed") is not False:
        raise ValueError("BLS build report does not preserve the active table")
    if payload.get("shadow_ready_for_swap_review") is not True:
        raise ValueError("BLS shadow is not ready for swap review")
    if payload.get("swap_authorized") is not False:
        raise ValueError("BLS build report already authorizes a swap")
    if payload.get("swap_performed") is not False:
        raise ValueError("BLS build report already records a swap")
    if payload.get("shadow_evidence", {}).get("hash_column_present") is not True:
        raise ValueError("BLS shadow technical hash is unavailable")
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
        "primary_key": primary_key,
        "hash_column_present": HASH_COLUMN in columns,
    }
    if evidence["rows"] != int(expected_rows):
        raise RuntimeError("Promoted BLS row count differs from source")
    if evidence["unique_business_keys"] != int(expected_rows):
        raise RuntimeError("Promoted BLS business keys are not unique")
    if evidence["null_business_keys"] != 0:
        raise RuntimeError("Promoted BLS contains null business keys")
    if "CHAR" not in evidence["time_period_type"]:
        raise RuntimeError("Promoted BLS time_period type is unsafe")
    if primary_key != BUSINESS_KEY:
        raise RuntimeError("Promoted BLS primary key is incorrect")
    if evidence["hash_column_present"]:
        raise RuntimeError("Promoted BLS still contains the technical hash")
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


def swap_bls_active(
    engine,
    *,
    confirmation,
    readiness_payload,
    build_payload,
    staging_dir,
    backup_dir,
    workspace_dir,
    chunk_size=25_000,
):
    if confirmation != SWAP_BLS_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {SWAP_BLS_CONFIRMATION}"
        )
    suffix, readiness_plan = validate_readiness_report(
        readiness_payload,
        IMPORT_KEY,
    )
    validate_build_report(build_payload, readiness_plan)
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
        "BLS candidate",
    )
    backup_file = _validate_pinned_file(
        backup_path,
        readiness_plan["backup"],
        "BLS backup",
    )
    contract = get_macro_import(IMPORT_KEY)
    active_table = validate_identifier(contract["table_name"])
    backup = validate_scoped_backup(backup_path, (active_table,))
    if backup["sha256"] != backup_file["sha256"]:
        raise ValueError("BLS scoped backup verification changed")

    active_before = active_table_checkpoint(engine, IMPORT_KEY)
    if canonical_evidence(active_before) != canonical_evidence(
        build_payload["active_after"]
    ):
        raise ValueError("Active BLS checkpoint changed after shadow validation")
    shadow_table = readiness_plan["planned_names"]["shadow_table"]
    shadow_before = shadow_table_evidence(engine, shadow_table)
    if canonical_evidence(shadow_before) != canonical_evidence(
        build_payload["shadow_evidence"]
    ):
        raise ValueError("BLS shadow schema changed after validation")
    expected_rows = int(readiness_plan["audit"]["source_rows"])
    expected_retained = checkpoint_content(active_before)
    callback_evidence = {}

    def validate_promoted_state(*, engine, validations, retained_tables):
        validation = validations[0]
        if not validation.valid or validation.shadow_rows != expected_rows:
            raise RuntimeError("BLS shadow lost validation before swap")
        retained = retained_tables[0]
        retained_checkpoint = table_checkpoint(engine, retained)
        if canonical_evidence(retained_checkpoint) != canonical_evidence(
            expected_retained
        ):
            raise RuntimeError("Retained BLS differs from pre-swap active")
        promoted = shadow_table_evidence(engine, active_table)
        if promoted != shadow_before:
            raise RuntimeError("Promoted BLS differs from validated shadow schema")
        callback_evidence["retained_checkpoint"] = retained_checkpoint
        callback_evidence["promoted_with_hash"] = promoted

    def validate_final_state(*, engine, validations, retained_tables):
        retained = retained_tables[0]
        retained_checkpoint = table_checkpoint(engine, retained)
        if canonical_evidence(retained_checkpoint) != canonical_evidence(
            expected_retained
        ):
            raise RuntimeError("Retained BLS changed after promotion")
        audit = audit_euro_source_against_target(
            engine,
            IMPORT_KEY,
            chunk_size=chunk_size,
            workspace_dir=workspace_dir,
            sample_strategy="hash",
            source_path=source_path,
        )
        if not audit.valid:
            raise RuntimeError("Promoted BLS differs from official source")
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
        "source": source,
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
