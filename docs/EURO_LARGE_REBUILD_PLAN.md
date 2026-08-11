# Large EURO Rebuild Plan

Runbook version: v0.6.3

Date: 11 August 2026

## Scope

This runbook covers the three EURO source contracts whose registered CSV
history is substantially larger than the current MySQL tables:

1. `EURO_MFI_INTEREST_RATES`
2. `EURO_NATIONAL_ACCOUNTS`
3. `EURO_CONSUMER_PRICES`

Only one table may be processed per command. Build and swap are separate
operations with different import-specific confirmations. A successful build
creates and validates a shadow but does not change the active table.

## Read-Only Capacity Baseline

All preflights used a 5 GiB operating reserve. The backup is excluded from the
estimate and must be placed on a separate physical volume.

| Import | Source rows | Active bytes | Estimated shadow bytes | Store peak bytes | Combined required bytes | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| MFI interest rates | 1,594,491 | 69,861,376 | 1,160,347,243 | 154,017,792 | 6,683,074,155 | Pass |
| National accounts | 2,721,359 | 314,441,728 | 1,385,763,282 | 352,198,656 | 7,106,671,058 | Pass |
| Consumer prices | 6,548,663 | 242,040,832 | 2,346,474,969 | 600,059,904 | 8,315,243,993 | Pass |

The current MySQL data directory and temporary fingerprint workspace are on
the same `C:` volume. The recorded free space was approximately 17.6 GiB, so
every isolated preflight passed. Capacity must be checked again immediately
before each build because free space can change.

This table preserves the original v0.6.2 preflight evidence. After the first
national-account attempt exposed greater real storage growth from non-truncated
text, v0.6.3 added a 1.5 safety factor to every future shadow estimate. The
factor is reported explicitly by the preflight and does not change the
historical figures above.

## Safe Command Sequence

Generate a plan without connecting to MySQL:

```powershell
python project_scripts/diagnostics/remediate_euro_large_table.py EURO_MFI_INTEREST_RATES --stage plan
```

Run the read-only capacity preflight:

```powershell
python project_scripts/diagnostics/remediate_euro_large_table.py EURO_MFI_INTEREST_RATES --stage preflight --output-dir audit_outputs/euro_large_preflight
```

Create and verify the required scoped backup on a separate physical volume:

```powershell
python project_scripts/diagnostics/backup_euro_large_table.py EURO_MFI_INTEREST_RATES --output-dir "<separate-volume-backup-directory>"
```

After recording one timestamp suffix, build the isolated shadow:

```powershell
python project_scripts/diagnostics/remediate_euro_large_table.py EURO_MFI_INTEREST_RATES --stage build --backup-file "<verified-backup.sql>" --suffix "<timestamp>" --confirm BUILD_EURO_MFI_INTEREST_RATES_V062_SHADOW --output-dir audit_outputs/euro_large_rebuild
```

The build must report a valid row, key, non-null and full-row hash comparison.
It leaves the active table unchanged. The plan command prints the exact atomic
swap and rollback SQL for the selected suffix.

Only after reviewing the build report and obtaining separate approval:

```powershell
python project_scripts/diagnostics/remediate_euro_large_table.py EURO_MFI_INTEREST_RATES --stage swap --backup-file "<verified-backup.sql>" --suffix "<timestamp>" --confirm SWAP_EURO_MFI_INTEREST_RATES_V062_SHADOW --output-dir audit_outputs/euro_large_rebuild
```

Rerun the full read-only streaming audit after the swap. National accounts may
start only after MFI passes its post-swap audit; consumer prices remains last.

## Execution Status

Version 0.6.2 prepared and tested these controls. Version 0.6.3 executed the
runbook in the required order after explicit approval. Every table received a
separate structure-and-data backup on another physical volume, a capacity
preflight, an isolated shadow build, an exact disk-backed validation and an
atomic swap.

| Import | Active rows after swap | Missing | Extra | Hash mismatch | Retained table |
| --- | ---: | ---: | ---: | ---: | --- |
| MFI interest rates | 1,594,491 | 0 | 0 | 0 | `euro_mfi_interest_rate_statistics__pre_v062_20260811_101729` |
| National accounts | 2,721,359 | 0 | 0 | 0 | `euro_main_aggregates_national_accounts__pre_v062_20260811_103657` |
| Consumer prices | 6,548,663 | 0 | 0 | 0 | `euro_indices_consumer_prices__pre_v062_20260811_110132` |

The final read-only audit compared 10,864,513 source and active SQL rows with
zero differences. It also found zero null or duplicate business keys and zero
invalid numeric observations. The active tables are protected by unique
`(key_code, time_period)` contracts.

One initial national-account shadow failed on a long `data_comp` value before
any active-table change. The 17,250-row partial table was renamed to
`euro_main_aggregates_national_accou__failed_v062_20260811_103224` and retained
for forensic review. Non-key text fields are now promoted to `TEXT`, and the
successful rebuild preserved the complete source.

See `EURO_LARGE_REBUILD_RESULTS.md` for backup hashes, rollback statements and
the final evidence digest. No retained or failed table was deleted.
