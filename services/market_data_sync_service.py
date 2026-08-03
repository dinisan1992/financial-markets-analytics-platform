from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import csv
import re

import numpy as np
import pandas as pd
from sqlalchemy import text

from services.data_access_service import deduplicate_market_observations


MARKET_SOURCE_COLUMNS = (
    "snapped_at",
    "price",
    "market_cap",
    "total_volume",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
    "source_file",
)
NUMERIC_SOURCE_COLUMNS = (
    "price",
    "market_cap",
    "total_volume",
    "open",
    "high",
    "low",
    "close",
    "adj_close",
)
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


@dataclass(frozen=True)
class PreparedMarketFrame:
    frame: pd.DataFrame
    source_rows: int
    invalid_rows: int
    duplicate_rows: int
    duplicate_date_groups: int
    csv_path: Path | None = None


@dataclass(frozen=True)
class MarketSyncPlan:
    asset: str
    table: str
    source_rows: int
    valid_source_rows: int
    invalid_source_rows: int
    source_duplicate_rows: int
    source_duplicate_date_groups: int
    existing_rows: int
    existing_unique_dates: int
    existing_duplicate_rows: int
    planned_inserts: int
    planned_updates: int
    unchanged_rows: int
    unique_date_key_available: bool
    first_source_date: object
    last_source_date: object
    database_write_performed: bool = False

    def to_dict(self):
        return asdict(self)


def validate_identifier(identifier):
    value = str(identifier)
    if not IDENTIFIER_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def normalize_columns(frame):
    output = frame.copy()
    output.columns = [
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("%", "percent")
        for column in output.columns
    ]
    return output


def parse_market_number(value):
    if pd.isna(value):
        return np.nan

    normalized = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if normalized.upper() in {"", "-", "NAN", "NONE", "NULL", "N/A"}:
        return np.nan

    negative = normalized.startswith("(") and normalized.endswith(")")
    if negative:
        normalized = normalized[1:-1]

    multiplier = 1.0
    if normalized[-1:].upper() == "K":
        multiplier = 1_000.0
        normalized = normalized[:-1]
    elif normalized[-1:].upper() == "M":
        multiplier = 1_000_000.0
        normalized = normalized[:-1]
    elif normalized[-1:].upper() == "B":
        multiplier = 1_000_000_000.0
        normalized = normalized[:-1]

    if "," in normalized and "." in normalized:
        if normalized.rfind(",") > normalized.rfind("."):
            normalized = normalized.replace(".", "").replace(",", ".")
        else:
            normalized = normalized.replace(",", "")
    elif "," in normalized:
        thousands_pattern = re.fullmatch(r"[-+]?\d{1,3}(,\d{3})+", normalized)
        normalized = (
            normalized.replace(",", "")
            if thousands_pattern
            else normalized.replace(",", ".")
        )

    number = pd.to_numeric(normalized, errors="coerce")
    if pd.isna(number):
        return np.nan
    number = float(number) * multiplier
    return -number if negative else number


def _parse_market_dates(values):
    raw = (
        values.astype(str)
        .str.replace(" UTC", "", regex=False)
        .str.strip()
    )
    slash_dates = raw.str.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}")
    if not raw.empty and slash_dates.all():
        parts = raw.str.split("/", expand=True).astype(int)
        if (parts[0] > 12).any():
            date_format = "%d/%m/%Y"
        elif (parts[1] > 12).any():
            date_format = "%m/%d/%Y"
        else:
            date_format = "%d/%m/%Y"
        return pd.to_datetime(raw, format=date_format, errors="coerce")
    return pd.to_datetime(raw, format="mixed", errors="coerce")


def _repair_single_field_csv_rows(frame):
    if frame.empty or len(frame.columns) < 2:
        return frame
    if frame.iloc[:, 1:].notna().any().any():
        return frame

    first_column = frame.iloc[:, 0]
    if not first_column.astype(str).str.contains(",", regex=False).any():
        return frame

    repaired_rows = []
    for value in first_column:
        parsed = next(csv.reader([str(value)]))
        if len(parsed) != len(frame.columns):
            return frame
        repaired_rows.append(parsed)
    return pd.DataFrame(repaired_rows, columns=frame.columns)


def prepare_market_frame(frame, csv_path=None):
    output = normalize_columns(frame)
    if "total_volume" not in output.columns and "volume" in output.columns:
        output = output.rename(columns={"volume": "total_volume"})
    if "snapped_at" not in output.columns:
        raise ValueError("Missing CSV column: snapped_at")
    if "price" not in output.columns and "close" in output.columns:
        output["price"] = output["close"]
    if "price" not in output.columns:
        raise ValueError("Missing CSV column: price")

    source_rows = len(output)
    selected_columns = [column for column in MARKET_SOURCE_COLUMNS if column in output]
    output = output[selected_columns].copy()
    output["_source_order"] = np.arange(len(output))
    output["snapped_at"] = _parse_market_dates(output["snapped_at"]).dt.normalize()

    for column in NUMERIC_SOURCE_COLUMNS:
        if column in output.columns:
            output[column] = output[column].apply(parse_market_number)

    invalid_mask = output["snapped_at"].isna() | output["price"].isna()
    invalid_rows = int(invalid_mask.sum())
    output = output.loc[~invalid_mask].copy()
    group_sizes = output.groupby("snapped_at").size()
    duplicate_groups = group_sizes[group_sizes > 1]
    duplicate_rows = int((duplicate_groups - 1).sum())

    output = (
        output.sort_values(["snapped_at", "_source_order"], kind="mergesort")
        .drop_duplicates("snapped_at", keep="last")
        .drop(columns="_source_order")
        .reset_index(drop=True)
    )
    if "source_file" not in output.columns and csv_path is not None:
        output["source_file"] = Path(csv_path).name

    return PreparedMarketFrame(
        frame=output,
        source_rows=source_rows,
        invalid_rows=invalid_rows,
        duplicate_rows=duplicate_rows,
        duplicate_date_groups=len(duplicate_groups),
        csv_path=Path(csv_path) if csv_path is not None else None,
    )


def read_market_csv(csv_path):
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    last_error = None
    for encoding in ("utf-8-sig", "latin1"):
        try:
            frame = pd.read_csv(
                path,
                sep=None,
                engine="python",
                dtype=str,
                encoding=encoding,
            )
            frame = _repair_single_field_csv_rows(frame)
            return prepare_market_frame(frame, csv_path=path)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Unable to decode CSV: {path}") from last_error


def get_table_schema(engine, table_name):
    table_name = validate_identifier(table_name)
    query = text(
        """
        SELECT
            column_name,
            is_nullable,
            column_default,
            extra
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = :table_name
        ORDER BY ordinal_position
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"table_name": table_name}).mappings().all()
    if not rows:
        raise ValueError(f"Table not found: {table_name}")
    return [dict(row) for row in rows]


def has_unique_date_key(engine, table_name, date_column="snapped_at"):
    table_name = validate_identifier(table_name)
    date_column = validate_identifier(date_column)
    query = text(
        """
        SELECT COUNT(*) AS key_count
        FROM information_schema.statistics
        WHERE table_schema = DATABASE()
          AND table_name = :table_name
          AND column_name = :date_column
          AND non_unique = 0
        """
    )
    with engine.connect() as connection:
        count = connection.execute(
            query,
            {"table_name": table_name, "date_column": date_column},
        ).scalar_one()
    return int(count) > 0


def load_existing_market_frame(engine, table_name, table_schema=None):
    table_name = validate_identifier(table_name)
    schema = table_schema or get_table_schema(engine, table_name)
    table_columns = {row["column_name"] for row in schema}
    selected = [column for column in MARKET_SOURCE_COLUMNS if column in table_columns]
    if "snapped_at" not in selected or "price" not in selected:
        raise ValueError(f"Table {table_name} must contain snapped_at and price")

    quoted = ", ".join(f"`{validate_identifier(column)}`" for column in selected)
    query = f"SELECT {quoted} FROM `{table_name}` ORDER BY `snapped_at`"
    return pd.read_sql(query, engine)


def _values_equal(source_value, existing_value):
    if pd.isna(source_value):
        return True
    if pd.isna(existing_value):
        return False
    if isinstance(source_value, (int, float, np.number)):
        return bool(
            np.isclose(
                float(source_value),
                float(existing_value),
                rtol=1e-5,
                atol=1e-6,
            )
        )
    return str(source_value) == str(existing_value)


def build_market_sync_plan(
    asset,
    table,
    prepared_source,
    existing_frame,
    unique_date_key_available,
):
    existing = existing_frame.copy()
    if not existing.empty:
        existing["snapped_at"] = pd.to_datetime(
            existing["snapped_at"], errors="coerce"
        ).dt.normalize()
        existing = existing.dropna(subset=["snapped_at"])
    existing_rows = len(existing)
    canonical = deduplicate_market_observations(existing, "snapped_at")
    existing_duplicate_rows = existing_rows - len(canonical)
    lookup = canonical.set_index("snapped_at") if not canonical.empty else canonical
    comparable = [
        column
        for column in prepared_source.frame.columns
        if column != "snapped_at" and column in canonical.columns
    ]
    actions = []

    for _, source_row in prepared_source.frame.iterrows():
        snapped_at = source_row["snapped_at"]
        if canonical.empty or snapped_at not in lookup.index:
            action = "insert"
        else:
            current = lookup.loc[snapped_at]
            changed = any(
                not _values_equal(source_row[column], current[column])
                for column in comparable
            )
            action = "update" if changed else "unchanged"
        actions.append({"snapped_at": snapped_at, "action": action})

    actions_frame = pd.DataFrame(actions, columns=["snapped_at", "action"])
    action_values = actions_frame["action"] if not actions_frame.empty else pd.Series(dtype=str)
    source = prepared_source.frame
    plan = MarketSyncPlan(
        asset=asset,
        table=table,
        source_rows=prepared_source.source_rows,
        valid_source_rows=len(source),
        invalid_source_rows=prepared_source.invalid_rows,
        source_duplicate_rows=prepared_source.duplicate_rows,
        source_duplicate_date_groups=prepared_source.duplicate_date_groups,
        existing_rows=existing_rows,
        existing_unique_dates=len(canonical),
        existing_duplicate_rows=existing_duplicate_rows,
        planned_inserts=int(action_values.eq("insert").sum()),
        planned_updates=int(action_values.eq("update").sum()),
        unchanged_rows=int(action_values.eq("unchanged").sum()),
        unique_date_key_available=bool(unique_date_key_available),
        first_source_date=source["snapped_at"].min().date() if not source.empty else None,
        last_source_date=source["snapped_at"].max().date() if not source.empty else None,
    )
    return plan, actions_frame


def _python_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, np.generic):
        return value.item()
    return value


def apply_market_sync(
    engine,
    table_name,
    prepared_source,
    actions_frame,
    table_schema=None,
    chunk_size=500,
):
    table_name = validate_identifier(table_name)
    if not has_unique_date_key(engine, table_name):
        raise ValueError(
            f"Table {table_name} has no unique snapped_at key; refusing SQL write"
        )

    schema = table_schema or get_table_schema(engine, table_name)
    schema_by_name = {row["column_name"]: row for row in schema}
    source = prepared_source.frame.copy()
    actionable_dates = set(
        actions_frame.loc[
            actions_frame["action"].isin(["insert", "update"]),
            "snapped_at",
        ]
    )
    source = source[source["snapped_at"].isin(actionable_dates)].copy()
    if source.empty:
        return 0

    write_columns = [column for column in source.columns if column in schema_by_name]
    for column, column_schema in schema_by_name.items():
        required = (
            column_schema["is_nullable"] == "NO"
            and column_schema["column_default"] is None
            and "auto_increment" not in (column_schema["extra"] or "")
        )
        if required and column not in write_columns:
            if column == "market_cap":
                source[column] = 0
                write_columns.append(column)
            else:
                raise ValueError(
                    f"Required table column is absent from the CSV: {column}"
                )

    if "snapped_at" not in write_columns or "price" not in write_columns:
        raise ValueError("Sync requires snapped_at and price")

    update_columns = [column for column in write_columns if column != "snapped_at"]
    quoted_columns = ", ".join(f"`{validate_identifier(column)}`" for column in write_columns)
    placeholders = ", ".join(f":{column}" for column in write_columns)
    updates = ", ".join(
        f"`{validate_identifier(column)}` = "
        f"COALESCE(VALUES(`{validate_identifier(column)}`), `{validate_identifier(column)}`)"
        for column in update_columns
    )
    statement = text(
        f"INSERT INTO `{table_name}` ({quoted_columns}) VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {updates}"
    )
    records = [
        {column: _python_value(row[column]) for column in write_columns}
        for _, row in source.iterrows()
    ]

    with engine.begin() as connection:
        for start in range(0, len(records), chunk_size):
            connection.execute(statement, records[start:start + chunk_size])
    return len(records)


def format_market_sync_plan(plan):
    values = plan.to_dict()
    lines = [f"Market CSV sync: {values.pop('asset')} -> {values.pop('table')}"]
    lines.extend(f"  {key}: {value}" for key, value in values.items())
    return "\n".join(lines)
