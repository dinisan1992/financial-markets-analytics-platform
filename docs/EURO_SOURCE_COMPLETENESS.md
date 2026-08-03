# EURO Source Completeness

Version: v0.5.6

Audit date: 3 August 2026

## Purpose

Schema safety alone does not prove that a SQL table contains the complete CSV
history. This audit scanned every registered row in the six EURO sources that
remained unresolved after v0.5.5 and compared source business-key cardinality
with the active MySQL tables.

No database write was performed during the completeness audit.

## Full-Source Findings

| Import | Source rows | SQL rows before v0.5.6 | Missing from SQL | Decision |
| --- | ---: | ---: | ---: | --- |
| Consumer prices | 6,548,663 | 675,500 | 5,873,163 | Controlled rebuild |
| Fraud losses | 198 | 198 | 0 | Exact rebuild completed |
| National accounts | 2,721,359 | 617,500 | 2,103,859 | Controlled rebuild |
| MFI interest rates | 1,594,491 | 96,000 | 1,498,491 | Controlled rebuild |
| Retail interest rates | 8,798 | 8,798 | 0 | Exact rebuild completed |
| Payment-system transactions | 103,563 | 103,563 | 0 | Exact rebuild completed |

The three incomplete SQL tables are missing 9,475,513 registered source
observations in total. Adding a composite key to those tables would preserve
an incomplete history and incorrectly present the schemas as ready.

## Stored-Value Findings

Matching row counts and keys were not treated as sufficient evidence. A
canonical SHA-256 comparison across every mapped column found:

- 198/198 divergent fraud-loss rows;
- 7,038/8,798 divergent retail-interest-rate rows;
- 2,479/103,563 divergent payment-system rows.

The former tables rounded `obs_value` to ten decimal places. Some legacy text
columns were also truncated, and the original fraud import replaced commas in
descriptive fields. The v0.5.6 rebuild therefore uses `DECIMAL(38,12)`, `TEXT`
for long descriptions and the source `(key_code, time_period)` as the primary
key.

## v0.5.6 Migration Result

The three source-complete tables were rebuilt through isolated shadows and one
atomic swap. The active tables now contain 112,559 source observations and
report:

- zero missing source rows;
- zero extra SQL rows;
- zero full-row hash mismatches;
- zero null or duplicate business keys;
- a textual `time_period` column;
- a composite `(key_code, time_period)` primary key.

The verified pre-migration backup contains 48,858,895 bytes and has SHA-256:

`151A959D5DFC7FD171C09666EFE5C04E3C05EB1C2F5FD32ADA814950D6A7A736`

Local report digests:

- shadow build: `8A952DA68E5633B7E2BC7F70EE1F83DF1243F937220402AE61DD930AD6A48ABA`;
- atomic swap: `7D3C978D547FD3FDDF339DAF4A778A6B48A1B20D708F9FEDBEF7FF50D5F5242A`;
- post-migration audit: `5E3D9E5FFAEAA5A13E1D781415D495610D467644A76F0E7B50E13E6DB15B84C6`.

The backup and reports remain local under `audit_outputs/` and are excluded
from Git. The former tables remain in MySQL under `pre_v056` names.

## Capacity Review for the Remaining Tables

At the review point, drive C had 19.25 GB free and the MySQL database occupied
approximately 11.11 GB. The registered CSVs occupy approximately 4.03 GB.
Current-table density gives these rough full-table estimates:

| Table | Estimated full SQL size |
| --- | ---: |
| Consumer prices | 2.19 GB |
| National accounts | 1.29 GB |
| MFI interest rates | 1.08 GB |
| **Total** | **4.56 GB** |

Disk capacity is not the only constraint. The current exact validator retains
millions of Python hash objects and copies that dictionary during comparison.
That is not acceptably memory-bounded for a 6.5-million-row source.

## Next Safe Migration

Before rebuilding the remaining tables:

1. Replace the in-memory fingerprint dictionary with a streaming or SQL-backed
   comparison that has bounded memory.
2. Process one source table at a time.
3. Create and verify a table-scoped structure-and-data backup.
4. Estimate free disk before each shadow build and preserve an operating
   reserve for MySQL temporary and redo data.
5. Validate source/shadow rows, keys, non-null values and full-row signatures.
6. Swap only the validated table and retain its original for rollback.
7. Re-run the global EURO audit and all application checks after each table.

No large rebuild is authorized merely by this capacity estimate.
