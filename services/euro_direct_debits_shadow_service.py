from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from sqlalchemy import inspect, text

from macro_import_manifest import get_macro_import
from services.euro_backup_restore_service import (
    table_fingerprint,
    table_schema_signature,
)
from services.euro_direct_debits_diagnostic_service import IMPORT_KEY
from services.euro_rebuild_service import (
    BUILD_CONFIRMATION,
    BUSINESS_KEY,
    HASH_COLUMN,
    build_and_validate_shadows,
    mapped_source_columns,
    shadow_table_name,
    validate_scoped_backup,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


SHADOW_VERSION = "v069"
BUILD_DIRECT_DEBITS_CONFIRMATION = (
    "BUILD_EURO_DIRECT_DEBITS_V069_SHADOW"
)
VERIFIED_BACKUP_BYTES = 25_308_899
VERIFIED_BACKUP_SHA256 = (
    "724F9B20F7A7A651395FDBC689D99E23B324F96329EC6E629BC60F616682852E"
)
VERIFIED_SOURCE_BYTES = 32_010_024
VERIFIED_SOURCE_SHA256 = (
    "D8B5273ED4184E0733A0F2C629263F2077187A0BD75C85BAB7856E9C8E5FDB6B"
)
EXPECTED_SOURCE_ROWS = 121_564
EXPECTED_FREQUENCY_ROWS = {"A": 44_539, "H": 42_039, "Q": 34_986}
VERIFIED_ACTIVE_ROWS = 75_647
VERIFIED_ACTIVE_DATA_SHA256 = (
    "5BDAB01AFCF91D83161657736E94A0853B280FC946168008571233657EDD2907"
)
VERIFIED_ACTIVE_SCHEMA_SHA256 = (
    "6E6237FA71CBAF7603782A694107C0B9352D843E13B0258F6F42A32DBEB0F768"
)


def _file_signature(path):
    path = Path(path).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Non-empty file required: {path}")
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return {
        "path": path,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest().upper(),
    }


def validate_direct_debits_backup(backup_file):
    table_name = get_macro_import(IMPORT_KEY)["table_name"]
    backup = validate_scoped_backup(backup_file, (table_name,))
    if backup["bytes"] != VERIFIED_BACKUP_BYTES:
        raise ValueError("Direct Debits backup size differs from v0.6.8 evidence")
    if backup["sha256"] != VERIFIED_BACKUP_SHA256:
        raise ValueError("Direct Debits backup SHA-256 differs from v0.6.8 evidence")
    return backup


def validate_direct_debits_source():
    contract = get_macro_import(IMPORT_KEY)
    source = _file_signature(contract["csv_path"])
    if source["bytes"] != VERIFIED_SOURCE_BYTES:
        raise ValueError("Direct Debits source size differs from the reviewed CSV")
    if source["sha256"] != VERIFIED_SOURCE_SHA256:
        raise ValueError("Direct Debits source SHA-256 differs from the reviewed CSV")
    return source


def active_table_checkpoint(engine):
    contract = get_macro_import(IMPORT_KEY)
    table_name = validate_identifier(contract["table_name"])
    columns = mapped_source_columns(contract)
    return {
        "data": table_fingerprint(engine, table_name, columns),
        "schema": table_schema_signature(engine, table_name),
    }


def validate_active_table_checkpoint(engine):
    checkpoint = active_table_checkpoint(engine)
    data = checkpoint["data"]
    schema = checkpoint["schema"]
    if data["rows"] != VERIFIED_ACTIVE_ROWS:
        raise ValueError("Active Direct Debits row count changed after backup")
    if data["sha256"] != VERIFIED_ACTIVE_DATA_SHA256:
        raise ValueError("Active Direct Debits data changed after backup")
    if schema["sha256"] != VERIFIED_ACTIVE_SCHEMA_SHA256:
        raise ValueError("Active Direct Debits schema changed after backup")
    return checkpoint


def shadow_table_evidence(engine, shadow_table):
    shadow_table = validate_identifier(shadow_table)
    inspector = inspect(engine)
    columns = {
        normalize_column_name(column["name"]): str(column["type"]).upper()
        for column in inspector.get_columns(shadow_table)
    }
    primary_key = tuple(
        normalize_column_name(column)
        for column in inspector.get_pk_constraint(shadow_table).get(
            "constrained_columns", ()
        )
    )
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"SELECT freq, COUNT(*) AS rows_count "
                f"FROM `{shadow_table}` GROUP BY freq ORDER BY freq"
            )
        ).mappings()
        frequency_rows = {
            str(row["freq"]): int(row["rows_count"] or 0)
            for row in rows
        }
    evidence = {
        "column_count": len(columns),
        "time_period_type": columns.get("time_period"),
        "primary_key": primary_key,
        "hash_column_present": HASH_COLUMN in columns,
        "frequency_rows": frequency_rows,
    }
    if evidence["time_period_type"] != "VARCHAR(20)":
        raise RuntimeError("Direct Debits shadow time_period is not VARCHAR(20)")
    if primary_key != BUSINESS_KEY:
        raise RuntimeError("Direct Debits shadow business key is not the primary key")
    if not evidence["hash_column_present"]:
        raise RuntimeError("Direct Debits shadow source hash column is missing")
    if frequency_rows != EXPECTED_FREQUENCY_ROWS:
        raise RuntimeError("Direct Debits shadow frequency counts differ from source")
    return evidence


def build_direct_debits_shadow(
    engine,
    backup_file,
    confirmation,
    suffix,
    *,
    chunk_size=25_000,
    insert_batch_size=250,
    workspace_dir=None,
):
    if confirmation != BUILD_DIRECT_DEBITS_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {BUILD_DIRECT_DEBITS_CONFIRMATION}"
        )

    validate_identifier(f"suffix_{suffix}")
    backup = validate_direct_debits_backup(backup_file)
    source = validate_direct_debits_source()
    active_before = validate_active_table_checkpoint(engine)
    contract = get_macro_import(IMPORT_KEY)
    expected_shadow = shadow_table_name(
        contract["table_name"],
        suffix,
        version=SHADOW_VERSION,
    )

    result = build_and_validate_shadows(
        engine=engine,
        backup_file=backup["path"],
        confirmation=BUILD_CONFIRMATION,
        suffix=suffix,
        chunk_size=chunk_size,
        insert_batch_size=insert_batch_size,
        import_keys=(IMPORT_KEY,),
        version=SHADOW_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
    )
    validation = result["validations"][0]
    if validation.shadow_table != expected_shadow:
        raise RuntimeError("Unexpected Direct Debits shadow table name")
    if not validation.valid or validation.shadow_rows != EXPECTED_SOURCE_ROWS:
        raise RuntimeError("Direct Debits shadow does not match the reviewed source")

    evidence = shadow_table_evidence(engine, validation.shadow_table)
    active_after = validate_active_table_checkpoint(engine)
    if active_after != active_before:
        raise RuntimeError("Active Direct Debits table changed during shadow build")

    return {
        **result,
        "version": SHADOW_VERSION,
        "import_key": IMPORT_KEY,
        "source": source,
        "active_before": active_before,
        "active_after": active_after,
        "active_table_changed": False,
        "active_tables_changed": False,
        "shadow_table": validation.shadow_table,
        "shadow_evidence": evidence,
        "shadow_ready_for_swap_review": True,
        "swap_authorized": False,
        "swap_performed": False,
    }
