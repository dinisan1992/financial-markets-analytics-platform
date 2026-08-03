from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import sys

from sqlalchemy import create_engine, inspect, text


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import get_sqlalchemy_database_url
from services.macro_import_service import validate_sql_backup_for_table
from services.market_data_sync_service import validate_identifier


TARGET_TABLES = (
    "fed_total_assets",
    "fed_bank_credit",
    "fed_consumer_loans_credit_cards",
    "fed_charge_off_rate_credit_cards",
)
UNIQUE_KEY_NAME = "uq_observation_date"
APPLY_CONFIRMATION = "ADD_FED_OBSERVATION_DATE_KEYS"


@dataclass(frozen=True)
class FedKeyAudit:
    table_name: str
    table_exists: bool
    date_column_exists: bool
    date_nullable: bool | None
    rows_count: int
    non_null_dates: int
    distinct_dates: int
    null_dates: int
    duplicate_groups: int
    first_date: object | None
    last_date: object | None
    unique_date_key: bool

    @property
    def data_ready(self):
        return (
            self.table_exists
            and self.date_column_exists
            and self.date_nullable is False
            and self.null_dates == 0
            and self.duplicate_groups == 0
            and self.rows_count == self.distinct_dates
        )

    def to_dict(self):
        output = asdict(self)
        output["data_ready"] = self.data_ready
        return output


def _unique_date_key(inspector, table_name):
    expected = ("observation_date",)
    candidates = []
    primary = inspector.get_pk_constraint(table_name).get("constrained_columns") or []
    if primary:
        candidates.append(tuple(primary))
    for item in inspector.get_unique_constraints(table_name):
        columns = item.get("column_names") or []
        if columns:
            candidates.append(tuple(columns))
    for item in inspector.get_indexes(table_name):
        columns = item.get("column_names") or []
        if item.get("unique") and columns:
            candidates.append(tuple(columns))
    return expected in candidates


def audit_fed_key_table(engine, table_name):
    table_name = validate_identifier(table_name)
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return FedKeyAudit(
            table_name=table_name,
            table_exists=False,
            date_column_exists=False,
            date_nullable=None,
            rows_count=0,
            non_null_dates=0,
            distinct_dates=0,
            null_dates=0,
            duplicate_groups=0,
            first_date=None,
            last_date=None,
            unique_date_key=False,
        )

    columns = {column["name"]: column for column in inspector.get_columns(table_name)}
    date_column = columns.get("observation_date")
    if date_column is None:
        return FedKeyAudit(
            table_name=table_name,
            table_exists=True,
            date_column_exists=False,
            date_nullable=None,
            rows_count=0,
            non_null_dates=0,
            distinct_dates=0,
            null_dates=0,
            duplicate_groups=0,
            first_date=None,
            last_date=None,
            unique_date_key=False,
        )

    summary_sql = text(
        f"""
        SELECT
            COUNT(*) AS rows_count,
            COUNT(observation_date) AS non_null_dates,
            COUNT(DISTINCT observation_date) AS distinct_dates,
            SUM(observation_date IS NULL) AS null_dates,
            MIN(observation_date) AS first_date,
            MAX(observation_date) AS last_date
        FROM `{table_name}`
        """
    )
    duplicate_sql = text(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT observation_date
            FROM `{table_name}`
            GROUP BY observation_date
            HAVING COUNT(*) > 1
        ) AS duplicate_dates
        """
    )
    with engine.connect() as connection:
        summary = connection.execute(summary_sql).mappings().one()
        duplicate_groups = connection.execute(duplicate_sql).scalar_one()

    return FedKeyAudit(
        table_name=table_name,
        table_exists=True,
        date_column_exists=True,
        date_nullable=bool(date_column["nullable"]),
        rows_count=int(summary["rows_count"] or 0),
        non_null_dates=int(summary["non_null_dates"] or 0),
        distinct_dates=int(summary["distinct_dates"] or 0),
        null_dates=int(summary["null_dates"] or 0),
        duplicate_groups=int(duplicate_groups or 0),
        first_date=summary["first_date"],
        last_date=summary["last_date"],
        unique_date_key=_unique_date_key(inspector, table_name),
    )


def audit_fed_key_targets(engine, tables=TARGET_TABLES):
    return [audit_fed_key_table(engine, table_name) for table_name in tables]


def build_add_key_statement(table_name):
    table_name = validate_identifier(table_name)
    return (
        f"ALTER TABLE `{table_name}` "
        f"ADD UNIQUE KEY `{UNIQUE_KEY_NAME}` (`observation_date`)"
    )


def build_drop_key_statement(table_name):
    table_name = validate_identifier(table_name)
    return f"ALTER TABLE `{table_name}` DROP INDEX `{UNIQUE_KEY_NAME}`"


def validate_scoped_backup(backup_file, tables=TARGET_TABLES):
    results = {
        table_name: validate_sql_backup_for_table(backup_file, table_name)
        for table_name in tables
    }
    checksums = {result["sha256"] for result in results.values()}
    if len(checksums) != 1:
        raise RuntimeError("Backup checksum changed during validation")
    return results


def apply_fed_key_remediation(
    engine,
    backup_file,
    confirmation,
    tables=TARGET_TABLES,
):
    if confirmation != APPLY_CONFIRMATION:
        raise ValueError(f"--confirm must exactly match {APPLY_CONFIRMATION}")

    audits = audit_fed_key_targets(engine, tables)
    blocked = [audit.table_name for audit in audits if not audit.data_ready]
    if blocked:
        raise RuntimeError(
            "FED key remediation blocked by table audit: " + ", ".join(blocked)
        )
    backup = validate_scoped_backup(backup_file, tables)

    changed = []
    for audit in audits:
        if audit.unique_date_key:
            continue
        with engine.begin() as connection:
            connection.execute(text(build_add_key_statement(audit.table_name)))
        changed.append(audit.table_name)

    validated = audit_fed_key_targets(engine, tables)
    failed = [audit.table_name for audit in validated if not audit.unique_date_key]
    if failed:
        rollback = [
            build_drop_key_statement(table_name)
            for table_name in changed
        ]
        raise RuntimeError(
            "Post-migration key validation failed for "
            + ", ".join(failed)
            + ". Reviewed rollback statements: "
            + "; ".join(rollback)
        )

    checksum = next(iter(backup.values()))["sha256"]
    return {
        "changed_tables": tuple(changed),
        "already_ready_tables": tuple(
            audit.table_name for audit in audits if audit.unique_date_key
        ),
        "backup_sha256": checksum,
        "rollback_statements": tuple(
            build_drop_key_statement(table_name) for table_name in changed
        ),
    }


def print_audits(audits, writes_enabled=False):
    print("FED observation-date key remediation")
    print(f"Database writes: {'enabled' if writes_enabled else 'disabled'}")
    for audit in audits:
        print(
            f"{audit.table_name}: rows={audit.rows_count} | "
            f"distinct_dates={audit.distinct_dates} | null_dates={audit.null_dates} | "
            f"duplicate_groups={audit.duplicate_groups} | "
            f"unique_key={audit.unique_date_key} | data_ready={audit.data_ready} | "
            f"range={audit.first_date} -> {audit.last_date}"
        )


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Audit FED observation-date keys. Applying the migration requires "
            "a scoped SQL backup and an exact confirmation phrase."
        )
    )
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-file")
    parser.add_argument("--confirm")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    engine = create_engine(get_sqlalchemy_database_url(), pool_pre_ping=True)
    try:
        audits = audit_fed_key_targets(engine)
        print_audits(audits, writes_enabled=args.apply)
        if not args.apply:
            return 0
        if not args.backup_file or not args.confirm:
            raise SystemExit("--backup-file and --confirm are required with --apply")
        result = apply_fed_key_remediation(
            engine=engine,
            backup_file=args.backup_file,
            confirmation=args.confirm,
        )
        print(f"Changed tables: {len(result['changed_tables'])}")
        print(f"Already ready: {len(result['already_ready_tables'])}")
        print(f"Backup SHA-256: {result['backup_sha256']}")
        print("Rollback statements (review before any use):")
        for statement in result["rollback_statements"]:
            print(f"  {statement};")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
