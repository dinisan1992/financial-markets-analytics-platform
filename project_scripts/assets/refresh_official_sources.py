from pathlib import Path
import argparse
import sys
import tempfile


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from asset_config import ASSETS
from services.official_market_source_service import (
    download_h15_package,
    prepare_h15_market_frame,
    validate_h15_market_frame,
    write_standard_market_csv,
)


SUPPORTED_ASSETS = ("US2Y",)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Download and validate an official market source. Validation is the "
            "default; replacing a configured CSV requires --write-csv."
        )
    )
    parser.add_argument("asset_key", choices=SUPPORTED_ASSETS)
    parser.add_argument(
        "--input-file",
        help="Use an already-downloaded official package instead of the network.",
    )
    parser.add_argument(
        "--write-csv",
        action="store_true",
        help="Replace the configured local CSV after validation.",
    )
    return parser


def print_summary(asset_key, summary, destination=None):
    print(f"Official source refresh: {asset_key}")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    print(f"  csv_write_performed: {destination is not None}")
    if destination is not None:
        print(f"  destination: {destination}")


def main(argv=None):
    args = build_parser().parse_args(argv)
    asset_key = args.asset_key.upper()

    with tempfile.TemporaryDirectory(prefix="market_source_") as temp_dir:
        package_path = Path(args.input_file).expanduser().resolve() if args.input_file else None
        if package_path is None:
            package_path = download_h15_package(Path(temp_dir) / "h15_package.csv")
        if not package_path.exists():
            raise FileNotFoundError(f"Official source package not found: {package_path}")

        frame = prepare_h15_market_frame(package_path)
        summary = validate_h15_market_frame(frame)
        destination = None
        if args.write_csv:
            destination = write_standard_market_csv(
                frame,
                ASSETS[asset_key]["csv_path"],
            )
        print_summary(asset_key, summary, destination=destination)


if __name__ == "__main__":
    main()
