# ECB Backup And Shadow Plan

Version: v0.7.5

Date: 11 August 2026

## Completed Safety Gate

Fresh one-table structure-and-data backups were created for the three active
ECB targets before any shadow build or active-file promotion. `mysqldump` used
`--single-transaction`, `--quick` and `--skip-lock-tables`. Each file was
validated for both `CREATE TABLE` and `INSERT INTO` content, then hashed again
independently.

| Contract | Active rows | Backup bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `EURO_BANK_LENDING_SURVEY` | 1,164,356 | 580,771,710 | `7B34BA6ED3F7FC073B0FF0AC98F6D3E574461BEB84D1F4B07FB00FB9D08585BD` |
| `EURO_CARD_PAYMENTS` | 815,173 | 435,060,511 | `450B7E40A12CD28EB513F93C8CD36AB1B885F3BC94071D9AC90B22BC711670A1` |
| `EURO_BALANCE_SHEET_ITEMS` | 7,812,208 | 5,127,740,638 | `BF48162267E90D3D3FB20F9BD643FEA1A62D43D015B44ED48725941ED1DAAD67` |

Post-backup SELECT-only counts remained identical. The backup manifest SHA-256
is `9BBDF2DF85170ACB265B646FF27B96CCD3417551024E0C1B36CF9177F531CEE4`.

## Read-Only Shadow Plan

A three-contract plan was generated from the live schemas without executing
its SQL. Its SHA-256 is
`40440FB0E73E75C9F864407D6817630E708EDD27EEBBF19C670AC9CA3B1FCA53`.

| Contract | Planned shadow | Planned retained table |
| --- | --- | --- |
| `EURO_BANK_LENDING_SURVEY` | `euro_bank_lending_survey__shadow_v075_20260811_221532` | `euro_bank_lending_survey__pre_v075_20260811_221532` |
| `EURO_CARD_PAYMENTS` | `euro_card_payments__shadow_v075_20260811_221532` | `euro_card_payments__pre_v075_20260811_221532` |
| `EURO_BALANCE_SHEET_ITEMS` | `euro_balance_sheet_items__shadow_v075_20260811_221532` | `euro_balance_sheet_items__pre_v075_20260811_221532` |

Independent schema inspection confirmed that none of the six planned tables
exists. `database_write_performed`, `active_csv_write_performed` and
`statements_executed` are all false.

## Retention Policy

The official current ECB snapshot is authoritative for the future active
table. Keys withdrawn from PCP and BSI will not be merged into the new active
snapshot. They will remain recoverable in the complete versioned retained
table after a future atomic swap.

This policy provides both semantic clarity and reversibility:

- the active table represents the current official ECB universe;
- the retained table preserves every previously stored key and value;
- no historical row is destructively deleted from the retained copy;
- rollback remains one atomic rename away;
- the public repository contains no SQL dump, raw CSV or local path.

## Remaining Authorization Gate

The next phase is intentionally not executed in this checkpoint. It must:

1. revalidate candidate and backup hashes immediately before each build;
2. create one shadow at a time with an exact versioned confirmation;
3. load the complete official snapshot without modifying the active table;
4. compare every mapped column and business key against the candidate;
5. confirm that active-table counts and fingerprints remain unchanged;
6. review the complete shadow evidence before a separately authorized swap.

No shadow build or atomic swap should begin unless enough time is available to
finish that table's load and validation in the same controlled session.
