# ECB Rollback Retention Review

Status: completed, read-only and retain-only

Date: 17 August 2026

## Scope

Version v0.8.8 reviews the rollback checkpoints retained after the separately
authorized BLS, PCP and BSI atomic promotions. The command is restricted to
`SELECT COUNT(*)`, schema inspection and `information_schema` metadata. It has
no confirmation, deletion, rename, cleanup or database-write mode.

## Evidence

| Contract | Active rows | Retained rows | Retained size |
| --- | ---: | ---: | ---: |
| Bank Lending Survey | 1,225,110 | 1,164,356 | 0.546 GiB |
| Card Payments | 1,081,151 | 815,173 | 0.764 GiB |
| Balance Sheet Items | 8,055,309 | 7,812,208 | 5.943 GiB |

All six row counts match their signed promotion checkpoints. Every retained
table uses the `key_code + time_period` composite primary key, contains no
technical source hash and has no sibling shadow or failed-table artifact.
Together the retained tables occupy 7,787,757,568 bytes, approximately
7.25 GiB, according to current MySQL table metadata.

The ignored local report SHA-256 is
`400AFDA3369BE6FC19D8696525F1C588A903CABF0719D02220B0A86F143571C0`.

## Decision

Retain all three checkpoints. They provide immediate in-database rollback for
the official ECB snapshot promotions. A future deletion review should require,
at minimum:

1. a newer verified structure-and-data backup on a separate physical volume;
2. an adequate observation window with the promoted tables active;
3. a fresh read-only integrity review;
4. explicit authorization dedicated to the exact tables being removed.

This review does not authorize deletion and no table or CSV was changed.

## Limitations

The lightweight review recomputes exact row counts and schema signatures but
does not repeat full multi-million-row data fingerprints. The signed promotion
reports remain the content-integrity baseline. This distinction prevents a
quick storage review from being misrepresented as a new full data audit.
