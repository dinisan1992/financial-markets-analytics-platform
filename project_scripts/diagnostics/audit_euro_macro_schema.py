from pathlib import Path
import argparse
import sys

from sqlalchemy import create_engine


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_sqlalchemy_database_url
from services.euro_schema_audit_service import (
    audit_all_euro_schema_contracts,
    audit_configured_euro_series,
    write_euro_audit_report,
)


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Audit EURO CSV/SQL mappings and business keys. This command is "
            "strictly read-only."
        )
    )
    parser.add_argument("--deep", action="store_true")
    parser.add_argument("--sample-rows", type=int, default=1000)
    parser.add_argument("--output-dir")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        audits = audit_all_euro_schema_contracts(
            engine,
            sample_rows=args.sample_rows,
            deep=args.deep,
        )
        series_audits = audit_configured_euro_series(engine)
    finally:
        engine.dispose()

    print("EURO schema audit")
    print("Database writes: disabled")
    for audit in audits:
        print(
            f"{audit.import_key}: class={audit.remediation_class} | "
            f"rows={audit.target_rows} | key={audit.primary_key} | "
            f"period={audit.target_period_type}/{audit.period_patterns} | "
            f"duplicates={audit.duplicate_business_key_groups} | "
            f"blockers={audit.blockers}"
        )

    classes = {}
    for audit in audits:
        classes[audit.remediation_class] = classes.get(audit.remediation_class, 0) + 1
    print(f"Classification: {classes}")
    available = sum(audit.status == "available" for audit in series_audits)
    print(f"Configured series available: {available}/{len(series_audits)}")
    print("database_write_performed: False")

    if args.output_dir:
        outputs = write_euro_audit_report(
            args.output_dir,
            audits,
            series_audits,
        )
        for name, value in outputs.items():
            print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
