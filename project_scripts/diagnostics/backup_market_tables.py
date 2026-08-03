from pathlib import Path
from datetime import datetime
import argparse
import hashlib
import os
import shutil
import subprocess
import sys


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_CONFIG


DEFAULT_TABLES = (
    "btc_analysis",
    "sp500_analysis_clean",
    "stoxx600_analysis",
    "gold_analysis_clean",
    "dxy_analysis_clean",
    "euro_analysis",
    "yuan_analysis",
    "libra_analysis",
    "ssecomposite_analysis",
)


def resolve_mysqldump(explicit_path=None):
    candidates = [
        Path(explicit_path) if explicit_path else None,
        Path(r"C:\xampp\mysql\bin\mysqldump.exe"),
        Path(shutil.which("mysqldump")) if shutil.which("mysqldump") else None,
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    raise FileNotFoundError("mysqldump executable was not found")


def build_mysqldump_command(executable, tables):
    return [
        str(executable),
        f"--host={DB_CONFIG['host']}",
        f"--port={DB_CONFIG['port']}",
        f"--user={DB_CONFIG['user']}",
        "--single-transaction",
        "--quick",
        "--skip-lock-tables",
        "--default-character-set=utf8mb4",
        DB_CONFIG["database"],
        *tables,
    ]


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest().upper()


def create_backup(output_dir, tables=DEFAULT_TABLES, mysqldump_path=None):
    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"market_tables_before_v050_{timestamp}.sql"
    executable = resolve_mysqldump(mysqldump_path)
    command = build_mysqldump_command(executable, tables)
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = str(DB_CONFIG["password"])

    with output_path.open("wb") as output_handle:
        result = subprocess.run(
            command,
            stdout=output_handle,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )

    if result.returncode != 0:
        output_path.unlink(missing_ok=True)
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"mysqldump failed: {error}")
    if output_path.stat().st_size == 0:
        output_path.unlink(missing_ok=True)
        raise RuntimeError("mysqldump produced an empty backup")

    checksum = sha256_file(output_path)
    print(f"Backup: {output_path}")
    print(f"Tables: {len(tables)}")
    print(f"Bytes: {output_path.stat().st_size}")
    print(f"SHA-256: {checksum}")
    return output_path, checksum


def build_parser():
    parser = argparse.ArgumentParser(
        description="Create a credential-safe SQL backup of scoped market tables."
    )
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--mysqldump")
    parser.add_argument("--tables", nargs="+", default=list(DEFAULT_TABLES))
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    create_backup(
        output_dir=args.output_dir,
        tables=tuple(args.tables),
        mysqldump_path=args.mysqldump,
    )


if __name__ == "__main__":
    main()
