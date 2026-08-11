from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DB_CONFIG, get_sqlalchemy_database_url
from macro_import_manifest import get_macro_import
from project_scripts.diagnostics.backup_market_tables import create_backup
from services.euro_rebuild_service import (
    BUSINESS_KEY,
    canonical_row_hash,
    mapped_source_columns,
    normalize_row,
)
from services.euro_sync_service import (
    apply_euro_sync,
    build_euro_sync_plan,
    sync_confirmation,
)
from services.macro_import_service import validate_sql_backup_for_table
from services.market_data_sync_service import validate_identifier


IMPORT_KEY = "EURO_FRAUD_LOSSES"
ACCEPTANCE_VERSION = "v065"
TEST_SCHEMA_PREFIX = "mfi_sync_acceptance_v065_"
EXECUTION_CONFIRMATION = "RUN_ISOLATED_EURO_FRAUD_MYSQL_ACCEPTANCE_V065"
DEFAULT_BACKUP_DIR = (
    Path(os.environ["PROJECT_BACKUP_DIR"]).expanduser()
    if os.getenv("PROJECT_BACKUP_DIR")
    else None
)


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


def validate_backup_dir(value):
    path = Path(value).expanduser().resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        return path
    raise ValueError("Acceptance backups must be stored outside the repository")


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


def table_fingerprint(engine, table_name, columns):
    table_name = validate_identifier(table_name)
    columns = tuple(validate_identifier(column) for column in columns)
    selections = ", ".join(f"`{column}`" for column in columns)
    order_by = ", ".join(f"`{column}`" for column in BUSINESS_KEY)
    statement = text(
        f"SELECT {selections} FROM `{table_name}` ORDER BY {order_by}"
    )
    digest = sha256()
    row_count = 0
    with engine.connect() as connection:
        rows = connection.execution_options(stream_results=True).execute(
            statement
        ).mappings()
        for row in rows:
            record, invalid_columns = normalize_row(
                columns,
                tuple(row[column] for column in columns),
            )
            if invalid_columns:
                raise RuntimeError(
                    f"Invalid numeric columns in SQL fingerprint: {invalid_columns}"
                )
            payload = json.dumps(
                [
                    record[BUSINESS_KEY[0]],
                    record[BUSINESS_KEY[1]],
                    canonical_row_hash(columns, record),
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
            digest.update(payload)
            digest.update(b"\n")
            row_count += 1
    return {"rows": row_count, "sha256": digest.hexdigest().upper()}


def _raw_column_map(frame, mapped_columns):
    if len(frame.columns) != len(mapped_columns):
        raise ValueError("Raw and mapped source column counts differ")
    return dict(zip(mapped_columns, frame.columns))


def _increment_decimal(value, amount):
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation as exc:
        raise ValueError(f"Cannot increment non-numeric value: {value}") from exc
    if not number.is_finite():
        raise ValueError(f"Cannot increment non-finite value: {value}")
    return format(number + Decimal(str(amount)), "f")


def _numeric_row(frame, raw_obs_column, excluded=()):
    excluded = set(excluded)
    for index, value in frame[raw_obs_column].items():
        if index in excluded or not str(value).strip():
            continue
        try:
            if Decimal(str(value).strip()).is_finite():
                return index
        except InvalidOperation:
            continue
    raise ValueError("Source fixture has no usable numeric observation")


def _nullable_text_cell(frame, column_map, nullable_columns, excluded=()):
    excluded = set(excluded)
    preferences = (
        "comment_obs",
        "comment_ts",
        "title_compl",
        "coverage",
        "method_ref",
        "title",
        "obs_status",
        "freq",
    )
    for mapped_column in preferences:
        if mapped_column not in nullable_columns or mapped_column not in column_map:
            continue
        raw_column = column_map[mapped_column]
        for index, value in frame[raw_column].items():
            if index not in excluded and str(value).strip():
                return index, mapped_column, raw_column
    raise ValueError("Source fixture has no non-empty nullable text cell")


def build_success_fixture_frame(frame, mapped_columns, nullable_columns):
    output = frame.copy()
    column_map = _raw_column_map(output, mapped_columns)
    raw_obs = column_map["obs_value"]
    raw_key = column_map[BUSINESS_KEY[0]]
    raw_period = column_map[BUSINESS_KEY[1]]

    update_index = _numeric_row(output, raw_obs)
    output.at[update_index, raw_obs] = _increment_decimal(
        output.at[update_index, raw_obs],
        "1.25",
    )
    null_index, null_column, raw_null = _nullable_text_cell(
        output,
        column_map,
        set(nullable_columns),
        excluded=(update_index,),
    )
    output.at[null_index, raw_null] = ""

    insert_index = next(
        index for index in output.index if index not in {update_index, null_index}
    )
    inserted = output.loc[[insert_index]].copy()
    key_value = str(inserted.iloc[0][raw_key])
    existing_periods = set(
        output.loc[output[raw_key].astype(str) == key_value, raw_period].astype(str)
    )
    new_period = next(
        candidate
        for candidate in ("2099-S1", "2099-S2", "2099")
        if candidate not in existing_periods
    )
    inserted.iloc[0, inserted.columns.get_loc(raw_period)] = new_period
    output = pd.concat([output, inserted], ignore_index=True)

    return output, {
        "planned_inserts": 1,
        "planned_updates": 2,
        "null_overwrite_column": null_column,
        "synthetic_period": new_period,
    }


def build_rollback_fixture_frame(frame, mapped_columns):
    output = frame.copy()
    column_map = _raw_column_map(output, mapped_columns)
    raw_obs = column_map["obs_value"]
    update_index = _numeric_row(output, raw_obs)
    output.at[update_index, raw_obs] = _increment_decimal(
        output.at[update_index, raw_obs],
        "2.5",
    )
    return output


def _write_fixture(frame, path):
    path = Path(path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def _restore_original_test_table(test_engine, backup_file, schema, table_name, mysql_path):
    table_name = validate_identifier(table_name)
    with test_engine.begin() as connection:
        connection.execute(text(f"DROP TABLE `{table_name}`"))
    restore_backup(backup_file, schema, mysql_path=mysql_path)


def _create_failure_trigger(test_engine, table_name):
    table_name = validate_identifier(table_name)
    trigger_name = validate_identifier("force_euro_sync_post_validation_failure")
    with test_engine.begin() as connection:
        connection.execute(
            text(
                f"CREATE TRIGGER `{trigger_name}` BEFORE UPDATE ON `{table_name}` "
                "FOR EACH ROW SET NEW.`obs_value` = "
                "COALESCE(NEW.`obs_value`, 0) + 1"
            )
        )
    return trigger_name


def _assert_idempotent_plan(plan, label):
    if not plan.idempotent:
        raise RuntimeError(
            f"{label} is not exact and idempotent: {plan.to_dict()}"
        )


def run_acceptance(*, backup_dir, report_dir, mysql_path=None):
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    schema = new_test_schema_name()
    backup_dir = validate_backup_dir(backup_dir)
    report_dir = Path(report_dir).expanduser().resolve() / run_id
    report_dir.mkdir(parents=True, exist_ok=False)
    contract = get_macro_import(IMPORT_KEY)
    table_name = contract["table_name"]
    source_path = Path(contract["csv_path"]).expanduser().resolve()
    columns = mapped_source_columns(contract)
    report = {
        "acceptance_version": ACCEPTANCE_VERSION,
        "run_id": run_id,
        "status": "running",
        "import_key": IMPORT_KEY,
        "active_schema": DB_CONFIG["database"],
        "test_schema": schema,
        "active_database_write_performed": False,
        "test_schema_cleaned": False,
    }

    production_engine = create_engine(
        get_sqlalchemy_database_url(),
        pool_pre_ping=True,
    )
    admin_engine = production_engine
    test_engine = None
    schema_created = False
    primary_error = None
    cleanup_error = None
    production_before = None

    try:
        production_plan_before = build_euro_sync_plan(
            production_engine,
            IMPORT_KEY,
            chunk_size=500,
            workspace_dir=report_dir,
            minimum_free_bytes=0,
            source_path=source_path,
        )
        _assert_idempotent_plan(production_plan_before, "Active table before test")
        production_before = table_fingerprint(
            production_engine,
            table_name,
            columns,
        )
        report["production_before"] = production_before

        backup_file, backup_digest = create_backup(
            output_dir=backup_dir,
            tables=(table_name,),
            mysqldump_path=None,
            filename_prefix=f"{table_name}_acceptance_{ACCEPTANCE_VERSION}",
        )
        backup = validate_sql_backup_for_table(backup_file, table_name)
        if backup["sha256"] != backup_digest:
            raise RuntimeError("Backup digest changed during validation")
        report["backup"] = {
            "path": str(backup["path"]),
            "bytes": backup["bytes"],
            "sha256": backup["sha256"],
        }

        create_test_schema(admin_engine, schema)
        schema_created = True
        test_engine = create_engine(_database_url(schema), pool_pre_ping=True)
        restore_backup(backup_file, schema, mysql_path=mysql_path)
        restored = table_fingerprint(test_engine, table_name, columns)
        if restored != production_before:
            raise RuntimeError("Restored table fingerprint differs from production")
        report["restore_verified"] = restored

        source_frame = pd.read_csv(
            source_path,
            dtype=str,
            keep_default_na=False,
            na_filter=False,
            encoding="utf-8-sig",
            low_memory=False,
        )
        nullable_columns = {
            column["name"]
            for column in inspect(test_engine).get_columns(table_name)
            if column.get("nullable")
        }
        success_frame, fixture = build_success_fixture_frame(
            source_frame,
            columns,
            nullable_columns,
        )
        success_path = _write_fixture(
            success_frame,
            report_dir / "success_fixture.csv",
        )
        success_plan = build_euro_sync_plan(
            test_engine,
            IMPORT_KEY,
            chunk_size=100,
            workspace_dir=report_dir,
            minimum_free_bytes=0,
            source_path=success_path,
        )
        if (
            not success_plan.write_ready
            or success_plan.planned_inserts != fixture["planned_inserts"]
            or success_plan.planned_updates != fixture["planned_updates"]
        ):
            raise RuntimeError(
                f"Unexpected acceptance plan: {success_plan.to_dict()}"
            )
        success_result = apply_euro_sync(
            test_engine,
            IMPORT_KEY,
            backup_file=backup_file,
            confirmation=sync_confirmation(IMPORT_KEY),
            chunk_size=100,
            insert_batch_size=25,
            workspace_dir=report_dir,
            minimum_free_bytes=0,
            source_path=success_path,
        )
        idempotent_result = apply_euro_sync(
            test_engine,
            IMPORT_KEY,
            backup_file=backup_file,
            confirmation=sync_confirmation(IMPORT_KEY),
            chunk_size=100,
            insert_batch_size=25,
            workspace_dir=report_dir,
            minimum_free_bytes=0,
            source_path=success_path,
        )
        if (
            success_result["written_rows"] != 3
            or not success_result["database_write_performed"]
            or idempotent_result["written_rows"] != 0
            or idempotent_result["database_write_performed"]
            or not idempotent_result["plan"]["idempotent"]
        ):
            raise RuntimeError("Success or idempotency acceptance assertion failed")
        report["success_scenario"] = {
            **fixture,
            "written_rows": success_result["written_rows"],
            "post_validation_valid": success_result["post_validation_valid"],
            "idempotent_reapply_writes": idempotent_result["written_rows"],
        }

        _restore_original_test_table(
            test_engine,
            backup_file,
            schema,
            table_name,
            mysql_path,
        )
        before_rollback = table_fingerprint(test_engine, table_name, columns)
        if before_rollback != production_before:
            raise RuntimeError("Test table restore before rollback differs from production")
        rollback_frame = build_rollback_fixture_frame(source_frame, columns)
        rollback_path = _write_fixture(
            rollback_frame,
            report_dir / "rollback_fixture.csv",
        )
        trigger_name = _create_failure_trigger(test_engine, table_name)
        rollback_error = None
        try:
            apply_euro_sync(
                test_engine,
                IMPORT_KEY,
                backup_file=backup_file,
                confirmation=sync_confirmation(IMPORT_KEY),
                chunk_size=100,
                insert_batch_size=25,
                workspace_dir=report_dir,
                minimum_free_bytes=0,
                source_path=rollback_path,
            )
        except RuntimeError as exc:
            rollback_error = str(exc)
        if not rollback_error or "transaction rolled back" not in rollback_error:
            raise RuntimeError(
                "The forced MySQL post-validation failure did not roll back"
            )
        after_rollback = table_fingerprint(test_engine, table_name, columns)
        if after_rollback != before_rollback:
            raise RuntimeError("MySQL rollback did not restore the original rows")
        report["rollback_scenario"] = {
            "trigger": trigger_name,
            "expected_error_observed": True,
            "rows_before": before_rollback["rows"],
            "rows_after": after_rollback["rows"],
            "fingerprint_preserved": True,
        }
    except BaseException as exc:
        primary_error = exc
        report["status"] = "failed"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if test_engine is not None:
            test_engine.dispose()
        if schema_created:
            try:
                drop_test_schema(admin_engine, schema)
                report["test_schema_cleaned"] = True
            except BaseException as exc:
                cleanup_error = exc
                report["cleanup_error"] = f"{type(exc).__name__}: {exc}"

        try:
            if production_before is not None:
                production_after = table_fingerprint(
                    production_engine,
                    table_name,
                    columns,
                )
                report["production_after"] = production_after
                report["production_unchanged"] = (
                    production_after == production_before
                )
                production_plan_after = build_euro_sync_plan(
                    production_engine,
                    IMPORT_KEY,
                    chunk_size=500,
                    workspace_dir=report_dir,
                    minimum_free_bytes=0,
                    source_path=source_path,
                )
                report["production_idempotent_after"] = (
                    production_plan_after.idempotent
                )
                if production_after != production_before:
                    primary_error = primary_error or RuntimeError(
                        "Active production table changed during isolated test"
                    )
                if not production_plan_after.idempotent:
                    primary_error = primary_error or RuntimeError(
                        "Active production table is not exact after isolated test"
                    )
        except BaseException as exc:
            primary_error = primary_error or exc
            report["production_after_error"] = f"{type(exc).__name__}: {exc}"

        production_engine.dispose()
        if primary_error is None and cleanup_error is None:
            report["status"] = "passed"
        else:
            report["status"] = "failed"
            unresolved_error = primary_error or cleanup_error
            report.setdefault(
                "error",
                f"{type(unresolved_error).__name__}: {unresolved_error}",
            )
        report_path = report_dir / "mysql_acceptance_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )
        print(f"Acceptance report: {report_path}")
        print(f"Status: {report['status']}")
        print(f"Active database write performed: {report['active_database_write_performed']}")
        print(f"Temporary schema cleaned: {report['test_schema_cleaned']}")

    if primary_error is not None:
        raise primary_error
    if cleanup_error is not None:
        raise cleanup_error
    return report


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Run the guarded EURO sync against a temporary MySQL schema. "
            "The active database is fingerprinted but never written."
        )
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm")
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=ROOT / "audit_outputs" / "mysql_acceptance_v065",
    )
    parser.add_argument("--mysql")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not args.execute:
        print("Database writes: disabled")
        print("Scope: EURO_FRAUD_LOSSES in a generated temporary schema")
        print(f"Required confirmation: {EXECUTION_CONFIRMATION}")
        return 0
    if args.confirm != EXECUTION_CONFIRMATION:
        raise ValueError(
            f"--confirm must exactly match {EXECUTION_CONFIRMATION}"
        )
    if args.backup_dir is None:
        raise ValueError(
            "--backup-dir or PROJECT_BACKUP_DIR is required in execute mode"
        )
    run_acceptance(
        backup_dir=args.backup_dir,
        report_dir=args.report_dir,
        mysql_path=args.mysql,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
