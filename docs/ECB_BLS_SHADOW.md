# Official BLS Shadow Build

Version: v0.8.0

Date: 17 August 2026

## Authorized Scope

The authorized operation was limited to creating and validating the official
Bank Lending Survey shadow. It did not authorize an atomic swap, active CSV
promotion or modification of the active BLS table.

The build command is restricted to `EURO_BANK_LENDING_SURVEY`, requires the
exact `BUILD_EURO_BANK_LENDING_SURVEY_V079_SHADOW` confirmation and is bound to
the SHA-256-pinned v0.7.9 readiness report. It has no swap option.

## Built Shadow

| Field | Result |
| --- | --- |
| Shadow table | `euro_bank_lending_survey__shadow_v079_20260817_115720` |
| Official source rows | 1,225,110 |
| Shadow rows | 1,225,110 |
| Unique business keys | 1,225,110 |
| Null business keys | 0 |
| Duplicate business-key groups | 0 |
| Non-null observations | 830,090 |
| First period | `2003-Q1` |
| Last period | `2026-Q3` |
| Source-hash mismatches | 0 |
| Missing source rows | 0 |

The loader used a bounded external SQLite fingerprint store and never replaced
the configured active CSV.

## Signed-Zero Finding

The first post-storage validation found one technical row-hash mismatch for:

- key: `BLS.Q.FR.ALL.SME.E.Z.B3.ZZ.D.DINX`;
- period: `2020-Q2`;
- CSV observation: `-0E-12`;
- MySQL observation: `0E-12`.

These values are financially and numerically equivalent. The canonical hash
previously normalized signed zero only when target type metadata was supplied.
The shared normalization now treats signed decimal zero as zero in both typed
and untyped paths.

After proving that every mapped value was canonically equivalent, a guarded
update changed exactly one `_source_row_sha256` value in the shadow. It did not
change `obs_value` or any published financial field. A final targeted read
confirmed identical source, stored and recomputed hashes with no differences.

## Complete Validation

Two complete source-to-shadow validations were executed after the hash repair.
Both independently reported:

- 1,225,110 source and shadow rows;
- 1,225,110 unique source and shadow keys;
- zero missing or extra rows;
- zero row-hash or source-hash mismatches;
- zero null or duplicate business keys;
- `valid: true`.

The local validation report SHA-256 is
`402AD291D54DB561933A47572245A2CE1F4A32DAB7EF409CD6C12CF9B424D81F`.
The report remains under an ignored audit-output path and is not published with
raw source data or local filesystem paths.

## Active-Table Proof

The complete active BLS data and schema were fingerprinted immediately before
the guarded hash repair and again after both full shadow validations.

| Checkpoint | Before | After |
| --- | --- | --- |
| Active rows | 1,164,356 | 1,164,356 |
| Data SHA-256 | `CFE1767294A0E345483AFF7AA8C885B8D5D829677BD58B5DB3A73A8866E7FD5D` | `CFE1767294A0E345483AFF7AA8C885B8D5D829677BD58B5DB3A73A8866E7FD5D` |
| Schema SHA-256 | `C9F5D7AB529D7FC814496188A2A40DD71A944516D829015255AADDAEE1565E8D` | `C9F5D7AB529D7FC814496188A2A40DD71A944516D829015255AADDAEE1565E8D` |

The shadow schema SHA-256 is
`D0154552E6C09D2616C6C056A8CAEAFF1E1A8D7A517D8A133B075CB55622DB93`.
Its composite business key remains the primary key and its technical source
hash column remains present for pre-promotion review.

## Remaining Authorization Gate

The shadow is ready for swap review, but promotion has not been authorized or
performed. A future atomic operation must:

1. revalidate the official candidate, backup and complete shadow again;
2. confirm the active data/schema fingerprints above;
3. rename the current active table to the planned versioned retained name;
4. promote the validated shadow atomically;
5. validate the promoted table before removing any technical hash column;
6. roll back atomically on any failed post-swap check.

The former active table must remain intact under its retained name so rollback
does not depend on reimporting a SQL dump.
