# EURO Fraud Backlog

## Status

The European fraud series are important for Risk/Fraud Analytics, but they are temporarily excluded from the main macro/market analysis because validation currently returns `empty_series`.

## Affected Series

- EURO_CARD_FRAUD_LOSSES
- EURO_CREDIT_TRANSFER_FRAUD_LOSSES
- EURO_DIRECT_DEBIT_FRAUD_LOSSES
- EURO_EMONEY_FRAUD_LOSSES

## Reason

The current `key_code` values do not load valid data through `euro_data_loader.py`.

## Next Step

Create a dedicated module:

```text
euro_fraud_analysis.py
```
