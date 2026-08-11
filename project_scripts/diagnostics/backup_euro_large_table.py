from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from macro_import_manifest import get_macro_import
from project_scripts.diagnostics.backup_market_tables import create_backup
from services.euro_large_rebuild_service import (
    REBUILD_VERSION,
    TARGET_IMPORT_KEYS,
)
from services.euro_rebuild_service import validate_scoped_backup


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create and verify a structure-and-data backup for one large "
            "EURO table without modifying MySQL."
        )
    )
    parser.add_argument("import_key", choices=TARGET_IMPORT_KEYS)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mysqldump")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    table_name = get_macro_import(args.import_key)["table_name"]
    prefix = f"{table_name}_before_{REBUILD_VERSION}"
    path, digest = create_backup(
        output_dir=args.output_dir,
        tables=(table_name,),
        mysqldump_path=args.mysqldump,
        filename_prefix=prefix,
    )
    verification = validate_scoped_backup(path, (table_name,))
    if verification["sha256"] != digest:
        raise RuntimeError("Backup digest changed during verification")
    print("Backup verification: passed")
    print("Database writes: disabled")
    print(f"Verified table: {table_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
