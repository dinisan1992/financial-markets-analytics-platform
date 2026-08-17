# Official BSI Shadow Build

Version: v0.8.4

Date: 17 August 2026

## Authorized Scope

The authorized operation was limited to creating and validating the official
Balance Sheet Items (`BSI`) shadow. The command accepted only
`EURO_BALANCE_SHEET_ITEMS`, required the exact
`BUILD_EURO_BALANCE_SHEET_ITEMS_V079_SHADOW` confirmation and exposed no swap
or active-table promotion mode.

The signed readiness report, official CSV, scoped SQL backup, current active
checkpoint, future table names and storage capacity were revalidated before
the first database write. Failure cleanup was restricted to the exact newly
generated shadow name and required a fresh active-table checkpoint.

## Built Shadow

| Field | Result |
| --- | --- |
| Shadow table | `euro_balance_sheet_items__shadow_v079_20260817_141854` |
| Official source rows | 8,055,309 |
| Shadow rows | 8,055,309 |
| Unique business keys | 8,055,309 |
| Null business keys | 0 |
| Duplicate business-key groups | 0 |
| Non-null observations | 7,217,199 |
| First period | `1980-01` |
| Last period | `2026-Q2` |
| Row-hash mismatches | 0 |
| Source-hash mismatches | 0 |
| Missing source rows | 0 |
| Technical hash column | Present for review |
| Shadow schema SHA-256 | `35F99BD6C0ECE9FAEE233FFCD234B00C5CF6099A80A1966AC2D15E7628C51F95` |

Two complete build validations and a third separately executed SELECT-only
verification reproduced every source business key and mapped value. The
disk-backed comparison store used 1,552,138,240 bytes.

## Active-Table Proof

| Check | Result |
| --- | --- |
| Active table | `euro_balance_sheet_items` |
| Active rows | 7,812,208 |
| Data SHA-256 | `D8DB709C3DD8C9F67A119E7375D208FA91EAAF86786A1BB9F4DECE471D78D22A` |
| Schema SHA-256 | `3EA9698143D0269BE8C35D880F88666254D98A5D4998F57C1CD93F3CC94C75FA` |
| Active table changed | No |
| Active CSV changed | No |
| Retained/failed table created | No |
| Swap authorized or performed | No |

The 344,327 active-only keys remain in the unchanged active table. Applying the
official-snapshot-authoritative retention policy requires a future separately
reviewed and authorized atomic promotion.

## Signed Evidence

The SELECT-only readiness report SHA-256 is
`D9145086C967C09D7D9D910C0AED5FB08E028C7C784D23538D8893F43803FBEF`.
The local build report SHA-256 is
`F3D9C448D68781630B666272F940E020398C1F194EFCC7001DE3F0D8BA19DEE6`.
The independent post-build verification SHA-256 is
`D9F1EB83336C617EC32B8E7B3AAB5E25E1DC22AF66D8B6BBD1DAA99E0E2577EB`.

Generated reports remain under ignored audit-output paths. Raw ECB data, SQL
backups, credentials and absolute local paths are not published.

## Operational Note

The build and verification completed successfully, but host telemetry observed
transient Python working-set peaks of approximately 14.2 GB and 12.8 GB during
the large comparisons. Version v0.8.5 traced those peaks to the SQLAlchemy
mysqlconnector result path in disk-backed shadow validation and replaced it
with an explicit `buffered=False` DBAPI cursor capped at 5,000 rows per fetch.
The SQLAlchemy fallback is also bounded and closed deterministically. Unit
tests cover both paths; no further production-scale BSI scan or database write
was performed for this optimization checkpoint.

## Remaining Authorization Gate

The shadow is ready for review but promotion has not been authorized or
performed. A future BSI-only swap checkpoint must revalidate the complete
signed evidence chain, retain the former active table under its versioned name,
validate the promoted official snapshot and automatically reverse the atomic
rename after any post-swap failure.
