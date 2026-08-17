# ECB Shadow Readiness

Version: v0.7.9

Date: 17 August 2026

Status update: BLS was subsequently built, validated and promoted through its
separate atomic checkpoint. PCP was then built and twice validated in an
isolated shadow without promotion. See `docs/ECB_BLS_SWAP.md` and
`docs/ECB_PCP_SHADOW.md`.

## Scope And Safety

This checkpoint revalidates the official staged Bank Lending Survey (`BLS`),
Card Payments (`PCP`) and Balance Sheet Items (`BSI`) snapshots before any
database build. The workflow is deliberately read-only:

- the active CSV files were not replaced;
- no shadow or retained table was created;
- no SQL statement from a generated preview was executed;
- the live database was accessed through SELECT-only inspection;
- every report records database and active-CSV writes as false.

The readiness command has no build, apply, promote or swap option.

## Pinned Inputs

The staged candidates were independently hashed immediately before planning.

| Contract | Candidate bytes | Candidate SHA-256 |
| --- | ---: | --- |
| `EURO_BANK_LENDING_SURVEY` | 539,897,497 | `FF159B22C942D9D54212A2B8BFD08572B48540E92255825F50457B7CB089C0A7` |
| `EURO_CARD_PAYMENTS` | 396,345,008 | `F329805F2A745F228CFF275CE37361E5A2C84C1BD5232E17E4DC217B589F5EC5` |
| `EURO_BALANCE_SHEET_ITEMS` | 4,456,898,809 | `88C5E1DAF3E9D148A6BCC606CA24B4666328343794A3FD0BEEE40B877ED5DB56` |

The separately stored structure-and-data backups were also revalidated.

| Contract | Backup bytes | Backup SHA-256 |
| --- | ---: | --- |
| `EURO_BANK_LENDING_SURVEY` | 580,771,710 | `7B34BA6ED3F7FC073B0FF0AC98F6D3E574461BEB84D1F4B07FB00FB9D08585BD` |
| `EURO_CARD_PAYMENTS` | 435,060,511 | `450B7E40A12CD28EB513F93C8CD36AB1B885F3BC94071D9AC90B22BC711670A1` |
| `EURO_BALANCE_SHEET_ITEMS` | 5,127,740,638 | `BF48162267E90D3D3FB20F9BD643FEA1A62D43D015B44ED48725941ED1DAAD67` |

## Fresh Complete Audit

The memory-bounded auditor read the external candidates and compared every
business key and mapped value with the active MySQL targets.

| Contract | Source rows | Active rows | Candidate-only | Active-only | Mismatched |
| --- | ---: | ---: | ---: | ---: | ---: |
| `EURO_BANK_LENDING_SURVEY` | 1,225,110 | 1,164,356 | 60,754 | 0 | 3,194 |
| `EURO_CARD_PAYMENTS` | 1,081,151 | 815,173 | 272,146 | 6,168 | 807,892 |
| `EURO_BALANCE_SHEET_ITEMS` | 8,055,309 | 7,812,208 | 587,428 | 344,327 | 7,388,215 |

These results reproduce the reviewed 11 August classification. The audit
summary SHA-256 is
`B7185ADC0D4F0638B814F5DF0F529DCCF1201858A7845C02711B78394B5FB3F4`.

The official current snapshot remains authoritative. The 6,168 PCP and
344,327 BSI active-only keys will remain available in the complete retained
table after a future promotion rather than being merged into the new active
official universe.

## Capacity And Name Gates

The planner applies a 1.5 storage safety factor and preserves a 5 GiB database
operating reserve.

| Contract | Estimated shadow size | Database volume free | External workspace free | Ready |
| --- | ---: | ---: | ---: | --- |
| `EURO_BANK_LENDING_SURVEY` | 0.86 GiB | 20.33 GiB | 346.01 GiB | Yes |
| `EURO_CARD_PAYMENTS` | 1.52 GiB | 20.33 GiB | 346.01 GiB | Yes |
| `EURO_BALANCE_SHEET_ITEMS` | 9.19 GiB | 20.33 GiB | 346.01 GiB | Yes |

All six planned shadow and retained-table names were confirmed absent. The
readiness report SHA-256 is
`2F12A83243887974B327E81563DEE526CA7CFFC868E6AFB44AC1015A8AFD0A01`.

## Reproduction

First create a fresh audit from the external staging directory:

```powershell
python project_scripts/diagnostics/audit_euro_streaming_completeness.py `
  EURO_BANK_LENDING_SURVEY EURO_CARD_PAYMENTS EURO_BALANCE_SHEET_ITEMS `
  --source-dir <external-staging-directory> `
  --workspace-dir <external-workspace-directory> `
  --output-dir <fresh-audit-directory> `
  --sample-strategy hash
```

Then generate the readiness evidence:

```powershell
python project_scripts/diagnostics/plan_ecb_shadow_refresh.py `
  --staging-dir <external-staging-directory> `
  --backup-dir <external-backup-directory> `
  --audit-dir <fresh-audit-directory> `
  --workspace-dir <external-workspace-directory> `
  --pin-file <reviewed-shadow-plan.json> `
  --output-dir <readiness-output-directory>
```

Generated audit evidence remains local under ignored output paths. Raw ECB
files, SQL dumps, credentials and absolute local paths are not published.

## Next Authorization Gate

BLS and PCP completed their separately authorized builds; BLS was later
promoted and PCP remains an isolated validated shadow. The next gates are:

1. review PCP and require separate authorization before any promotion;
2. build and completely validate BSI under its own authorization;
3. review BSI before any later promotion.

Each build and promotion remains a distinct database write with a separate
explicit authorization.
