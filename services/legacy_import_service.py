from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_LEGACY_COLUMNS = ("snapped_at", "price", "total_volume")


@dataclass(frozen=True)
class PreparedLegacyFrame:
    frame: pd.DataFrame
    source_rows: int
    invalid_rows: int
    duplicate_rows: int
    duplicate_date_groups: int


@dataclass(frozen=True)
class ImportDryRun:
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
    existing_duplicate_date_groups: int
    planned_inserts: int
    planned_updates: int
    unchanged_rows: int
    source_dates_overlapping_existing_duplicates: int
    first_source_date: object
    last_source_date: object
    database_write_performed: bool = False

    def to_dict(self):
        return asdict(self)


def normalize_columns(frame: pd.DataFrame):
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


def parse_legacy_price(value):
    if pd.isna(value):
        return np.nan
    normalized = str(value).replace(" ", "").replace(",", "").strip()
    return pd.to_numeric(normalized, errors="coerce")


def parse_legacy_volume(value):
    if pd.isna(value):
        return 0.0

    normalized = str(value).upper().replace(" ", "").replace(",", "").strip()
    if normalized in {"", "-", "NAN", "NONE"}:
        return 0.0

    multiplier = 1
    if normalized.endswith("K"):
        multiplier = 1_000
        normalized = normalized[:-1]
    elif normalized.endswith("M"):
        multiplier = 1_000_000
        normalized = normalized[:-1]
    elif normalized.endswith("B"):
        multiplier = 1_000_000_000
        normalized = normalized[:-1]

    try:
        return float(normalized) * multiplier
    except (TypeError, ValueError):
        return 0.0


def _parse_legacy_dates(values: pd.Series):
    raw = values.astype(str).str.replace(" UTC", "", regex=False).str.strip()
    parsed = pd.to_datetime(raw, format="%b %d, %Y", errors="coerce")
    fallback_mask = parsed.isna()
    if fallback_mask.any():
        parsed.loc[fallback_mask] = pd.to_datetime(
            raw.loc[fallback_mask],
            errors="coerce",
        )
    return parsed.dt.normalize()


def prepare_legacy_market_frame(frame: pd.DataFrame):
    """Normalize and deduplicate one legacy daily-market source in memory."""
    output = normalize_columns(frame)
    missing = [column for column in REQUIRED_LEGACY_COLUMNS if column not in output]
    if missing:
        raise ValueError(f"Missing CSV columns: {missing}")

    source_rows = len(output)
    output = output[list(REQUIRED_LEGACY_COLUMNS)].copy()
    output["_source_order"] = np.arange(len(output))
    output["snapped_at"] = _parse_legacy_dates(output["snapped_at"])
    output["price"] = output["price"].apply(parse_legacy_price)
    output["total_volume"] = output["total_volume"].apply(parse_legacy_volume)

    invalid_mask = output["snapped_at"].isna() | output["price"].isna()
    invalid_rows = int(invalid_mask.sum())
    valid = output.loc[~invalid_mask].copy()

    group_sizes = valid.groupby("snapped_at").size()
    duplicate_groups = group_sizes[group_sizes > 1]
    duplicate_rows = int((duplicate_groups - 1).sum())

    valid = (
        valid.sort_values(["snapped_at", "_source_order"])
        .drop_duplicates("snapped_at", keep="last")
        .drop(columns="_source_order")
        .reset_index(drop=True)
    )

    return PreparedLegacyFrame(
        frame=valid,
        source_rows=source_rows,
        invalid_rows=invalid_rows,
        duplicate_rows=duplicate_rows,
        duplicate_date_groups=len(duplicate_groups),
    )


def read_legacy_csv(csv_path):
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    frame = pd.read_csv(path, sep=";", encoding="utf-8-sig", header=0)
    return prepare_legacy_market_frame(frame)


def prepare_existing_market_frame(frame: pd.DataFrame):
    """Normalize existing SQL rows and choose a deterministic canonical row per date."""
    output = normalize_columns(frame)
    missing = [column for column in REQUIRED_LEGACY_COLUMNS if column not in output]
    if missing:
        raise ValueError(f"Missing table columns: {missing}")

    output = output[list(REQUIRED_LEGACY_COLUMNS)].copy()
    output["_row_order"] = np.arange(len(output))
    output["snapped_at"] = pd.to_datetime(output["snapped_at"], errors="coerce").dt.normalize()
    output["price"] = pd.to_numeric(output["price"], errors="coerce")
    output["total_volume"] = pd.to_numeric(output["total_volume"], errors="coerce")
    output = output.dropna(subset=["snapped_at", "price"])
    output["_completeness"] = output[["price", "total_volume"]].notna().sum(axis=1)

    canonical = (
        output.sort_values(["snapped_at", "_completeness", "_row_order"])
        .drop_duplicates("snapped_at", keep="last")
        .drop(columns=["_row_order", "_completeness"])
        .reset_index(drop=True)
    )
    return output, canonical


def build_duplicate_group_preview(existing_frame: pd.DataFrame):
    normalized, _ = prepare_existing_market_frame(existing_frame)
    rows = []

    for snapped_at, group in normalized.groupby("snapped_at", sort=True):
        if len(group) < 2:
            continue
        rows.append(
            {
                "snapped_at": snapped_at.date(),
                "rows_for_date": len(group),
                "rows_removable": len(group) - 1,
                "distinct_prices": group["price"].nunique(dropna=False),
                "distinct_volumes": group["total_volume"].nunique(dropna=False),
                "values_identical": (
                    group["price"].nunique(dropna=False) == 1
                    and group["total_volume"].nunique(dropna=False) == 1
                ),
                "proposed_keep_rule": "most_complete_then_last",
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "snapped_at",
            "rows_for_date",
            "rows_removable",
            "distinct_prices",
            "distinct_volumes",
            "values_identical",
            "proposed_keep_rule",
        ],
    )


def build_existing_duplicate_summary(asset: str, table: str, existing_frame: pd.DataFrame):
    normalized, canonical = prepare_existing_market_frame(existing_frame)
    preview = build_duplicate_group_preview(existing_frame)
    identical_flags = preview["values_identical"].astype(bool)
    return {
        "asset": asset,
        "table": table,
        "existing_rows": len(normalized),
        "existing_unique_dates": len(canonical),
        "existing_duplicate_rows": len(normalized) - len(canonical),
        "existing_duplicate_date_groups": len(preview),
        "identical_duplicate_groups": int(identical_flags.sum()),
        "conflicting_duplicate_groups": int((~identical_flags).sum()),
        "first_duplicate_date": preview["snapped_at"].min() if not preview.empty else None,
        "last_duplicate_date": preview["snapped_at"].max() if not preview.empty else None,
        "max_rows_per_date": int(preview["rows_for_date"].max()) if not preview.empty else 1,
        "database_write_performed": False,
    }


def _values_match(source_row, existing_row):
    price_match = np.isclose(
        source_row["price"],
        existing_row["price"],
        rtol=1e-10,
        atol=1e-12,
        equal_nan=True,
    )
    volume_match = np.isclose(
        source_row["total_volume"],
        existing_row["total_volume"],
        rtol=1e-10,
        atol=1e-12,
        equal_nan=True,
    )
    return bool(price_match and volume_match)


def build_import_dry_run(
    asset: str,
    table: str,
    prepared_source: PreparedLegacyFrame,
    existing_frame: pd.DataFrame,
):
    normalized_existing, canonical_existing = prepare_existing_market_frame(existing_frame)
    existing_counts = normalized_existing.groupby("snapped_at").size()
    canonical_lookup = canonical_existing.set_index("snapped_at")
    actions = []

    for _, source_row in prepared_source.frame.iterrows():
        snapped_at = source_row["snapped_at"]
        if snapped_at not in canonical_lookup.index:
            action = "insert"
            current_price = np.nan
            current_volume = np.nan
            existing_rows_for_date = 0
        else:
            current = canonical_lookup.loc[snapped_at]
            action = "unchanged" if _values_match(source_row, current) else "update"
            current_price = current["price"]
            current_volume = current["total_volume"]
            existing_rows_for_date = int(existing_counts.loc[snapped_at])

        actions.append(
            {
                "snapped_at": snapped_at.date(),
                "action": action,
                "source_price": source_row["price"],
                "source_total_volume": source_row["total_volume"],
                "current_price": current_price,
                "current_total_volume": current_volume,
                "existing_rows_for_date": existing_rows_for_date,
            }
        )

    actions_frame = pd.DataFrame(actions)
    duplicate_date_count = int((existing_counts > 1).sum())
    duplicate_rows = int((existing_counts[existing_counts > 1] - 1).sum())
    overlapping_duplicates = int(
        actions_frame.get("existing_rows_for_date", pd.Series(dtype=int)).gt(1).sum()
    )

    report = ImportDryRun(
        asset=asset,
        table=table,
        source_rows=prepared_source.source_rows,
        valid_source_rows=len(prepared_source.frame),
        invalid_source_rows=prepared_source.invalid_rows,
        source_duplicate_rows=prepared_source.duplicate_rows,
        source_duplicate_date_groups=prepared_source.duplicate_date_groups,
        existing_rows=len(normalized_existing),
        existing_unique_dates=len(canonical_existing),
        existing_duplicate_rows=duplicate_rows,
        existing_duplicate_date_groups=duplicate_date_count,
        planned_inserts=int(actions_frame.get("action", pd.Series(dtype=str)).eq("insert").sum()),
        planned_updates=int(actions_frame.get("action", pd.Series(dtype=str)).eq("update").sum()),
        unchanged_rows=int(actions_frame.get("action", pd.Series(dtype=str)).eq("unchanged").sum()),
        source_dates_overlapping_existing_duplicates=overlapping_duplicates,
        first_source_date=(
            prepared_source.frame["snapped_at"].min().date()
            if not prepared_source.frame.empty
            else None
        ),
        last_source_date=(
            prepared_source.frame["snapped_at"].max().date()
            if not prepared_source.frame.empty
            else None
        ),
    )
    return report, actions_frame


def preview_legacy_csv_import(asset, table, csv_path, existing_frame):
    prepared = read_legacy_csv(csv_path)
    return build_import_dry_run(asset, table, prepared, existing_frame)


def preview_legacy_csv_against_connection(asset, table, csv_path, connection):
    query = f"""
    SELECT snapped_at, price, total_volume
    FROM `{table}`
    ORDER BY snapped_at
    """
    existing = pd.read_sql(query, connection)
    return preview_legacy_csv_import(asset, table, csv_path, existing)


def format_dry_run_report(report: ImportDryRun):
    values = report.to_dict()
    lines = [f"Import dry-run: {values.pop('asset')} -> {values.pop('table')}"]
    lines.extend(f"  {key}: {value}" for key, value in values.items())
    return "\n".join(lines)
