# Official PCP Shadow Build

Version: v0.8.2

Date: 17 August 2026

## Authorized Scope

The authorized operation was limited to creating and validating the official
Card Payments (`PCP`) shadow. The command accepted only
`EURO_CARD_PAYMENTS`, required the exact
`BUILD_EURO_CARD_PAYMENTS_V079_SHADOW` confirmation and exposed no swap,
cleanup or active-table promotion mode.

The source CSV, scoped SQL backup, pin manifest, readiness report, current
active schema, audit classifications, future table names and storage capacity
were revalidated before the shadow was created. The configured active CSV was
not replaced.

## Built Shadow

| Field | Result |
| --- | --- |
| Shadow table | `euro_card_payments__shadow_v079_20260817_115720` |
| Official source rows | 1,081,151 |
| Shadow rows | 1,081,151 |
| Unique business keys | 1,081,151 |
| Null business keys | 0 |
| Duplicate business-key groups | 0 |
| Non-null observations | 976,858 |
| First period | `2000` |
| Last period | `2026-Q1` |
| Row-hash mismatches | 0 |
| Source-hash mismatches | 0 |
| Missing source rows | 0 |
| Technical hash column | Present for review |
| Shadow schema SHA-256 | `CD2C5CAC8D407522F8853B7E59AE96044139035BC4204A4AC0A00F4C925DDABF` |

Two complete memory-bounded validations independently reproduced every row,
business key and mapped value from the official staged source.

## Active-Table Proof

The active PCP table was fingerprinted immediately before the build, after both
complete validations and once more through a separate SELECT-only post-build
check.

| Check | Result |
| --- | --- |
| Active table | `euro_card_payments` |
| Active rows | 815,173 |
| Data SHA-256 | `491E0A03679544679FF7381D4027461C7BBF576F54E08F7C051BAA2EDA82887C` |
| Schema SHA-256 | `A0379A34BB5AFCBD7AA588F6F0C068243920400D0BE81CE1CF1F050CF89C8A8B` |
| Active table changed | No |
| Active CSV changed | No |
| Retained/failed table created | No |
| Swap authorized or performed | No |

The official-snapshot-authoritative policy is not applied to the active table
until a future promotion is separately reviewed and authorized. The 6,168
active-only keys therefore remain in the unchanged current active table.

## Signed Evidence

The local build report SHA-256 is
`D07C53007549F70E26E3885C1D49A52AF5A2064F8EE0E708A57D5762C1A0306D`.
The independent post-build verification SHA-256 is
`A564DD9E61E910BC62825A78B31771D82256C57A045C68431E95040DBC8C6E0B`.

Generated reports remain under ignored audit-output paths. Raw ECB data, SQL
backups, credentials and absolute local paths are not published.

## Remaining Authorization Gate

The shadow is ready for review but promotion has not been authorized or
performed. A future swap-only checkpoint must revalidate the pinned inputs,
complete shadow and active fingerprint, retain the former active table under
its versioned name, validate the promoted official snapshot and execute an
inverse atomic rename on any post-swap failure.

That guarded command and its independent read-only preflight were subsequently
completed. After separate authorization, v0.8.3 atomically promoted the shadow
and preserved this document's former active checkpoint under its versioned
retained name. See `docs/ECB_PCP_SWAP.md` for the final evidence.
