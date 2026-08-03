# EURO Schema Remediation

Version: v0.5.5

Migration date: 3 August 2026

## Scope

Six EURO tables could not preserve the source time series because of lossy
period types, duplicate business keys or `key_code`-only primary keys. Version
v0.5.5 rebuilt these tables from their registered ECB CSV sources without
updating or deleting rows in place.

## Safety Controls

The migration required:

1. a structure-and-data SQL backup containing all six active tables;
2. an exact confirmation phrase to build shadows;
3. an exact, separate confirmation phrase for the atomic swap;
4. unique and non-null `(key_code, time_period)` source keys;
5. bounded SQL insert batches under the MySQL packet limit;
6. a SHA-256 signature for every normalized source row;
7. recalculation of each signature after reading the row back from MySQL;
8. exact source/shadow row, key and non-null-value counts;
9. post-swap schema and data checks with automatic rollback on failure.

The reusable command is read-only by default:

```powershell
python project_scripts/diagnostics/remediate_euro_rebuild_tables.py --stage plan
```

Building shadows and swapping them are deliberately separate operations. Both
require the verified backup and their exact confirmation phrase:

```powershell
python project_scripts/diagnostics/remediate_euro_rebuild_tables.py --stage build --backup-file <scoped-backup.sql> --confirm BUILD_EURO_REBUILD_SHADOWS --suffix <reviewed-suffix>
python project_scripts/diagnostics/remediate_euro_rebuild_tables.py --stage swap --backup-file <scoped-backup.sql> --confirm SWAP_EURO_REBUILD_SHADOWS --suffix <reviewed-suffix>
```

The verified pre-migration dump contains 324,480,219 bytes and has SHA-256:

`88CFB9475046A301F1F2318E5E58351D862D1AFF53AF0CBEF972844B0725C13F`

The dump and generated JSON/CSV reports remain local and are excluded from Git.
The local report digests are:

- shadow-build report: `7C9C720E05BD437FDCF307F7A968E779EA9159555336A27D03443B150EC26A40`;
- atomic-swap report: `919224C2E214F20328D82DF6269564B297B8256B66BA48957D52396A669B4929`;
- post-swap deep audit: `FA2AD9D377F065A3A6636394CFADDBB456497936BB05646CCDD05AD8A587AF38`.

## Results

| Table | Previous rows | Previous unique keys | Current rows | Recovered keys |
| --- | ---: | ---: | ---: | ---: |
| `euro_atm_pos_transactions` | 607,291 | 499,995 | 607,291 | 107,296 |
| `euro_card_payments_by_merchant_category` | 30,680 | 30,680 | 419,510 | 388,830 |
| `euro_composite_indicator_stress` | 42 | 42 | 142,527 | 142,485 |
| `euro_country_level_financial_stress` | 28 | 28 | 12,806 | 12,778 |
| `euro_credit_transfers` | 36,244 | 36,244 | 218,564 | 182,320 |
| `euro_emoney_payment_transactions` | 24,194 | 24,194 | 147,202 | 123,008 |

The current tables contain 1,548,900 unique source observations and recover
956,717 business keys relative to the representable history in the former
schemas. All six report zero null keys, duplicate groups, missing source rows,
source-hash mismatches and stored-row-hash mismatches.

## Current Schema Status

The post-migration deep audit reports:

- 11 EURO schemas with safe period types and unique business keys;
- six schemas that remain composite-key candidates;
- zero schemas requiring reconstruction;
- 16/16 configured EURO series available;
- 12/12 active EURO/market pairs operational.

General EURO refresh writes remain intentionally disabled. A future updater
must define the missing-observation policy, use transactions and pass
database-backed source synchronization tests before writes can be enabled.

## Recovery

All six former tables remain in MySQL under versioned `pre_v055` names. The
migration report records an atomic rollback statement that moves the current
tables to `failed_v055` names and restores every retained table in one operation.

Retained tables must not be deleted until a later, separately approved cleanup
checkpoint confirms stable application operation and preserves an external SQL
backup.

## v0.5.6 Follow-up

The six remaining candidates received a complete source-cardinality and
full-row review. Fraud losses, retail interest rates and payment-system
transactions were rebuilt exactly from 112,559 rows and their former tables
remain under `pre_v056` names. Consumer prices, national accounts and MFI
interest rates were reclassified as rebuilds because the active SQL tables are
missing 9,475,513 registered source rows.

See `EURO_SOURCE_COMPLETENESS.md` for the exact counts, report digests and the
memory-bounded migration plan for those larger tables.
