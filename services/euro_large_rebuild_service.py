from __future__ import annotations

from math import ceil
from pathlib import Path
import shutil
from tempfile import gettempdir

from sqlalchemy import text

from macro_import_manifest import get_macro_import
from services.euro_rebuild_service import (
    BUILD_CONFIRMATION,
    SWAP_CONFIRMATION,
    build_and_validate_shadows,
    swap_validated_shadows,
)
from services.market_data_sync_service import validate_identifier


TARGET_IMPORT_KEYS = (
    "EURO_CONSUMER_PRICES",
    "EURO_NATIONAL_ACCOUNTS",
    "EURO_MFI_INTEREST_RATES",
)
REBUILD_VERSION = "v062"
DEFAULT_OPERATING_RESERVE_BYTES = 5 * 1024**3
V061_AUDIT_BASELINES = {
    "EURO_CONSUMER_PRICES": {
        "source_rows": 6_548_663,
        "comparison_store_bytes": 600_059_904,
    },
    "EURO_NATIONAL_ACCOUNTS": {
        "source_rows": 2_721_359,
        "comparison_store_bytes": 352_198_656,
    },
    "EURO_MFI_INTEREST_RATES": {
        "source_rows": 1_594_491,
        "comparison_store_bytes": 154_017_792,
    },
}


def validate_large_import_key(import_key):
    import_key = str(import_key).upper()
    if import_key not in TARGET_IMPORT_KEYS:
        raise ValueError(f"Unsupported large EURO rebuild: {import_key}")
    return import_key


def build_confirmation(import_key):
    import_key = validate_large_import_key(import_key)
    return f"BUILD_{import_key}_{REBUILD_VERSION.upper()}_SHADOW"


def swap_confirmation(import_key):
    import_key = validate_large_import_key(import_key)
    return f"SWAP_{import_key}_{REBUILD_VERSION.upper()}_SHADOW"


def build_large_shadow(
    engine,
    import_key,
    backup_file,
    confirmation,
    suffix,
    chunk_size=50_000,
    insert_batch_size=250,
    workspace_dir=None,
):
    import_key = validate_large_import_key(import_key)
    expected = build_confirmation(import_key)
    if confirmation != expected:
        raise ValueError(f"--confirm must exactly match {expected}")
    return build_and_validate_shadows(
        engine=engine,
        backup_file=backup_file,
        confirmation=BUILD_CONFIRMATION,
        suffix=suffix,
        chunk_size=chunk_size,
        insert_batch_size=insert_batch_size,
        import_keys=(import_key,),
        version=REBUILD_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
    )


def swap_large_shadow(
    engine,
    import_key,
    backup_file,
    confirmation,
    suffix,
    chunk_size=50_000,
    workspace_dir=None,
):
    import_key = validate_large_import_key(import_key)
    expected = swap_confirmation(import_key)
    if confirmation != expected:
        raise ValueError(f"--confirm must exactly match {expected}")
    return swap_validated_shadows(
        engine=engine,
        backup_file=backup_file,
        confirmation=SWAP_CONFIRMATION,
        suffix=suffix,
        chunk_size=chunk_size,
        import_keys=(import_key,),
        version=REBUILD_VERSION,
        memory_bounded=True,
        workspace_dir=workspace_dir,
    )


def estimate_large_rebuild_capacity(
    engine,
    import_key,
    *,
    workspace_dir=None,
    operating_reserve_bytes=DEFAULT_OPERATING_RESERVE_BYTES,
):
    """Return a read-only capacity estimate for one future shadow build."""
    import_key = validate_large_import_key(import_key)
    contract = get_macro_import(import_key)
    table_name = validate_identifier(contract["table_name"])
    source_path = Path(contract["csv_path"]).expanduser().resolve()
    if not source_path.is_file():
        raise FileNotFoundError(f"EURO source CSV not found: {source_path}")

    query = text(
        f"""
        SELECT
            @@datadir AS mysql_data_dir,
            (SELECT COUNT(*) FROM `{table_name}`) AS target_rows,
            COALESCE((
                SELECT data_length + index_length
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                  AND table_name = :table_name
            ), 0) AS active_table_bytes
        """
    )
    with engine.connect() as connection:
        database = dict(
            connection.execute(
                query,
                {"table_name": table_name},
            ).mappings().one()
        )

    target_rows = int(database["target_rows"] or 0)
    active_table_bytes = int(database["active_table_bytes"] or 0)
    if target_rows < 1 or active_table_bytes < 1:
        raise ValueError(f"Cannot estimate table density: {table_name}")

    baseline = V061_AUDIT_BASELINES[import_key]
    source_rows = int(baseline["source_rows"])
    store_bytes = int(baseline["comparison_store_bytes"])
    estimated_shadow_bytes = ceil(
        active_table_bytes * source_rows / target_rows
    )
    reserve_bytes = max(0, int(operating_reserve_bytes))
    mysql_data_dir = Path(database["mysql_data_dir"]).expanduser().resolve()
    workspace_root = (
        Path(workspace_dir).expanduser().resolve()
        if workspace_dir is not None
        else Path(gettempdir()).resolve()
    )
    if not mysql_data_dir.is_dir():
        raise FileNotFoundError(f"MySQL data directory not found: {mysql_data_dir}")
    if not workspace_root.is_dir():
        raise FileNotFoundError(
            f"Fingerprint workspace does not exist: {workspace_root}"
        )

    mysql_free = shutil.disk_usage(mysql_data_dir).free
    workspace_free = shutil.disk_usage(workspace_root).free
    same_volume = mysql_data_dir.drive.lower() == workspace_root.drive.lower()
    mysql_required = estimated_shadow_bytes + reserve_bytes
    workspace_required = store_bytes + reserve_bytes
    if same_volume:
        combined_required = estimated_shadow_bytes + store_bytes + reserve_bytes
        capacity_pass = mysql_free >= combined_required
    else:
        combined_required = None
        capacity_pass = (
            mysql_free >= mysql_required
            and workspace_free >= workspace_required
        )

    return {
        "import_key": import_key,
        "table_name": table_name,
        "source_file": source_path.name,
        "source_file_bytes": source_path.stat().st_size,
        "source_rows": source_rows,
        "target_rows": target_rows,
        "active_table_bytes": active_table_bytes,
        "estimated_shadow_bytes": estimated_shadow_bytes,
        "comparison_store_peak_bytes": store_bytes,
        "operating_reserve_bytes": reserve_bytes,
        "mysql_free_bytes": mysql_free,
        "workspace_free_bytes": workspace_free,
        "workspace_and_mysql_same_volume": same_volume,
        "combined_required_bytes": combined_required,
        "mysql_required_bytes": mysql_required,
        "workspace_required_bytes": workspace_required,
        "capacity_pass": capacity_pass,
        "backup_space_included": False,
        "backup_recommendation": "Use a separate physical volume.",
        "database_write_performed": False,
    }
