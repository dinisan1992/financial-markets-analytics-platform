from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from config import DB_CONFIG, get_sqlalchemy_database_url
from macro_import_manifest import get_macro_import
from services.euro_rebuild_service import (
    BUSINESS_KEY,
    canonical_row_hash,
    mapped_source_columns,
    normalize_row,
    validate_scoped_backup,
)
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier
from services.mysql_streaming_service import unbuffered_mysql_cursor


BACKUP_VERIFY_VERSION = "v068"
TEST_SCHEMA_PREFIX = "euro_backup_verify_v068_"
FINGERPRINT_CHUNK_SIZE = 5_000


def _euro_contract(import_key):
    import_key = str(import_key).upper()
    contract = get_macro_import(import_key)
    if contract.get("group") != "EURO":
        raise ValueError(f"Not a EURO import contract: {import_key}")
    return import_key, contract


def verification_confirmation(import_key):
    import_key, _ = _euro_contract(import_key)
    return f"VERIFY_{import_key}_BACKUP_RESTORE_{BACKUP_VERIFY_VERSION.upper()}"


def _physical_volume_id(value):
    path = Path(value).expanduser().resolve()
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    try:
        return ("device", os.stat(candidate).st_dev)
    except OSError:
        drive = path.drive.lower()
        return ("drive", drive) if drive else None


def validate_external_backup_dir(value, project_root):
    path = Path(value).expanduser().resolve()
    root = Path(project_root).expanduser().resolve()
    try:
        path.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("Backup directory must be outside the repository")
    path_volume = _physical_volume_id(path)
    root_volume = _physical_volume_id(root)
    if path_volume is not None and path_volume == root_volume:
        raise ValueError("Backup directory must use a separate physical volume")
    return path


def validate_test_schema_name(value, production_schema=None):
    schema = str(value).lower()
    production = str(production_schema or DB_CONFIG["database"]).lower()
    if not re.fullmatch(r"[a-z0-9_]{1,64}", schema):
        raise ValueError(f"Unsafe MySQL test schema name: {value}")
    if not schema.startswith(TEST_SCHEMA_PREFIX):
        raise ValueError(
            f"Test schema must start with {TEST_SCHEMA_PREFIX}: {value}"
        )
    if schema == production:
        raise ValueError("Test schema cannot be the production schema")
    return schema


def new_test_schema_name(now=None, token=None):
    timestamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S")
    suffix = token or secrets.token_hex(3)
    return validate_test_schema_name(
        f"{TEST_SCHEMA_PREFIX}{timestamp}_{suffix}"
    )


def resolve_mysql_client(explicit_path=None):
    candidates = [
        Path(explicit_path) if explicit_path else None,
        Path(r"C:\xampp\mysql\bin\mysql.exe"),
        Path(shutil.which("mysql")) if shutil.which("mysql") else None,
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError("mysql client executable was not found")


def build_mysql_restore_command(executable, schema):
    schema = validate_test_schema_name(schema)
    return [
        str(Path(executable)),
        f"--host={DB_CONFIG['host']}",
        f"--port={DB_CONFIG['port']}",
        f"--user={DB_CONFIG['user']}",
        "--default-character-set=utf8mb4",
        schema,
    ]


def restore_backup(backup_file, schema, mysql_path=None):
    path = Path(backup_file).expanduser().resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Non-empty SQL backup required: {path}")
    executable = resolve_mysql_client(mysql_path)
    command = build_mysql_restore_command(executable, schema)
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = str(DB_CONFIG["password"])
    with path.open("rb") as input_handle:
        result = subprocess.run(
            command,
            stdin=input_handle,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"mysql restore failed: {error}")


def _database_url(database):
    return make_url(get_sqlalchemy_database_url()).set(database=database)


def _schema_exists(connection, schema):
    return connection.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.schemata "
            "WHERE schema_name = :schema"
        ),
        {"schema": schema},
    ).scalar_one() == 1


def create_test_schema(admin_engine, schema):
    schema = validate_test_schema_name(schema)
    with admin_engine.connect() as connection:
        if _schema_exists(connection, schema):
            raise RuntimeError(f"Refusing to reuse existing test schema: {schema}")
        connection.execute(
            text(
                f"CREATE DATABASE `{schema}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        )


def drop_test_schema(admin_engine, schema):
    schema = validate_test_schema_name(schema)
    with admin_engine.connect() as connection:
        if _schema_exists(connection, schema):
            connection.execute(text(f"DROP DATABASE `{schema}`"))
        if _schema_exists(connection, schema):
            raise RuntimeError(f"Temporary schema cleanup failed: {schema}")


def _target_value_batches(connection, statement, chunk_size):
    chunk_size = max(1, int(chunk_size))
    dialect = connection.engine.dialect
    if dialect.name in {"mysql", "mariadb"} and dialect.driver == "mysqlconnector":
        driver_connection = connection.connection.driver_connection
        cursor = unbuffered_mysql_cursor(driver_connection)
        try:
            cursor.execute(statement.text)
            while rows := cursor.fetchmany(chunk_size):
                yield rows
        finally:
            cursor.close()
        return

    result = connection.execution_options(
        stream_results=True,
        max_row_buffer=chunk_size,
    ).execute(statement)
    try:
        while rows := result.fetchmany(chunk_size):
            yield [tuple(row) for row in rows]
    finally:
        result.close()


def table_fingerprint(engine, table_name, columns, chunk_size=FINGERPRINT_CHUNK_SIZE):
    table_name = validate_identifier(table_name)
    columns = tuple(validate_identifier(column) for column in columns)
    inspector = inspect(engine)
    actual_columns = {
        normalize_column_name(column["name"]): column["name"]
        for column in inspector.get_columns(table_name)
    }
    missing = sorted(set(columns) - set(actual_columns))
    if missing:
        raise ValueError(f"Backup fingerprint columns are missing: {missing}")

    selections = ", ".join(
        f"`{validate_identifier(actual_columns[column])}` AS `{column}`"
        for column in columns
    )
    order_columns = tuple(column for column in BUSINESS_KEY if column in columns)
    order_by = ", ".join(f"`{column}`" for column in order_columns)
    statement = text(
        f"SELECT {selections} FROM `{table_name}`"
        + (f" ORDER BY {order_by}" if order_by else "")
    )

    digest = sha256()
    row_count = 0
    with engine.connect() as connection:
        for batch in _target_value_batches(connection, statement, chunk_size):
            for values in batch:
                record, invalid_columns = normalize_row(columns, values)
                if invalid_columns:
                    raise RuntimeError(
                        "Invalid numeric columns in SQL fingerprint: "
                        f"{invalid_columns}"
                    )
                digest.update(canonical_row_hash(columns, record).encode("ascii"))
                digest.update(b"\n")
                row_count += 1
    return {"rows": row_count, "sha256": digest.hexdigest().upper()}


def table_schema_signature(engine, table_name):
    table_name = validate_identifier(table_name)
    inspector = inspect(engine)
    columns = [
        {
            "name": normalize_column_name(column["name"]),
            "type": str(column["type"]),
            "nullable": bool(column.get("nullable", True)),
            "default": (
                None if column.get("default") is None else str(column["default"])
            ),
            "autoincrement": str(column.get("autoincrement", "auto")),
        }
        for column in inspector.get_columns(table_name)
    ]
    primary_key = tuple(
        normalize_column_name(column)
        for column in inspector.get_pk_constraint(table_name).get(
            "constrained_columns", ()
        )
    )
    indexes = sorted(
        (
            str(index.get("name") or ""),
            bool(index.get("unique")),
            tuple(
                normalize_column_name(column)
                for column in index.get("column_names", ())
                if column is not None
            ),
        )
        for index in inspector.get_indexes(table_name)
    )
    payload = {
        "columns": columns,
        "primary_key": primary_key,
        "indexes": indexes,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return {
        "sha256": sha256(encoded).hexdigest().upper(),
        "column_count": len(columns),
        "primary_key": primary_key,
        "indexes": indexes,
    }


def verify_euro_backup_restore(
    production_engine,
    import_key,
    backup_file,
    confirmation,
    *,
    mysql_path=None,
    schema=None,
):
    import_key, contract = _euro_contract(import_key)
    expected_confirmation = verification_confirmation(import_key)
    if confirmation != expected_confirmation:
        raise ValueError(f"--confirm must exactly match {expected_confirmation}")

    table_name = validate_identifier(contract["table_name"])
    backup = validate_scoped_backup(backup_file, (table_name,))
    columns = mapped_source_columns(contract)
    test_schema = validate_test_schema_name(schema or new_test_schema_name())
    active_before = table_fingerprint(production_engine, table_name, columns)
    active_schema_before = table_schema_signature(production_engine, table_name)

    test_engine = None
    schema_created = False
    restored = None
    restored_schema = None
    try:
        create_test_schema(production_engine, test_schema)
        schema_created = True
        test_engine = create_engine(_database_url(test_schema), pool_pre_ping=True)
        restore_backup(backup["path"], test_schema, mysql_path=mysql_path)
        if not inspect(test_engine).has_table(table_name):
            raise RuntimeError(f"Restored table not found: {table_name}")
        restored = table_fingerprint(test_engine, table_name, columns)
        restored_schema = table_schema_signature(test_engine, table_name)
        if restored != active_before:
            raise RuntimeError("Restored table fingerprint differs from active table")
        if restored_schema != active_schema_before:
            raise RuntimeError("Restored table schema differs from active table")
    finally:
        if test_engine is not None:
            test_engine.dispose()
        if schema_created:
            drop_test_schema(production_engine, test_schema)

    active_after = table_fingerprint(production_engine, table_name, columns)
    active_schema_after = table_schema_signature(production_engine, table_name)
    if active_after != active_before or active_schema_after != active_schema_before:
        raise RuntimeError("Active table changed during isolated backup verification")

    with production_engine.connect() as connection:
        temporary_schema_removed = not _schema_exists(connection, test_schema)
    if not temporary_schema_removed:
        raise RuntimeError(f"Temporary schema still exists: {test_schema}")

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "version": BACKUP_VERIFY_VERSION,
        "import_key": import_key,
        "active_table": table_name,
        "backup": {
            "path": str(backup["path"]),
            "bytes": backup["bytes"],
            "sha256": backup["sha256"],
        },
        "active_before": active_before,
        "restored": restored,
        "active_after": active_after,
        "active_schema_before": active_schema_before,
        "restored_schema": restored_schema,
        "active_schema_after": active_schema_after,
        "temporary_schema": test_schema,
        "temporary_schema_created": True,
        "temporary_schema_removed": temporary_schema_removed,
        "restore_verified": True,
        "database_write_scope": "temporary_isolated_schema_only",
        "active_database_write_performed": False,
        "active_table_changed": False,
        "isolated_schema_write_performed": True,
    }


def write_backup_restore_report(output_dir, report):
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"euro_backup_restore_{timestamp}.json"
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=True, default=str),
        encoding="utf-8",
    )
    return path
