from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from macro_import_manifest import get_macro_import
from services.euro_direct_debits_diagnostic_service import (
    IMPORT_KEY,
    diagnose_euro_direct_debits,
)
from services.euro_rebuild_service import (
    build_rollback_statement,
    build_shadow_schema_statements,
    build_swap_statement,
    failed_table_name,
    retained_table_name,
    shadow_table_name,
)
from services.market_data_sync_service import validate_identifier


REMEDIATION_VERSION = "v067"


def build_direct_debits_rebuild_plan(engine, suffix, diagnostic=None):
    validate_identifier(f"suffix_{suffix}")
    contract = get_macro_import(IMPORT_KEY)
    active_table = validate_identifier(contract["table_name"])
    diagnostic = diagnostic or diagnose_euro_direct_debits(engine)
    summary = diagnostic["summary"]
    if summary["conclusion"] != "lossy_target_time_period_storage_confirmed":
        raise ValueError("Direct Debits period-loss diagnosis is not conclusive")

    shadow = shadow_table_name(
        active_table,
        suffix,
        version=REMEDIATION_VERSION,
    )
    retained = retained_table_name(
        active_table,
        suffix,
        version=REMEDIATION_VERSION,
    )
    failed = failed_table_name(
        active_table,
        suffix,
        version=REMEDIATION_VERSION,
    )
    schema_statements = build_shadow_schema_statements(
        engine,
        IMPORT_KEY,
        suffix,
        version=REMEDIATION_VERSION,
    )
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "plan",
        "version": REMEDIATION_VERSION,
        "import_key": IMPORT_KEY,
        "source_file": Path(contract["csv_path"]).name,
        "active_table": active_table,
        "shadow_table": shadow,
        "retained_table": retained,
        "failed_table": failed,
        "source_rows": summary["source_rows"],
        "active_rows": summary["target_rows"],
        "expected_shadow_rows": summary["source_rows"],
        "current_time_period_type": summary["target_period_type"],
        "proposed_time_period_type": "VARCHAR(20)",
        "source_only_rows": summary["source_only_rows"],
        "target_only_rows": summary["target_only_rows"],
        "unexplained_source_only_rows": summary["unexplained_source_only_rows"],
        "unexplained_target_only_rows": summary["unexplained_target_only_rows"],
        "shadow_schema_statements": schema_statements,
        "future_swap_statement": build_swap_statement(
            (IMPORT_KEY,),
            suffix,
            version=REMEDIATION_VERSION,
        ),
        "future_rollback_statement": build_rollback_statement(
            (IMPORT_KEY,),
            suffix,
            version=REMEDIATION_VERSION,
        ),
        "required_gates": (
            "fresh_table_scoped_structure_and_data_backup",
            "independent_backup_hash_and_restore_verification",
            "exact_source_to_shadow_full_row_validation",
            "separate_build_authorization",
            "separate_atomic_swap_authorization",
            "post_swap_read_only_sync_plan",
        ),
        "write_path_enabled": False,
        "database_write_performed": False,
        "active_table_changed": False,
    }


def write_direct_debits_rebuild_plan(output_dir, plan):
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"euro_direct_debits_rebuild_plan_{timestamp}.json"
    path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=True, default=str),
        encoding="utf-8",
    )
    return path
