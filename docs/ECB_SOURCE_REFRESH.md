# Official ECB Source Refresh

Version: v0.7.4

Date: 11 August 2026

## Scope

This checkpoint establishes a reproducible, non-destructive refresh path for
three production-scale ECB Data Portal datasets:

| Import contract | ECB dataflow | Active rows | Candidate rows | Candidate latest period |
| --- | --- | ---: | ---: | --- |
| `EURO_BANK_LENDING_SURVEY` | `BLS` | 1,164,356 | 1,225,110 | 2026-Q3 |
| `EURO_CARD_PAYMENTS` | `PCP` | 815,173 | 1,081,151 | 2026-Q1 |
| `EURO_BALANCE_SHEET_ITEMS` | `BSI` | 7,812,208 | 8,055,309 | 2026-Q2 |

The dataflows and complete CSV endpoints are recorded in
`macro_import_manifest.py`. The implementation follows the official
[ECB Data API](https://data.ecb.europa.eu/help/api/data) and
[bulk-download guidance](https://data.ecb.europa.eu/help/bulk-download).

## Safety Model

`project_scripts/ingestion/refresh_ecb_sources.py` has three deliberate
properties:

- normal execution probes one existing series per dataset and downloads nothing;
- `--download` writes only to an explicit staging directory through a
  `.partial` file and validates the complete CSV header before atomic rename;
- the command has no active-CSV promotion and no SQL write mode.

Every result records both `database_write_performed: false` and
`active_csv_write_performed: false`. Downloads are hashed with SHA-256. Full
candidate validation uses a temporary disk-backed business-key index, so it
does not retain millions of keys in memory.

## Reproducible Commands

Probe the three configured dataflows:

```powershell
python project_scripts/ingestion/refresh_ecb_sources.py
```

Download complete snapshots into an external staging directory:

```powershell
python project_scripts/ingestion/refresh_ecb_sources.py `
  --download `
  --staging-dir "X:\ECB_SOURCE_STAGING"
```

Compare staged snapshots with the active CSVs without SQL access:

```powershell
python project_scripts/ingestion/refresh_ecb_sources.py `
  --compare `
  --staging-dir "X:\ECB_SOURCE_STAGING" `
  --workspace-dir "X:\ECB_SOURCE_STAGING"
```

The established streaming auditor can then compare those files with MySQL by
overriding `EURO_SOURCE_DIR` for that process. The auditor issues SELECT
statements only.

## Staged Snapshot Evidence

| Dataflow | Bytes | SHA-256 |
| --- | ---: | --- |
| `BLS` | 539,897,497 | `FF159B22C942D9D54212A2B8BFD08572B48540E92255825F50457B7CB089C0A7` |
| `PCP` | 396,345,008 | `F329805F2A745F228CFF275CE37361E5A2C84C1BD5232E17E4DC217B589F5EC5` |
| `BSI` | 4,456,898,809 | `88C5E1DAF3E9D148A6BCC606CA24B4666328343794A3FD0BEEE40B877ED5DB56` |

All three candidates have:

- the same column order as their registered active CSV;
- zero null business keys;
- zero invalid numeric observations;
- zero duplicate business-key groups;
- zero duplicate hash conflicts;
- source period formats compatible with the active SQL schema.

## Read-Only MySQL Plan

| Contract | Candidate | MySQL target | Candidate-only | Target-only | Row mismatches |
| --- | ---: | ---: | ---: | ---: | ---: |
| `EURO_BANK_LENDING_SURVEY` | 1,225,110 | 1,164,356 | 60,754 | 0 | 3,194 |
| `EURO_CARD_PAYMENTS` | 1,081,151 | 815,173 | 272,146 | 6,168 | 807,892 |
| `EURO_BALANCE_SHEET_ITEMS` | 8,055,309 | 7,812,208 | 587,428 | 344,327 | 7,388,215 |

The complete report SHA-256 is
`9B073F15974845080AFAB949052820B6438BCBC1F1E8EF2BAEFDA9A2513F336D`.
No database writes were performed.

## Interpretation

These are not simple append-only updates. Deterministic mismatch samples show:

- `BLS` contains revised observation values, including 2025-Q3 values;
- `PCP` contains broad `title` and `title_compl` rewrites, storage-precision
  differences and some substantive observation revisions;
- `BSI` contains broad title rewrites, storage-precision differences and
  substantive historical observation revisions;
- the ECB candidate no longer contains 6,168 current PCP keys and 344,327
  current BSI keys, consistent with source-series withdrawal or reclassification
  that requires explicit retention policy review.

The sampled field analysis is diagnostic evidence, not an estimate of the
exact number of value revisions across every mismatch.

## Decision And Next Gate

The candidates are structurally valid and approved for further read-only
planning only. They have not replaced the active CSVs and have not changed
MySQL.

Before any data write:

1. create fresh scoped structure-and-data SQL backups on a separate physical
   volume;
2. retain the current active tables under versioned rollback names;
3. use a complete shadow rebuild for PCP and BSI because target-only keys make
   ordinary upsert non-idempotent;
4. decide whether BLS should use transactional synchronization or the same
   shadow-rebuild pattern;
5. validate every candidate row against each shadow, then review the planned
   atomic swap;
6. request explicit authorization before executing any SQL write or replacing
   an active CSV.
