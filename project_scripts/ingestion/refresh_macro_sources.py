from pathlib import Path
import sys


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from macro_import_manifest import MACRO_IMPORTS, get_macro_import_keys
from services.macro_import_service import (
    apply_macro_import,
    build_import_parser,
    format_macro_preview,
    preview_macro_import,
)


def _selected_keys(target):
    if target == "ALL":
        return list(MACRO_IMPORTS)
    if target in {"FED", "EURO"}:
        return get_macro_import_keys(target)
    return [target]


def main(argv=None):
    args = build_import_parser().parse_args(argv)
    keys = _selected_keys(args.target)
    if args.update_sql:
        if len(keys) != 1:
            raise SystemExit("--update-sql requires one explicit import key")
        if not args.backup_file or not args.confirm_table:
            raise SystemExit(
                "--backup-file and --confirm-table are required with --update-sql"
            )
        result = apply_macro_import(
            keys[0],
            backup_file=args.backup_file,
            confirm_table=args.confirm_table,
            chunk_size=args.chunk_size,
        )
        for key, value in result.items():
            print(f"{key}: {value}")
        return 0

    failures = 0
    for index, import_key in enumerate(keys, start=1):
        preview = preview_macro_import(
            import_key,
            sample_rows=args.sample_rows,
            full_scan=args.full_scan,
            check_sql=args.check_sql,
        )
        print(f"\n[{index}/{len(keys)}]")
        print(format_macro_preview(preview))
        if not preview.source_exists or preview.missing_required_columns:
            failures += 1
    print(f"\nPreview completed: {len(keys) - failures} OK, {failures} failed")
    print("database_write_performed: False")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
