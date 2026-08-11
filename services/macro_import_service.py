from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import argparse

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, inspect, text

from config import get_sqlalchemy_database_url
from macro_import_manifest import MACRO_IMPORTS, get_macro_import


@dataclass(frozen=True)
class MacroImportPreview:
    import_key: str
    group: str
    table_name: str
    csv_path: str
    source_exists: bool
    source_bytes: int
    source_columns: int
    sampled_rows: int
    valid_sample_rows: int
    invalid_sample_rows: int
    duplicate_sample_keys: int
    missing_required_columns: tuple[str, ...]
    sql_checked: bool
    table_exists: bool | None
    unique_business_key: bool | None
    write_policy: str
    write_ready: bool
    blocked_reasons: tuple[str, ...]
    database_write_performed: bool = False

    def to_dict(self):
        return asdict(self)


def normalize_column_name(value):
    return (
        str(value)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def normalize_source_columns(frame, contract):
    output = frame.copy()
    output.columns = [normalize_column_name(column) for column in output.columns]
    aliases = {
        normalize_column_name(source): normalize_column_name(target)
        for source, target in contract.get("column_aliases", {}).items()
    }
    return output.rename(columns=aliases)


def prepare_simple_series_frame(frame, contract):
    output = normalize_source_columns(frame, contract)
    required = list(contract["required_columns"])
    missing = [column for column in required if column not in output.columns]
    if missing:
        raise ValueError(f"Missing source columns: {missing}")

    output = output[required].copy()
    output["observation_date"] = pd.to_datetime(
        output["observation_date"], errors="coerce"
    ).dt.normalize()
    value_column = contract["value_column"]
    output[value_column] = pd.to_numeric(output[value_column], errors="coerce")
    output = output.dropna(subset=["observation_date", value_column])
    return (
        output.sort_values("observation_date", kind="mergesort")
        .drop_duplicates("observation_date", keep="last")
        .reset_index(drop=True)
    )


def _prepare_sample(frame, contract):
    normalized = normalize_source_columns(frame, contract)
    required = list(contract["required_columns"])
    missing = tuple(column for column in required if column not in normalized.columns)
    if missing:
        return normalized, missing, 0, len(normalized), 0

    if contract["mode"] == "simple_series":
        candidate = normalized[required].copy()
        candidate["observation_date"] = pd.to_datetime(
            candidate["observation_date"], errors="coerce"
        ).dt.normalize()
        value_column = contract["value_column"]
        candidate[value_column] = pd.to_numeric(
            candidate[value_column], errors="coerce"
        )
        valid = candidate.dropna(subset=["observation_date", value_column])
        invalid_rows = len(candidate) - len(valid)
        duplicate_rows = int(valid.duplicated("observation_date", keep="last").sum())
        prepared = prepare_simple_series_frame(frame, contract)
        valid_rows = len(prepared)
        return prepared, (), valid_rows, invalid_rows, duplicate_rows

    keys = list(contract["source_key_columns"])
    required_values = normalized[required].replace(r"^\s*$", np.nan, regex=True)
    valid_mask = required_values.notna().all(axis=1)
    valid_mask &= pd.to_numeric(
        normalized["obs_value"], errors="coerce"
    ).notna()
    valid = normalized.loc[valid_mask]
    duplicate_rows = int(valid.duplicated(keys, keep="last").sum())
    return normalized, (), int(valid_mask.sum()), int((~valid_mask).sum()), duplicate_rows


def _sql_contract(engine, contract):
    inspector = inspect(engine)
    table_name = contract["table_name"]
    if not inspector.has_table(table_name):
        return False, False

    expected = tuple(normalize_column_name(c) for c in contract["target_key_columns"])
    unique_keys = []
    primary = inspector.get_pk_constraint(table_name).get("constrained_columns") or []
    if primary:
        unique_keys.append(tuple(normalize_column_name(c) for c in primary))
    for item in inspector.get_unique_constraints(table_name):
        columns = item.get("column_names") or []
        if columns:
            unique_keys.append(tuple(normalize_column_name(c) for c in columns))
    for item in inspector.get_indexes(table_name):
        if item.get("unique"):
            columns = item.get("column_names") or []
            if columns:
                unique_keys.append(tuple(normalize_column_name(c) for c in columns))
    return True, expected in unique_keys


def preview_macro_import(
    import_key,
    sample_rows=1000,
    full_scan=False,
    check_sql=False,
    engine=None,
    source_path=None,
):
    contract = get_macro_import(import_key)
    path = Path(source_path or contract["csv_path"])
    blocked = []
    if not path.exists():
        return MacroImportPreview(
            import_key=str(import_key).upper(),
            group=contract["group"],
            table_name=contract["table_name"],
            csv_path=str(path),
            source_exists=False,
            source_bytes=0,
            source_columns=0,
            sampled_rows=0,
            valid_sample_rows=0,
            invalid_sample_rows=0,
            duplicate_sample_keys=0,
            missing_required_columns=tuple(contract["required_columns"]),
            sql_checked=check_sql,
            table_exists=None,
            unique_business_key=None,
            write_policy=contract["write_policy"],
            write_ready=False,
            blocked_reasons=("source_file_missing",),
        )

    read_options = {"dtype": str, "encoding": "utf-8-sig", "low_memory": False}
    if not full_scan:
        read_options["nrows"] = max(1, int(sample_rows))
    frame = pd.read_csv(path, **read_options)
    prepared, missing, valid_rows, invalid_rows, duplicate_rows = _prepare_sample(
        frame, contract
    )
    if missing:
        blocked.append("missing_required_columns")
    if invalid_rows:
        blocked.append("invalid_source_rows")
    if duplicate_rows:
        blocked.append("duplicate_source_keys")
    if contract["write_policy"] != "validated_upsert":
        if contract["write_policy"] == "transactional_sync_guarded":
            blocked.append("dedicated_transactional_sync_required")
        else:
            blocked.append(contract["write_policy"])

    table_exists = None
    unique_business_key = None
    owns_engine = False
    if check_sql:
        if engine is None:
            engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
            owns_engine = True
        try:
            table_exists, unique_business_key = _sql_contract(engine, contract)
        finally:
            if owns_engine:
                engine.dispose()
        if not table_exists:
            blocked.append("target_table_missing")
        elif not unique_business_key:
            blocked.append("unique_business_key_missing")

    write_ready = (
        not blocked
        and check_sql
        and table_exists is True
        and unique_business_key is True
    )
    return MacroImportPreview(
        import_key=str(import_key).upper(),
        group=contract["group"],
        table_name=contract["table_name"],
        csv_path=str(path),
        source_exists=True,
        source_bytes=path.stat().st_size,
        source_columns=len(frame.columns),
        sampled_rows=len(frame),
        valid_sample_rows=valid_rows,
        invalid_sample_rows=invalid_rows,
        duplicate_sample_keys=duplicate_rows,
        missing_required_columns=tuple(missing),
        sql_checked=check_sql,
        table_exists=table_exists,
        unique_business_key=unique_business_key,
        write_policy=contract["write_policy"],
        write_ready=write_ready,
        blocked_reasons=tuple(dict.fromkeys(blocked)),
    )


def validate_sql_backup_for_table(backup_path, table_name):
    path = Path(backup_path).expanduser().resolve()
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError(f"A non-empty SQL backup is required: {path}")
    create_marker = f"CREATE TABLE `{table_name}`".encode()
    insert_marker = f"INSERT INTO `{table_name}`".encode()
    digest = sha256()
    found_create = False
    found_insert = False
    overlap = b""
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
            searchable = overlap + chunk
            found_create = found_create or create_marker in searchable
            found_insert = found_insert or insert_marker in searchable
            overlap = searchable[-256:]
    if not found_create or not found_insert:
        raise ValueError(f"SQL backup does not contain structure and data for {table_name}")
    return {
        "path": path,
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest().upper(),
    }


def _mysql_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, np.generic):
        return value.item()
    return value


def apply_macro_import(
    import_key,
    backup_file,
    confirm_table,
    chunk_size=5000,
    engine=None,
    source_path=None,
):
    contract = get_macro_import(import_key)
    table_name = contract["table_name"]
    if confirm_table != table_name:
        raise ValueError(f"--confirm-table must exactly match {table_name}")
    if contract["mode"] != "simple_series":
        raise RuntimeError(
            "EURO SQL writes remain blocked until multidimensional business keys "
            "and complete column mappings are remediated."
        )
    backup = validate_sql_backup_for_table(backup_file, table_name)
    owns_engine = engine is None
    if engine is None:
        engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    preview = preview_macro_import(
        import_key,
        full_scan=True,
        check_sql=True,
        engine=engine,
        source_path=source_path,
    )
    if not preview.write_ready:
        if owns_engine:
            engine.dispose()
        raise RuntimeError(
            f"Import is not write-ready: {', '.join(preview.blocked_reasons)}"
        )

    path = Path(source_path or contract["csv_path"])
    columns = list(contract["required_columns"])
    key_columns = set(contract["target_key_columns"])
    update_columns = [column for column in columns if column not in key_columns]
    column_sql = ", ".join(f"`{column}`" for column in columns)
    values_sql = ", ".join(f":{column}" for column in columns)
    update_sql = ", ".join(
        f"`{column}` = VALUES(`{column}`)" for column in update_columns
    )
    statement = text(
        f"INSERT INTO `{table_name}` ({column_sql}) VALUES ({values_sql}) "
        f"ON DUPLICATE KEY UPDATE {update_sql}"
    )

    affected = 0
    try:
        with engine.begin() as connection:
            for chunk in pd.read_csv(
                path,
                dtype=str,
                encoding="utf-8-sig",
                chunksize=max(1, int(chunk_size)),
            ):
                prepared = prepare_simple_series_frame(chunk, contract)
                if prepared.empty:
                    continue
                rows = [
                    {column: _mysql_value(row[column]) for column in columns}
                    for _, row in prepared.iterrows()
                ]
                result = connection.execute(statement, rows)
                affected += max(0, int(result.rowcount or 0))
    finally:
        if owns_engine:
            engine.dispose()
    return {
        "import_key": str(import_key).upper(),
        "table_name": table_name,
        "affected_rows": affected,
        "backup_sha256": backup["sha256"],
        "database_write_performed": True,
    }


def format_macro_preview(preview):
    data = preview.to_dict()
    lines = [f"Macro import preview: {preview.import_key}"]
    for key, value in data.items():
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def build_import_parser(import_key=None):
    parser = argparse.ArgumentParser(
        description="Preview a macro CSV import. SQL writes require explicit safeguards."
    )
    if import_key is None:
        parser.add_argument("target", choices=("ALL", "FED", "EURO", *MACRO_IMPORTS))
    parser.add_argument("--check-sql", action="store_true")
    parser.add_argument("--full-scan", action="store_true")
    parser.add_argument("--sample-rows", type=int, default=1000)
    parser.add_argument("--update-sql", action="store_true")
    parser.add_argument("--confirm-table")
    parser.add_argument("--backup-file")
    parser.add_argument("--chunk-size", type=int, default=5000)
    return parser


def run_import_cli(import_key, argv=None):
    args = build_import_parser(import_key=import_key).parse_args(argv)
    if args.update_sql:
        if not args.backup_file or not args.confirm_table:
            raise SystemExit(
                "--backup-file and --confirm-table are required with --update-sql"
            )
        result = apply_macro_import(
            import_key,
            backup_file=args.backup_file,
            confirm_table=args.confirm_table,
            chunk_size=args.chunk_size,
        )
        for key, value in result.items():
            print(f"{key}: {value}")
        return 0

    preview = preview_macro_import(
        import_key,
        sample_rows=args.sample_rows,
        full_scan=args.full_scan,
        check_sql=args.check_sql,
    )
    print(format_macro_preview(preview))
    return 0 if preview.source_exists and not preview.missing_required_columns else 1
