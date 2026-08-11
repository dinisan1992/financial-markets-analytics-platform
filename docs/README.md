# Project Documentation

Current version: v0.7.0

This directory contains the technical evidence, architecture notes, analytical
methodology and controlled database runbooks for the Macro-Financial Risk &
Market Behaviour Analytics Platform. Start with the repository-level
`README.md` for installation, application usage and the current feature set.

## Core Reference

- `PROJECT_STATUS.md` in the repository root: current capabilities, validation
  status, limitations and roadmap.
- `DATABASE_SCHEMA.md`: market, FED, EURO/ECB and event-table contracts.
- `DATA_PIPELINE.md`: source, SQL and analytical processing boundaries.
- `CALCULATION_REFERENCE.md`: financial formulas and interpretation.
- `project_structure.md`: maintained code and command map.
- `CHANGELOG.md`: version-by-version engineering and validation evidence.
- `TODO.md`: completed checkpoints and controlled next steps.

## EURO Data Integrity

- `EURO_SCHEMA_AUDIT.md`: deep schema and source-completeness audit.
- `EURO_TRANSACTIONAL_SYNC.md`: guarded one-contract synchronization design.
- `EURO_SYNC_STATUS.md`: latest 17-contract planning baseline.
- `EURO_DIRECT_DEBITS_REMEDIATION.md`: confirmed temporal-loss diagnosis.
- `EURO_DIRECT_DEBITS_BACKUP.md`: independently restored table backup.
- `EURO_DIRECT_DEBITS_SHADOW.md`: validated v0.6.9 non-active replacement.
- `EURO_DIRECT_DEBITS_SWAP.md`: v0.7.0 atomic promotion and rollback evidence.
- `MACRO_IMPORT_SAFETY.md`: write gates, confirmations and recovery controls.

## Public Repository Boundary

The repository publishes source code, tests and technical documentation. It
does not publish credentials, raw datasets, SQL dumps, generated audit reports
or the local production-scale database. Database migration evidence records
hashes and aggregate results without exposing private paths or data contents.

The platform is an analytical and educational project. Its risk and anomaly
signals are not proof of manipulation and are not financial advice.
