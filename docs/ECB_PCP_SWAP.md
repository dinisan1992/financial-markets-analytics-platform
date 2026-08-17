# Official PCP Atomic Promotion

Version: v0.8.3

Date: 17 August 2026

## Scope

This checkpoint promoted only the separately built, twice-validated and
independently preflighted official Card Payments (`PCP`) shadow. The swap-only
command revalidated the three-report evidence chain, official CSV, scoped SQL
backup, active checkpoint and complete shadow before changing table names.

The atomic operation was:

```sql
RENAME TABLE
  euro_card_payments
    TO euro_card_payments__pre_v079_20260817_115720,
  euro_card_payments__shadow_v079_20260817_115720
    TO euro_card_payments;
```

No table, source row or active CSV was deleted or overwritten. The former
active table is the immediate rollback checkpoint.

## Active Table

| Check | Result |
| --- | --- |
| Rows | 1,081,151 |
| Unique business keys | 1,081,151 |
| Null business keys | 0 |
| First period | `2000` |
| Last period | `2026-Q1` |
| Columns | 35 |
| `time_period` | `VARCHAR(20)` |
| `obs_value` | `DECIMAL(38,12)` |
| Primary key | `(key_code, time_period)` |
| Technical hash column | Removed after validation |
| Data SHA-256 | `8033E4DEDAD046CA3508F4B404BE8B56007B56FD1E5A23B7A312145CD2B737B4` |
| Schema SHA-256 | `D0B500F780A90BA33A9C005D82C180148E8DA82669791302C4E85C5670C9AD37` |

The complete post-swap source audit found zero missing source keys, zero extra
target keys and zero mapped-value hash mismatches.

## Retained Table

The former active table remains intact as:

`euro_card_payments__pre_v079_20260817_115720`

It contains 815,173 rows with data SHA-256
`491E0A03679544679FF7381D4027461C7BBF576F54E08F7C051BAA2EDA82887C`
and schema SHA-256
`A0379A34BB5AFCBD7AA588F6F0C068243920400D0BE81CE1CF1F050CF89C8A8B`.
An independent SELECT-only pass reproduced both fingerprints after the
promotion. No shadow or failed-table artifact remains.

The 6,168 keys withdrawn from the current official snapshot remain available
in this retained table. The promoted active snapshot adds 272,146 current keys
and applies 807,892 reviewed revisions relative to the former active state.

## Signed Evidence

The successful operation reports `swap_performed: true`,
`rollback_performed: false`, `active_csv_write_performed: false` and
`source-to-active valid: true`. Its local report SHA-256 is
`0A6BB320DB9CEA1078B944B5FE9A0AE0B96D3FF5E598D8302ED89DB2D3F938A7`.

The operation was bound to the previously published readiness, build and
independent post-build report hashes. Generated reports, raw sources, backups,
credentials and local paths remain excluded from Git.

## Rollback Contract

The command delayed removal of the technical row hash until after the atomic
rename and promoted-state validation. Any failure before final validation would
have executed an inverse atomic rename restoring the retained table as active.
No rollback was required in the successful run.
