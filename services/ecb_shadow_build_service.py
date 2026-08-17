from __future__ import annotations

from pathlib import Path

from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.ecb_shadow_readiness_service import (
    PLAN_VERSION,
    build_confirmation,
    build_ecb_shadow_readiness,
    validate_ecb_import_key,
)
from services.euro_backup_restore_service import (
    table_fingerprint,
    table_schema_signature,
)
from services.euro_rebuild_service import (
    BUILD_CONFIRMATION,
    BUSINESS_KEY,
    HASH_COLUMN,
    build_and_validate_shadows,
    canonical_row_hash,
    mapped_source_columns,
    normalize_row,
    normalize_source_frame,
    source_chunks,
    validate_existing_shadows,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


BUILDABLE_IMPORT_KEYS = ("EURO_BALANCE_SHEET_ITEMS",)


def validate_build_import_key(import_key):
    key = validate_ecb_import_key(import_key)
    if key not in BUILDABLE_IMPORT_KEYS:
        raise ValueError(f"ECB shadow build is not authorized for: {key}")
    return key


def validate_readiness_report(payload, import_key):
    key = validate_build_import_key(import_key)
    if payload.get("plan_version") != PLAN_VERSION:
        raise ValueError("ECB readiness report version mismatch")
    if payload.get("database_write_performed") is not False:
        raise ValueError("Readiness report must confirm zero database writes")
    if payload.get("active_csv_write_performed") is not False:
        raise ValueError("Readiness report must confirm zero active CSV writes")
    if payload.get("statements_executed") is not False:
        raise ValueError("Readiness report must confirm zero executed statements")
    if int(payload.get("error_count", -1)) != 0:
        raise ValueError("Readiness report contains errors")
    suffix = str(payload.get("suffix", ""))
    validate_identifier(f"suffix_{suffix}")
    matching = [
        plan
        for plan in payload.get("plans", ())
        if str(plan.get("import_key", "")).upper() == key
    ]
    if len(matching) != 1:
        raise ValueError(f"Readiness report must contain one plan for {key}")
    plan = matching[0]
    if plan.get("database_write_performed") is not False:
        raise ValueError("Readiness plan must confirm zero database writes")
    if plan.get("active_csv_write_performed") is not False:
        raise ValueError("Readiness plan must confirm zero active CSV writes")
    if plan.get("statements_executed") is not False:
        raise ValueError("Readiness plan must confirm zero executed statements")
    if plan.get("build_confirmation") != build_confirmation(key):
        raise ValueError("Readiness build confirmation mismatch")
    if plan.get("blockers"):
        raise ValueError(f"Readiness plan has blockers: {plan['blockers']}")
    if plan.get("ready_for_shadow_build_authorization") is not True:
        raise ValueError("Readiness plan is not approved for build authorization")
    names = plan.get("planned_names", {})
    if names.get("shadow_exists") or names.get("retained_exists"):
        raise ValueError("Readiness plan references an existing future table")
    return suffix, plan


def active_table_checkpoint(engine, import_key):
    key = validate_ecb_import_key(import_key)
    contract = get_macro_import(key)
    table_name = validate_identifier(contract["table_name"])
    columns = mapped_source_columns(contract)
    return {
        "table": table_name,
        "data": table_fingerprint(engine, table_name, columns),
        "schema": table_schema_signature(engine, table_name),
    }


def shadow_table_evidence(engine, table_name):
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
    return {
        "column_count": len(columns),
        "primary_key": primary_key,
        "hash_column_present": HASH_COLUMN in columns,
        "schema": table_schema_signature(engine, table_name),
    }


def compare_source_shadow_row(
    engine,
    import_key,
    shadow_table,
    source_path,
    key_code,
    time_period,
    *,
    chunk_size=25_000,
):
    key = validate_build_import_key(import_key)
    contract = get_macro_import(key)
    columns = mapped_source_columns(contract)
    expected_key = (str(key_code), str(time_period))
    source_record = None
    for raw_chunk in source_chunks(
        contract,
        chunk_size,
        source_path=source_path,
    ):
        chunk = normalize_source_frame(contract, raw_chunk, columns)
        for values in chunk.itertuples(index=False, name=None):
            record, invalid_columns = normalize_row(columns, values)
            if invalid_columns:
                continue
            row_key = tuple(record[column] for column in BUSINESS_KEY)
            if row_key == expected_key:
                source_record = record
                break
        if source_record is not None:
            break
    if source_record is None:
        raise ValueError(f"Source row not found: {expected_key}")

    shadow_table = validate_identifier(shadow_table)
    selections = ", ".join(f"`{column}`" for column in columns)
    statement = text(
        f"SELECT {selections}, `{HASH_COLUMN}` FROM `{shadow_table}` "
        "WHERE key_code = :key_code AND time_period = :time_period"
    )
    with engine.connect() as connection:
        row = connection.execute(
            statement,
            {"key_code": expected_key[0], "time_period": expected_key[1]},
        ).mappings().one()
    shadow_record, invalid_columns = normalize_row(
        columns,
        tuple(row[column] for column in columns),
    )
    if invalid_columns:
        raise RuntimeError(
            f"Invalid numeric columns in shadow row: {invalid_columns}"
        )
    differences = []
    for column in columns:
        source_hash = canonical_row_hash((column,), source_record)
        shadow_hash = canonical_row_hash((column,), shadow_record)
        if source_hash != shadow_hash:
            differences.append(
                {
                    "column": column,
                    "source_value": source_record[column],
                    "shadow_value": shadow_record[column],
                }
            )
    return {
        "import_key": key,
        "shadow_table": shadow_table,
        "key_code": expected_key[0],
        "time_period": expected_key[1],
        "stored_hash": str(row[HASH_COLUMN]).strip().upper(),
        "source_hash": canonical_row_hash(columns, source_record),
        "shadow_hash": canonical_row_hash(columns, shadow_record),
        "differences": differences,
        "database_write_performed": False,
    }


def repair_confirmation(import_key):
    key = validate_build_import_key(import_key)
    return f"REPAIR_{key}_{PLAN_VERSION.upper()}_SHADOW_HASHES"


def repair_shadow_storage_hash(
    engine,
    import_key,
    shadow_table,
    source_path,
    key_code,
    time_period,
    *,
    confirmation,
):
    key = validate_build_import_key(import_key)
    expected_confirmation = repair_confirmation(key)
    if confirmation != expected_confirmation:
        raise ValueError(
            f"--confirm must exactly match {expected_confirmation}"
        )
    diagnosis = compare_source_shadow_row(
        engine,
        key,
        shadow_table,
        source_path,
        key_code,
        time_period,
    )
    if diagnosis["differences"]:
        raise ValueError("Source and shadow values are not canonically equivalent")
    if diagnosis["source_hash"] != diagnosis["shadow_hash"]:
        raise ValueError("Source and shadow canonical hashes still differ")
    if diagnosis["stored_hash"] == diagnosis["source_hash"]:
        raise ValueError("Shadow hash is already normalized")

    shadow_table = validate_identifier(shadow_table)
    statement = text(
        f"UPDATE `{shadow_table}` SET `{HASH_COLUMN}` = :new_hash "
        "WHERE key_code = :key_code AND time_period = :time_period "
        f"AND `{HASH_COLUMN}` = :old_hash"
    )
    with engine.begin() as connection:
        result = connection.execute(
            statement,
            {
                "new_hash": diagnosis["source_hash"],
                "key_code": diagnosis["key_code"],
                "time_period": diagnosis["time_period"],
                "old_hash": diagnosis["stored_hash"],
            },
        )
        if result.rowcount != 1:
            raise RuntimeError(
                "Expected exactly one guarded shadow hash update, "
                f"received {result.rowcount}"
            )
    return {
        **diagnosis,
        "old_hash": diagnosis["stored_hash"],
        "new_hash": diagnosis["source_hash"],
        "rows_updated": 1,
        "database_write_scope": "shadow_technical_hash_only",
        "database_write_performed": True,
        "active_table_changed": False,
    }


def _assert_same_readiness(recorded, current):
    checks = (
        ("candidate", "file_name"),
        ("candidate", "bytes"),
        ("candidate", "sha256"),
        ("backup", "file_name"),
        ("backup", "bytes"),
        ("backup", "sha256"),
        ("audit", "source_rows"),
        ("audit", "target_rows"),
        ("audit", "source_unique_business_keys"),
        ("audit", "target_unique_business_keys"),
        ("audit", "source_rows_missing_from_target"),
        ("audit", "target_rows_missing_from_source"),
        ("audit", "row_hash_mismatches"),
        ("audit", "source_null_business_keys"),
        ("audit", "target_null_business_keys"),
        ("audit", "source_duplicate_business_key_groups"),
        ("audit", "target_duplicate_business_key_groups"),
        ("active_checkpoint", "target_rows"),
        ("active_checkpoint", "schema_signature", "sha256"),
        ("planned_names", "shadow_table"),
        ("planned_names", "retained_table"),
    )

    def nested_value(payload, path):
        value = payload
        for field in path:
            if not isinstance(value, dict):
                return None
            value = value.get(field)
        return value

    changed = [
        ".".join(path)
        for path in checks
        if nested_value(recorded, path) != nested_value(current, path)
    ]
    if changed:
        raise ValueError(f"ECB readiness evidence changed: {changed}")


def build_ecb_shadow(
    engine,
    import_key,
    *,
    confirmation,
    readiness_payload,
    pin,
    audit_payload,
    staging_dir,
    backup_dir,
    workspace_dir,
    chunk_size=25_000,
    insert_batch_size=500,
):
    key = validate_build_import_key(import_key)
    expected_confirmation = build_confirmation(key)
    if confirmation != expected_confirmation:
        raise ValueError(
            f"--confirm must exactly match {expected_confirmation}"
        )
    suffix, recorded_readiness = validate_readiness_report(
        readiness_payload,
        key,
    )
    current_readiness = build_ecb_shadow_readiness(
        engine,
        key,
        pin=pin,
        audit_payload=audit_payload,
        staging_dir=staging_dir,
        backup_dir=backup_dir,
        workspace_dir=workspace_dir,
        suffix=suffix,
    )
    if not current_readiness["ready_for_shadow_build_authorization"]:
        raise ValueError(
            f"Fresh ECB readiness blockers: {current_readiness['blockers']}"
        )
    _assert_same_readiness(recorded_readiness, current_readiness)

    source_path = (
        Path(staging_dir).expanduser().resolve()
        / current_readiness["candidate"]["file_name"]
    )
    backup_path = (
        Path(backup_dir).expanduser().resolve()
        / current_readiness["backup"]["file_name"]
    )
    active_before = active_table_checkpoint(engine, key)
    result = build_and_validate_shadows(
        engine=engine,
        backup_file=backup_path,
        confirmation=BUILD_CONFIRMATION,
        suffix=suffix,
        chunk_size=chunk_size,
        insert_batch_size=insert_batch_size,
        import_keys=(key,),
        version=PLAN_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
        source_path_overrides={key: source_path},
    )
    validation = result["validations"][0]
    planned_shadow = current_readiness["planned_names"]["shadow_table"]
    if validation.shadow_table != planned_shadow:
        raise RuntimeError("Built ECB shadow name differs from readiness plan")
    if not validation.valid:
        raise RuntimeError("Built ECB shadow failed complete source validation")
    if validation.shadow_rows != int(audit_payload["source_rows"]):
        raise RuntimeError("Built ECB shadow row count differs from staged source")

    repeated_validation = validate_existing_shadows(
        engine,
        suffix,
        chunk_size,
        (key,),
        version=PLAN_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
        source_path_overrides={key: source_path},
    )[0]
    if not repeated_validation.valid:
        raise RuntimeError("Independent ECB shadow revalidation failed")
    if repeated_validation.shadow_rows != validation.shadow_rows:
        raise RuntimeError("Repeated ECB shadow row count changed")

    evidence = shadow_table_evidence(engine, validation.shadow_table)
    if not evidence["hash_column_present"]:
        raise RuntimeError("ECB shadow source hash column is missing")
    active_after = active_table_checkpoint(engine, key)
    if active_after != active_before:
        raise RuntimeError("Active ECB table changed during shadow build")

    return {
        "version": PLAN_VERSION,
        "import_key": key,
        "suffix": suffix,
        "confirmation": confirmation,
        "source": current_readiness["candidate"],
        "backup": current_readiness["backup"],
        "shadow_table": validation.shadow_table,
        "shadow_evidence": evidence,
        "initial_validation": validation.to_dict(),
        "repeated_validation": repeated_validation.to_dict(),
        "active_before": active_before,
        "active_after": active_after,
        "database_write_performed": True,
        "memory_bounded_validation": bool(
            result["memory_bounded_validation"]
        ),
        "active_table_changed": False,
        "active_tables_changed": False,
        "active_csv_write_performed": False,
        "shadow_ready_for_swap_review": True,
        "swap_authorized": False,
        "swap_performed": False,
    }
