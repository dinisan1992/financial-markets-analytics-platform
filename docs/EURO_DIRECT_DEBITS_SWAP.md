# EURO Direct Debits Atomic Promotion

Version: v0.7.0

Date: 11 August 2026

## Scope

This checkpoint completed the controlled Direct Debits rebuild. It used a
separately confirmed swap-only command after the backup, source, active table
and complete v0.6.9 shadow had been revalidated.

The atomic operation was:

```sql
RENAME TABLE
  euro_direct_debits
    TO euro_direct_debits__pre_v069_20260811_163215,
  euro_direct_debits__shadow_v069_20260811_163215
    TO euro_direct_debits;
```

No table was deleted. The inverse atomic rename remains documented for
rollback.

## Active Table

| Check | Result |
| --- | --- |
| Rows | 121,564 |
| Unique business keys | 121,564 |
| Null business keys | 0 |
| Columns | 31 |
| `time_period` | `VARCHAR(20)` |
| Primary key | `(key_code, time_period)` |
| Helper hash column | Removed after validation |
| Data SHA-256 | `F291BD9ED9B7A895FB3A23F6DB30B890984C5DC4B3ADCCE56982DE8B70826844` |
| Schema SHA-256 | `1C635CC43683C5001FACFC451454AA210AC1623BC5B9D106F3337B853616399C` |

Frequency preservation remains exact:

| Frequency | Rows |
| --- | ---: |
| Annual (`A`) | 44,539 |
| Semiannual (`H`) | 42,039 |
| Quarterly (`Q`) | 34,986 |

## Retained Table

The former active table remains available as:

`euro_direct_debits__pre_v069_20260811_163215`

It still has 75,647 rows, the v0.6.8 data SHA-256
`5BDAB01AFCF91D83161657736E94A0853B280FC946168008571233657EDD2907`
and schema SHA-256
`6E6237FA71CBAF7603782A694107C0B9352D843E13B0258F6F42A32DBEB0F768`.
No failed-table artifact exists because rollback was not required.

## Post-Swap Validation

The immediate synchronization plan reported:

- 121,564 source rows and 121,564 target rows;
- 121,564 unchanged rows;
- zero inserts and zero updates;
- zero target-only rows and zero deletes;
- zero null, duplicate or invalid numeric keys;
- zero blockers;
- `write_ready: true` and `idempotent: true`.

The post-swap schema audit classifies all 17 EURO contracts as
`write_contract_ready`, with 16/16 configured EURO series available. The 38
market calculations, nine Streamlit pages and application health check also
passed.

The local atomic-swap report SHA-256 is
`705D5A020A4F6DB6A9DF59740284BBB6B4668BFAD4332E0CBB8EB7C8F6B87999`.
The post-swap sync report SHA-256 is
`6857279B7211FFE2933F1FFA020C0EEC9C369EA44D15FE2596C663A51EB4E26E`.
The schema-audit JSON SHA-256 is
`CF0A0CA9F0E36E9583F6B74D53641C6D655D342CF942B65BB2D26548F8A73447`.
Generated reports and private paths remain excluded from Git.

## Reusable Command

```powershell
python project_scripts/diagnostics/swap_euro_direct_debits.py `
  --backup-file "<verified-v068-backup.sql>" `
  --confirm SWAP_EURO_DIRECT_DEBITS_V070_ACTIVE `
  --suffix 20260811_163215 `
  --workspace-dir "<local-workspace>"
```

The command refuses changed inputs, an invalid active checkpoint, a missing or
invalid shadow, existing retained/failed names or an incorrect confirmation.
Any validation failure after the first rename executes the inverse atomic
rename before raising the error.
