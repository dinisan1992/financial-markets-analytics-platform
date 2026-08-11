# Large EURO Rebuild Results

Version: v0.6.3

Execution date: 11 August 2026

## Outcome

The final three incomplete EURO histories were rebuilt one table at a time
after explicit approval. Each operation used a table-scoped structure-and-data
backup on a separate physical volume, an isolated shadow, a disk-backed
full-row comparison and an atomic rename. No active row was updated or deleted
in place.

| Import | Active rows | Unique keys | Missing | Extra | Hash mismatch | Period range |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| MFI interest rates | 1,594,491 | 1,594,491 | 0 | 0 | 0 | 1980-01 to 2025-08 |
| National accounts | 2,721,359 | 2,721,359 | 0 | 0 | 0 | 1948 to 2025-Q2 |
| Consumer prices | 6,548,663 | 6,548,663 | 0 | 0 | 0 | 1985-01 to 2025-Q2 |
| **Total** | **10,864,513** | **10,864,513** | **0** | **0** | **0** | |

The final audit also reports zero null business keys, duplicate business keys,
invalid numeric observations and source-to-target row-hash differences.

## Verified Backups

The dumps are private local recovery artifacts and are excluded from Git.
Their filenames, byte counts and independently verified SHA-256 values are:

| Table | Backup file | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| MFI interest rates | `euro_mfi_interest_rate_statistics_before_v062_20260811_101729.sql` | 69,572,338 | `6E6786742FEAA4630F0AFEEA602A80772052CAC94BEC6C669C7B1699B5D253BB` |
| National accounts | `euro_main_aggregates_national_accounts_before_v062_20260811_103224.sql` | 363,835,601 | `C8FD086F2B3059757B196EEFB6FAAEB706FEE837B039B7BDB602CDDB4CBAB772` |
| Consumer prices | `euro_indices_consumer_prices_before_v062_20260811_110132.sql` | 270,902,271 | `666E550D4C588CE9AFB25AE03DDE039A447AC964780F4D1976FBF46102727F27` |

The three verified dumps total 704,310,210 bytes. Each contains exactly one
target table with both structure and data.

## Retained Tables and Recovery

The former active tables remain available locally:

- `euro_mfi_interest_rate_statistics__pre_v062_20260811_101729`
- `euro_main_aggregates_national_accounts__pre_v062_20260811_103657`
- `euro_indices_consumer_prices__pre_v062_20260811_110132`

The reviewed rollback statements are:

```sql
RENAME TABLE `euro_mfi_interest_rate_statistics`
  TO `euro_mfi_interest_rate_statistics__failed_v062_20260811_101729`,
  `euro_mfi_interest_rate_statistics__pre_v062_20260811_101729`
  TO `euro_mfi_interest_rate_statistics`;
```

```sql
RENAME TABLE `euro_main_aggregates_national_accounts`
  TO `euro_main_aggregates_national_accou__failed_v062_20260811_103657`,
  `euro_main_aggregates_national_accounts__pre_v062_20260811_103657`
  TO `euro_main_aggregates_national_accounts`;
```

```sql
RENAME TABLE `euro_indices_consumer_prices`
  TO `euro_indices_consumer_prices__failed_v062_20260811_110132`,
  `euro_indices_consumer_prices__pre_v062_20260811_110132`
  TO `euro_indices_consumer_prices`;
```

These statements are recovery documentation, not automatic application code.
They must only be used after a separate failure review and approval.

## Failed Shadow Record

The first national-account build stopped after 17,250 rows because a legacy
`VARCHAR` definition could not preserve a long `data_comp` value. The active
table was never touched. The partial shadow was renamed to
`euro_main_aggregates_national_accou__failed_v062_20260811_103224` and retained
for forensic review. The shadow schema generator now promotes non-key text
dimensions to `TEXT`; the corrected rebuild passed exact validation.

## Independent Evidence

- Global 10,864,513-row post-migration digest:
  `6B0EC4A231ADDA60FB48091E27B9D5BC8E31174D6C8840157EBCF78D6F382F59`
- Deep 17-contract schema-audit digest:
  `45596B651D848205E4761DA2B8157DE089A793B8063D169502E0AD74AFE219B4`
- 17/17 EURO schemas are `write_contract_ready`.
- 16/16 configured EURO series are available.
- 12/12 active EURO/market pairs load and align; four disabled fraud series
  are explicitly skipped.

Local JSON, CSV, SQLite, SQL-dump and audit-output artifacts remain excluded
from the public repository. No retained or failed table was deleted.
