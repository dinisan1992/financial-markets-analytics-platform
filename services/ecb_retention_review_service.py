from __future__ import annotations

from dataclasses import asdict, dataclass

from sqlalchemy import inspect, text

from services.euro_backup_restore_service import table_schema_signature
from services.euro_rebuild_service import HASH_COLUMN
from services.macro_import_service import normalize_column_name
from services.market_data_sync_service import validate_identifier


REVIEW_VERSION = "v088"


@dataclass(frozen=True)
class RetainedContract:
    import_key: str
    active_table: str
    retained_table: str
    expected_active_rows: int
    expected_retained_rows: int


RETAINED_CONTRACTS = (
    RetainedContract(
        import_key="EURO_BANK_LENDING_SURVEY",
        active_table="euro_bank_lending_survey",
        retained_table=(
            "euro_bank_lending_survey__pre_v079_20260817_115720"
        ),
        expected_active_rows=1_225_110,
        expected_retained_rows=1_164_356,
    ),
    RetainedContract(
        import_key="EURO_CARD_PAYMENTS",
        active_table="euro_card_payments",
        retained_table="euro_card_payments__pre_v079_20260817_115720",
        expected_active_rows=1_081_151,
        expected_retained_rows=815_173,
    ),
    RetainedContract(
        import_key="EURO_BALANCE_SHEET_ITEMS",
        active_table="euro_balance_sheet_items",
        retained_table=(
            "euro_balance_sheet_items__pre_v079_20260817_141854"
        ),
        expected_active_rows=8_055_309,
        expected_retained_rows=7_812_208,
    ),
)


def _exact_rows(connection, table_name):
    table_name = validate_identifier(table_name)
    return int(
        connection.execute(
            text(f"SELECT COUNT(*) FROM `{table_name}`")
        ).scalar_one()
    )


def _storage_evidence(connection, table_name):
    row = connection.execute(
        text(
            "SELECT ENGINE, TABLE_ROWS, DATA_LENGTH, INDEX_LENGTH "
            "FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :table_name"
        ),
        {"table_name": table_name},
    ).mappings().one()
    data_bytes = int(row["DATA_LENGTH"] or 0)
    index_bytes = int(row["INDEX_LENGTH"] or 0)
    return {
        "engine": row["ENGINE"],
        "estimated_rows": int(row["TABLE_ROWS"] or 0),
        "data_bytes": data_bytes,
        "index_bytes": index_bytes,
        "total_bytes": data_bytes + index_bytes,
    }


def _table_evidence(connection, table_name, expected_rows):
    inspector = inspect(connection)
    columns = tuple(
        normalize_column_name(column["name"])
        for column in inspector.get_columns(table_name)
    )
    primary_key = tuple(
        normalize_column_name(column)
        for column in inspector.get_pk_constraint(table_name).get(
            "constrained_columns", ()
        )
    )
    exact_rows = _exact_rows(connection, table_name)
    return {
        "table": table_name,
        "exact_rows": exact_rows,
        "expected_rows": int(expected_rows),
        "row_count_matches": exact_rows == int(expected_rows),
        "column_count": len(columns),
        "primary_key": primary_key,
        "technical_hash_present": HASH_COLUMN in columns,
        "schema_sha256": table_schema_signature(
            connection.engine,
            table_name,
        )["sha256"],
        "storage": _storage_evidence(connection, table_name),
    }


def evaluate_contract(
    contract,
    *,
    active_evidence=None,
    retained_evidence=None,
    residual_artifacts=(),
):
    blockers = []
    if active_evidence is None:
        blockers.append("active_table_missing")
    elif not active_evidence["row_count_matches"]:
        blockers.append("active_row_count_changed")
    if retained_evidence is None:
        blockers.append("retained_table_missing")
    elif not retained_evidence["row_count_matches"]:
        blockers.append("retained_row_count_changed")
    if residual_artifacts:
        blockers.append("shadow_or_failed_artifact_present")
    return {
        **asdict(contract),
        "active_evidence": active_evidence,
        "retained_evidence": retained_evidence,
        "residual_artifacts": tuple(residual_artifacts),
        "status": "verified_retain" if not blockers else "review_required",
        "blockers": tuple(blockers),
        "recommendation": "retain",
        "full_data_fingerprint_recomputed": False,
    }


def build_review_payload(results):
    results = tuple(results)
    total_retained_bytes = sum(
        result["retained_evidence"]["storage"]["total_bytes"]
        for result in results
        if result["retained_evidence"] is not None
    )
    verified = sum(result["status"] == "verified_retain" for result in results)
    return {
        "version": REVIEW_VERSION,
        "stage": "ecb_retained_table_review",
        "database_write_performed": False,
        "table_deleted": False,
        "full_data_fingerprint_recomputed": False,
        "contracts": results,
        "summary": {
            "contracts": len(results),
            "verified_retain": verified,
            "review_required": len(results) - verified,
            "total_retained_bytes": total_retained_bytes,
            "all_valid": verified == len(results),
        },
        "recommendation": (
            "Retain every checkpoint until a separately authorized review "
            "confirms a newer verified backup and an adequate observation "
            "window. This report never authorizes deletion."
        ),
    }


def review_ecb_retained_tables(engine, contracts=RETAINED_CONTRACTS):
    with engine.connect() as connection:
        table_names = set(inspect(connection).get_table_names())
        results = []
        for contract in contracts:
            prefix = f"{contract.active_table}__"
            residual_artifacts = sorted(
                table_name
                for table_name in table_names
                if table_name.startswith(prefix)
                and (
                    "__shadow_" in table_name
                    or "__failed_" in table_name
                )
            )
            active = (
                _table_evidence(
                    connection,
                    contract.active_table,
                    contract.expected_active_rows,
                )
                if contract.active_table in table_names
                else None
            )
            retained = (
                _table_evidence(
                    connection,
                    contract.retained_table,
                    contract.expected_retained_rows,
                )
                if contract.retained_table in table_names
                else None
            )
            results.append(
                evaluate_contract(
                    contract,
                    active_evidence=active,
                    retained_evidence=retained,
                    residual_artifacts=residual_artifacts,
                )
            )
    return build_review_payload(results)
