from __future__ import annotations

from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.euro_backup_restore_service import (
    table_fingerprint,
    table_schema_signature,
)
from services.euro_direct_debits_diagnostic_service import IMPORT_KEY
from services.euro_direct_debits_shadow_service import (
    EXPECTED_FREQUENCY_ROWS,
    EXPECTED_SOURCE_ROWS,
    SHADOW_VERSION,
    shadow_table_evidence,
    validate_active_table_checkpoint,
    validate_direct_debits_backup,
    validate_direct_debits_source,
)
from services.euro_rebuild_service import (
    BUSINESS_KEY,
    HASH_COLUMN,
    SWAP_CONFIRMATION,
    mapped_source_columns,
    swap_validated_shadows,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


SWAP_VERSION = "v070"
SWAP_DIRECT_DEBITS_CONFIRMATION = "SWAP_EURO_DIRECT_DEBITS_V070_ACTIVE"


def table_checkpoint(engine, table_name):
    contract = get_macro_import(IMPORT_KEY)
    columns = mapped_source_columns(contract)
    table_name = validate_identifier(table_name)
    return {
        "data": table_fingerprint(engine, table_name, columns),
        "schema": table_schema_signature(engine, table_name),
    }


def final_active_evidence(engine, table_name):
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
                f"SUM(key_code IS NULL OR time_period IS NULL) AS null_keys "
                f"FROM `{table_name}`"
            )
        ).mappings().one()
        frequencies = connection.execute(
            text(
                f"SELECT freq, COUNT(*) AS rows_count "
                f"FROM `{table_name}` GROUP BY freq ORDER BY freq"
            )
        ).mappings()
        frequency_rows = {
            str(row["freq"]): int(row["rows_count"] or 0)
            for row in frequencies
        }
    evidence = {
        "rows": int(summary["rows_count"] or 0),
        "unique_business_keys": int(summary["unique_keys"] or 0),
        "null_business_keys": int(summary["null_keys"] or 0),
        "column_count": len(columns),
        "time_period_type": columns.get("time_period"),
        "primary_key": primary_key,
        "hash_column_present": HASH_COLUMN in columns,
        "frequency_rows": frequency_rows,
    }
    if evidence["rows"] != EXPECTED_SOURCE_ROWS:
        raise RuntimeError("Promoted Direct Debits row count differs from source")
    if evidence["unique_business_keys"] != EXPECTED_SOURCE_ROWS:
        raise RuntimeError("Promoted Direct Debits business keys are not unique")
    if evidence["null_business_keys"] != 0:
        raise RuntimeError("Promoted Direct Debits contains null business keys")
    if evidence["time_period_type"] != "VARCHAR(20)":
        raise RuntimeError("Promoted Direct Debits time_period is not VARCHAR(20)")
    if primary_key != BUSINESS_KEY:
        raise RuntimeError("Promoted Direct Debits primary key is incorrect")
    if evidence["hash_column_present"]:
        raise RuntimeError("Promoted Direct Debits still contains the hash column")
    if frequency_rows != EXPECTED_FREQUENCY_ROWS:
        raise RuntimeError("Promoted Direct Debits frequency counts differ")
    return evidence


def swap_direct_debits_active(
    engine,
    backup_file,
    confirmation,
    suffix,
    *,
    chunk_size=25_000,
    workspace_dir=None,
):
    if confirmation != SWAP_DIRECT_DEBITS_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {SWAP_DIRECT_DEBITS_CONFIRMATION}"
        )

    validate_identifier(f"suffix_{suffix}")
    backup = validate_direct_debits_backup(backup_file)
    source = validate_direct_debits_source()
    active_before = validate_active_table_checkpoint(engine)
    contract = get_macro_import(IMPORT_KEY)
    active_table = validate_identifier(contract["table_name"])
    callback_evidence = {}

    def validate_promoted_state(*, engine, validations, retained_tables):
        validation = validations[0]
        if not validation.valid or validation.shadow_rows != EXPECTED_SOURCE_ROWS:
            raise RuntimeError("Direct Debits shadow lost validation before swap")
        retained_table = retained_tables[0]
        retained_checkpoint = table_checkpoint(engine, retained_table)
        if retained_checkpoint != active_before:
            raise RuntimeError("Retained Direct Debits table differs from pre-swap active")
        callback_evidence["retained_checkpoint"] = retained_checkpoint
        callback_evidence["promoted_with_hash"] = shadow_table_evidence(
            engine,
            active_table,
        )

    def validate_final_state(*, engine, validations, retained_tables):
        retained_table = retained_tables[0]
        retained_checkpoint = table_checkpoint(engine, retained_table)
        if retained_checkpoint != active_before:
            raise RuntimeError("Retained Direct Debits checkpoint changed after swap")
        callback_evidence["retained_after"] = retained_checkpoint
        callback_evidence["active_after"] = table_checkpoint(
            engine,
            active_table,
        )
        callback_evidence["final_active"] = final_active_evidence(
            engine,
            active_table,
        )

    result = swap_validated_shadows(
        engine=engine,
        backup_file=backup["path"],
        confirmation=SWAP_CONFIRMATION,
        suffix=suffix,
        chunk_size=chunk_size,
        import_keys=(IMPORT_KEY,),
        version=SHADOW_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
        drop_hash_before_swap=False,
        post_swap_validator=validate_promoted_state,
        post_hash_drop_validator=validate_final_state,
    )
    retained_table = result["retained_tables"][0]

    return {
        **result,
        "version": SWAP_VERSION,
        "shadow_version": SHADOW_VERSION,
        "import_key": IMPORT_KEY,
        "source": source,
        "active_before": active_before,
        "active_after": callback_evidence["active_after"],
        "retained_table": retained_table,
        "retained_checkpoint": callback_evidence["retained_after"],
        "promoted_with_hash_evidence": callback_evidence[
            "promoted_with_hash"
        ],
        "final_active_evidence": callback_evidence["final_active"],
        "active_table_changed": True,
        "swap_authorized": True,
        "swap_performed": True,
        "rollback_performed": False,
    }
