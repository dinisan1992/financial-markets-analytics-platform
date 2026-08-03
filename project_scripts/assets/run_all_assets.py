from pathlib import Path
import argparse
import os
import subprocess
import sys
import time


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_config import get_all_asset_keys


VALIDATOR_SCRIPT = Path(__file__).resolve().parent / "new_market_asset.py"


def build_validation_command(asset_key):
    """Build a SQL-only validation command with no database-write flag."""
    return [
        sys.executable,
        str(VALIDATOR_SCRIPT),
        asset_key,
        "--source",
        "sql",
    ]


def validate_asset(asset_key):
    print("\n" + "=" * 70)
    print(f"Validating: {asset_key}")
    print("=" * 70)
    started = time.time()
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            build_validation_command(asset_key),
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=environment,
        )
    except Exception as exc:
        return {
            "asset": asset_key,
            "status": "exception",
            "duration": round(time.time() - started, 2),
            "returncode": None,
            "error": str(exc),
        }

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print("WARNINGS / STDERR:")
        print(result.stderr)

    return {
        "asset": asset_key,
        "status": "success" if result.returncode == 0 else "error",
        "duration": round(time.time() - started, 2),
        "returncode": result.returncode,
        "error": result.stderr or None,
    }


def print_summary(results):
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    success = sum(result["status"] == "success" for result in results)
    failures = len(results) - success
    print(f"Assets: {len(results)}")
    print(f"Success: {success}")
    print(f"Failures: {failures}")
    print("Database writes: disabled")
    for result in results:
        print(
            f"{result['asset']} | status={result['status']} | "
            f"duration={result['duration']}s"
        )


def build_parser():
    parser = argparse.ArgumentParser(
        description="Validate all configured asset tables without importing CSV data."
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop after the first failed asset validation.",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    print("Starting SQL-only validation for configured assets...")
    print(f"Project: {PROJECT_ROOT}")
    print("Database writes: disabled")

    results = []
    for asset_key in get_all_asset_keys():
        result = validate_asset(asset_key)
        results.append(result)
        if args.stop_on_error and result["status"] != "success":
            break

    print_summary(results)
    if any(result["status"] != "success" for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
