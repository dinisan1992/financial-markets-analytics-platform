from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from macro_import_manifest import get_macro_import, get_macro_import_keys
from project_scripts.diagnostics.backup_market_tables import create_backup
from services.euro_backup_restore_service import (
    BACKUP_VERIFY_VERSION,
    validate_external_backup_dir,
)
from services.euro_rebuild_service import validate_scoped_backup


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Create and verify a one-table EURO structure-and-data backup on "
            "a separate physical volume. MySQL is read-only."
        )
    )
    parser.add_argument("import_key", choices=get_macro_import_keys("EURO"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mysqldump")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    output_dir = validate_external_backup_dir(args.output_dir, ROOT)
    contract = get_macro_import(args.import_key)
    table_name = contract["table_name"]
    path, digest = create_backup(
        output_dir=output_dir,
        tables=(table_name,),
        mysqldump_path=args.mysqldump,
        filename_prefix=f"{table_name}_before_{BACKUP_VERIFY_VERSION}",
    )
    verification = validate_scoped_backup(path, (table_name,))
    if verification["sha256"] != digest:
        raise RuntimeError("Backup digest changed during verification")
    payload = {
        "import_key": args.import_key,
        "table_name": table_name,
        "path": str(verification["path"]),
        "bytes": verification["bytes"],
        "sha256": verification["sha256"],
        "structure_and_data_verified": True,
        "database_write_performed": False,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    print("Database writes: disabled")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
