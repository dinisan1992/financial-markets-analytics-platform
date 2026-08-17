# Official BSI Shadow Readiness

Status: ready for separate shadow-build authorization

Date: 17 August 2026

## Scope

This checkpoint is restricted to `EURO_BALANCE_SHEET_ITEMS` (`BSI`). It
revalidates the official staged snapshot, scoped SQL backup, current active
table, future table names and storage capacity. No shadow, retained or failed
table was created, and no active CSV or MySQL row was changed.

The current build command accepts BSI only. BLS and PCP are rejected targets,
and the command exposes no swap or promotion mode. Its only cleanup path is an
automatic failure handler restricted to the exact generated shadow name.

## Pinned Inputs

| Evidence | Result |
| --- | --- |
| Official CSV | `Balance Sheet Items.csv` |
| CSV bytes | 4,456,898,809 |
| CSV SHA-256 | `88C5E1DAF3E9D148A6BCC606CA24B4666328343794A3FD0BEEE40B877ED5DB56` |
| Scoped backup | `euro_balance_sheet_items_before_v068_20260811_220956.sql` |
| Backup bytes | 5,127,740,638 |
| Backup SHA-256 | `BF48162267E90D3D3FB20F9BD643FEA1A62D43D015B44ED48725941ED1DAAD67` |
| Pin-manifest SHA-256 | `40440FB0E73E75C9F864407D6817630E708EDD27EEBBF19C670AC9CA3B1FCA53` |

Names, sizes and hashes were recalculated immediately before this readiness
checkpoint.

## Source And Active State

| Check | Official source | Current active |
| --- | ---: | ---: |
| Rows | 8,055,309 | 7,812,208 |
| Unique business keys | 8,055,309 | 7,812,208 |
| Null business keys | 0 | 0 |
| Duplicate business-key groups | 0 | 0 |
| First period | `1980-01` | retained in audit evidence |
| Last source period | `2026-Q2` | retained in audit evidence |

The complete source-to-active audit classifies 587,428 official-source-only
keys, 344,327 active-only keys and 7,388,215 reviewed mapped-value revisions.
These differences are expected under the official-snapshot-authoritative
policy; they are not merged into the current active table in place.

The live active table still has 7,812,208 rows, a composite
`(key_code, time_period)` primary key, `VARCHAR(20)` periods and
`DECIMAL(20,6)` observations.

## Planned Tables

| Role | Name | Exists |
| --- | --- | --- |
| Shadow | `euro_balance_sheet_items__shadow_v079_20260817_141854` | No |
| Future retained | `euro_balance_sheet_items__pre_v079_20260817_141854` | No |
| Automatic-failure slot | `euro_balance_sheet_items__failed_v079_20260817_141854` | No |

The shadow build requires the exact
`BUILD_EURO_BALANCE_SHEET_ITEMS_V079_SHADOW` confirmation. That confirmation
authorizes only creation and complete validation of the versioned shadow. It
does not authorize promotion.

## Capacity

| Check | Bytes |
| --- | ---: |
| Current MySQL free space | 19,437,838,336 |
| MySQL required including reserve | 15,239,010,464 |
| Remaining modeled margin | 4,198,827,872 |
| Validation-workspace free space | 371,521,888,256 |
| Validation-workspace required | 6,897,639,424 |

The capacity gate passes with a 5 GiB operating reserve, but the MySQL margin
is materially smaller than for BLS or PCP. Free space and future table-name
availability must be checked again by the build command immediately before its
first database write.

## Build Contract

If separately authorized, the builder will:

1. Reverify the readiness report, pin manifest, source, backup, audit evidence,
   active row/schema checkpoint, future names and capacity.
2. Create only the versioned BSI shadow.
3. Stream the 8,055,309 official rows in bounded batches.
4. Validate every business key and mapped value against the source.
5. Repeat that complete validation independently.
6. Recompute the active checkpoint and fail if the active table changed.
7. If any build or validation step fails, drop only the exact generated
   partial shadow and recompute the active checkpoint before surfacing the
   failure.
8. Emit a signed ignored local report with `swap_authorized: false` and
   `swap_performed: false`.

No promotion is bundled with this operation. The active-only keys remain in
the unchanged active table unless a later, separately reviewed atomic
promotion is authorized.

## Signed Readiness

The SELECT-only readiness report SHA-256 is
`D9145086C967C09D7D9D910C0AED5FB08E028C7C784D23538D8893F43803FBEF`.
It records zero SQL writes, zero active-CSV writes, zero executed statements,
zero errors and no blockers. Raw reports and machine-specific paths remain
excluded from Git.
