# EURO Storage-Precision Audit

Version: v0.7.3

Date: 11 August 2026

## Objective

The synchronization baseline reported millions of row-hash differences in
three EURO contracts whose business keys and row counts already matched. This
audit determined whether those differences represented revised ECB data,
metadata changes or SQL storage representation.

All database access was read-only. The commands issued schema inspection and
`SELECT` statements only; no database row or schema was changed.

## Method

The exact row fingerprint now canonicalizes values according to the active
target type:

- MySQL `FLOAT` values are selected through `CAST(... AS DOUBLE)` and compared
  through their exact stored 32-bit representation;
- `DECIMAL(p, s)` values use the declared target scale with decimal rounding;
- negative storage zero and positive zero share one canonical value;
- outer whitespace in text metadata does not change a row fingerprint;
- business keys, nulls, numeric validity and all substantive text remain
  strictly checked.

Mismatch samples can be ordered by their SHA-256 row hash. This produces a
deterministic sample distributed across the differing rows instead of only the
first alphabetical business keys. A separate field auditor then compares every
mapped column for those keys and records the change category and bounded
examples.

## Complete Results

| Contract | Rows per side | Previous apparent updates | Storage-aware differences | Interpretation |
| --- | ---: | ---: | ---: | --- |
| EURO_CARD_PAYMENTS | 815,173 | 459,207 | 15 | Six rows contain `method_ref` as `2005` versus `2005.0`; nine rows contain a different stored FLOAT value. |
| EURO_BANK_LENDING_SURVEY | 1,164,356 | 222,668 | 1 | One row contains a different stored FLOAT value. |
| EURO_BALANCE_SHEET_ITEMS | 7,812,208 | 3,132,298 | 54 | Only `obs_value` differs at the sixth-decimal boundary of `DECIMAL(20,6)`. |

Across all three contracts, source and target cardinality match, business keys
are unique, and there are no source-only or target-only keys. The complete
comparison covered 9,791,737 source rows and the same number of target rows.

The 54 Balance Sheet Items differences are consistent with historical binary
float conversion before insertion into a six-decimal target. This is an
inference from the half-unit boundary pattern; the audit deliberately retains
them as real differences rather than hiding them with a wider tolerance.

## Commands

Generate a complete storage-aware comparison and a deterministic mismatch
sample:

```powershell
python project_scripts/diagnostics/audit_euro_streaming_completeness.py `
  EURO_CARD_PAYMENTS EURO_BANK_LENDING_SURVEY EURO_BALANCE_SHEET_ITEMS `
  --sample-limit 100 --sample-strategy hash
```

Classify the saved mismatch keys by field:

```powershell
python project_scripts/diagnostics/audit_euro_field_differences.py `
  audit_outputs/euro_streaming_validation/euro_card_payments.json
```

Generated evidence remains under Git-ignored `audit_outputs/`. Public reports
contain source filenames only, never absolute local paths.

## Write Gate

No write is approved by this audit. The three CSV snapshots were downloaded in
October 2025, so the next safe sequence is:

1. download fresh copies from the ECB Data Portal;
2. validate file identity and rerun the complete read-only plans;
3. create a fresh scoped SQL backup on a separate physical volume;
4. review the resulting 15 Card Payments, one Bank Lending Survey and 54
   Balance Sheet Items actions;
5. use the existing explicit confirmation and transactional post-validation
   only if the reviewed counts remain valid.

Government Finance is excluded from this precision conclusion. Its 3,822,937
source-only rows remain a separate expansion and capacity-review task.
