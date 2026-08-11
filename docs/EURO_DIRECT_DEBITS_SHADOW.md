# EURO Direct Debits Validated Shadow

Version: v0.6.9

Date: 11 August 2026

## Scope

This checkpoint created and populated one non-active MySQL table:

`euro_direct_debits__shadow_v069_20260811_163215`

The command had no swap stage. It did not rename, update, delete or replace the
active `euro_direct_debits` table.

## Pinned Inputs

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Reviewed Direct Debits CSV | 32,010,024 | `D8B5273ED4184E0733A0F2C629263F2077187A0BD75C85BAB7856E9C8E5FDB6B` |
| Verified v0.6.8 SQL backup | 25,308,899 | `724F9B20F7A7A651395FDBC689D99E23B324F96329EC6E629BC60F616682852E` |

Before writing, the build also required the active table to match the verified
75,647-row data fingerprint and 31-column schema fingerprint recorded in
v0.6.8. Any difference blocks the build.

## Shadow Evidence

| Check | Result |
| --- | --- |
| Rows | 121,564 |
| Unique `(key_code, time_period)` keys | 121,564 |
| Null business keys | 0 |
| Duplicate key groups | 0 |
| Non-null observations | 92,468 |
| Period range | `2000` to `2025-Q2` |
| `time_period` type | `VARCHAR(20)` |
| Primary key | `(key_code, time_period)` |
| Source hash column | Present until any separately authorized swap |

The preserved frequency distribution is:

| Frequency | Rows |
| --- | ---: |
| Annual (`A`) | 44,539 |
| Semiannual (`H`) | 42,039 |
| Quarterly (`Q`) | 34,986 |

The disk-backed build comparison and a second independent read-only comparison
both reported:

- zero row-hash mismatches;
- zero source-hash mismatches;
- zero source rows missing from the shadow;
- zero extra shadow rows;
- zero null or duplicate business keys.

## Active Table Evidence

The active table was fingerprinted before and after the shadow build:

| Check | Before | After |
| --- | --- | --- |
| Rows | 75,647 | 75,647 |
| Data SHA-256 | `5BDAB01AFCF91D83161657736E94A0853B280FC946168008571233657EDD2907` | same |
| Schema SHA-256 | `6E6237FA71CBAF7603782A694107C0B9352D843E13B0258F6F42A32DBEB0F768` | same |
| `time_period` | `YEAR(4)` | `YEAR(4)` |

The local build report SHA-256 is
`42F8A4EE978BFB45174C1DF96669EA18CF97657E54173CCD975C40E01CB031F7`.
Generated reports remain under Git-ignored `audit_outputs/` and private paths
are not published.

## Reusable Build Command

```powershell
python project_scripts/diagnostics/build_euro_direct_debits_shadow.py `
  --backup-file "<verified-v068-backup.sql>" `
  --confirm BUILD_EURO_DIRECT_DEBITS_V069_SHADOW `
  --suffix YYYYMMDD_HHMMSS `
  --workspace-dir "<local-workspace>"
```

This command performs a database write to the versioned shadow only. It refuses
a changed backup, changed source, changed active checkpoint, existing shadow or
incorrect confirmation. It exposes no swap option.

## Next Gate

The shadow is ready for review, not promotion. A future atomic swap would retain
the current table under a versioned rollback name, remove the temporary hash
column from the validated shadow and rename both tables atomically. That action
has not been authorized or executed and must be followed immediately by
read-only synchronization and application validation.
