# Large EURO Rebuild Plan

Version: v0.6.2

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

## Safety Status

Version 0.6.2 prepared and tested these commands but did not execute the backup,
build or swap stages. No MySQL row, index, schema or table was changed.
