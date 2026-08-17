# Government Finance Readiness

Status: discovery complete, blocked before backup

Date: 17 August 2026

## Official Source

The ECB Data Portal identifies Government Finance Statistics as dataflow
`GFS`. Version v0.8.9 records that identity in the import manifest and exposes
the reproducible API URL:

`https://data-api.ecb.europa.eu/service/data/GFS?format=csvdata`

The local 4,279,231,531-byte CSV has SHA-256
`4CD8F612FD47633CC31676CC319416FDBD6D41DEA318E4891E194CFA4EFD90A4`
and was last modified in October 2025. The official portal reports a later
dataset update, so this file must not be treated as a fresh migration candidate.
No download or CSV replacement was performed during this review.

## Current Baseline

The signed read-only synchronization report SHA-256 is
`1B7780FAD3DC001A912D58F01EE961B0439807EF9AFC89E2CC5A4F256C94B7BC`.
It records:

| Measure | Rows |
| --- | ---: |
| Reviewed source | 6,086,437 |
| Current target | 2,263,500 |
| Source-only inserts | 3,822,937 |
| Changed shared rows | 28,799 |
| Target-only rows | 0 |

The current InnoDB table contains the expected 2,263,500 rows, occupies
2,148,106,240 bytes, uses primary key `id` and enforces a unique
`key_code + time_period` business index.

## Capacity

Scaling the current footprint to the reviewed source cardinality and applying
a conservative 1.25 safety factor estimates a 6.724 GiB shadow. Adding the
standard 5 GiB operating reserve requires about 11.724 GiB free. Approximately
14.039 GiB was available during discovery, leaving only 2.315 GiB margin.

This is indicative, not a build authorization. Free space and candidate size
must be recalculated from the fresh snapshot immediately before construction.

## Required Sequence

1. Download the official `GFS` snapshot into external staging without replacing
   the active CSV.
2. Validate headers, bytes, SHA-256, unique keys, null keys and numeric values.
3. Run a fresh complete source-to-target audit.
4. Create and verify a scoped structure-and-data backup on a separate volume.
5. Repeat the capacity preflight with the fresh source cardinality.
6. Prepare a Government Finance-only shadow builder with a separate exact
   authorization boundary.

No database write, CSV write, download, backup, shadow build or promotion was
performed during this discovery checkpoint.
