"""Source and write-safety contracts for FED and EURO CSV importers."""

from config import EURO_SOURCE_DIR, FED_SOURCE_DIR


def _fed(
    filename,
    table_name,
    source_identifier,
    value_column,
    script_name,
):
    return {
        "group": "FED",
        "source_provider": "Federal Reserve Bank of St. Louis (FRED)",
        "source_identifier": source_identifier,
        "source_reference": f"https://fred.stlouisfed.org/series/{source_identifier}",
        "csv_path": FED_SOURCE_DIR / filename,
        "table_name": table_name,
        "mode": "simple_series",
        "source_key_columns": ("observation_date",),
        "target_key_columns": ("observation_date",),
        "column_aliases": {
            source_identifier.lower(): value_column,
        },
        "required_columns": ("observation_date", value_column),
        "value_column": value_column,
        "write_policy": "validated_upsert",
        "script_name": script_name,
    }


def _euro(filename, table_name, script_name, column_aliases=None):
    return {
        "group": "EURO",
        "source_provider": "European Central Bank Data Portal",
        "source_identifier": filename.removesuffix(".csv"),
        "source_reference": "https://data.ecb.europa.eu/",
        "csv_path": EURO_SOURCE_DIR / filename,
        "table_name": table_name,
        "mode": "multidimensional_series",
        "source_key_columns": ("key_code", "time_period"),
        "target_key_columns": ("key_code", "time_period"),
        "column_aliases": {"key": "key_code", **(column_aliases or {})},
        "required_columns": ("key_code", "time_period", "obs_value"),
        "write_policy": "schema_remediation_required",
        "script_name": script_name,
    }


MACRO_IMPORTS = {
    "FED_FUNDS_RATE": _fed(
        "Federal Funds Effective Rate.csv",
        "fed_federal_funds_rate",
        "FEDFUNDS",
        "federal_funds_rate",
        "tools/fed/fed_federal_funds_rate.py",
    ),
    "FED_M2": _fed(
        "M2SL.csv",
        "fed_m2",
        "M2SL",
        "m2",
        "tools/fed/fed_m2.py",
    ),
    "FED_TOTAL_ASSETS": _fed(
        "Assets Total Assets Total Assets.csv",
        "fed_total_assets",
        "WALCL",
        "total_assets",
        "tools/fed/fed_total_assets.py",
    ),
    "FED_RESERVE_BANK_CREDIT": _fed(
        "Reserve Bank Credit.csv",
        "fed_reserve_bank_credit",
        "RSBKCRNS",
        "reserve_bank_credit",
        "tools/fed/fed_reserve_bank_credit.py",
    ),
    "FED_DEPOSITS": _fed(
        "Deposits, All Commercial Banks.csv",
        "fed_deposits",
        "DPSACBW027SBOG",
        "deposits",
        "tools/fed/fed_deposits.py",
    ),
    "FED_BANK_CREDIT": _fed(
        "Bank Credit, All Commercial Banks.csv",
        "fed_bank_credit",
        "TOTBKCR",
        "totbkcr",
        "tools/legacy/bank_credit_all_commercial_banks.py",
    ),
    "FED_LOANS_LEASES": _fed(
        "Loans and Leases in Bank Credit, All Commercial Banks.csv",
        "fed_loans_leases",
        "TOTLLNSA",
        "total_loans_leases",
        "tools/fed/fed_loans_leases.py",
    ),
    "FED_SECURITIES_BANK_CREDIT": _fed(
        "Securities in Bank Credit, All Commercial Banks.csv",
        "fed_securities_bank_credit",
        "SBCACBW027SBOG",
        "securities_in_bank_credit",
        "tools/fed/fed_securities_bank_credit.py",
    ),
    "FED_CONSUMER_LOANS_CREDIT_CARDS": _fed(
        "Consumer Loans Credit Cards and Other Revolving Plans, All Commercial Banks.csv",
        "fed_consumer_loans_credit_cards",
        "CCLACBW027SBOG",
        "consumer_loans",
        "tools/fed/fed_consumer_loans_credit_cards.py",
    ),
    "FED_CREDIT_CARD_DELINQUENCY": _fed(
        "Delinquency Rate on Credit Card Loans, All Commercial Banks.csv",
        "fed_credit_card_delinquency",
        "DRCCLACBS",
        "delinquency_rate",
        "tools/fed/fed_credit_card_delinquency.py",
    ),
    "FED_CHARGE_OFF_RATE_CREDIT_CARDS": _fed(
        "Charge-Off Rate on Credit Card Loans, All Commercial Banks.csv",
        "fed_charge_off_rate_credit_cards",
        "CORCCACBS",
        "charge_off_rate",
        "tools/fed/fed_charge_off_rate_credit_cards.py",
    ),
    "EURO_ATM_POS_TRANSACTIONS": _euro(
        "ATM, OTC and POS terminal transactions.csv",
        "euro_atm_pos_transactions",
        "tools/eu/euro_atm_pos_transactions.py",
        column_aliases={
            "trmnl_lctn": "terminal_location",
            "typ_trnsctn": "transaction_type",
            "rl_trnsctn": "reported_transaction",
            "inttn_chnnl": "intention_channel",
        },
    ),
    "EURO_BALANCE_SHEET_ITEMS": _euro(
        "Balance Sheet Items.csv",
        "euro_balance_sheet_items",
        "tools/eu/euro_balance_sheet_items.py",
    ),
    "EURO_BANK_LENDING_SURVEY": _euro(
        "Bank Lending Survey.csv",
        "euro_bank_lending_survey",
        "tools/eu/euro_bank_lending_survey.py",
    ),
    "EURO_CARD_PAYMENTS": _euro(
        "Card payments and cash withdrawals using cards (including fraud data).csv",
        "euro_card_payments",
        "tools/eu/euro_card_payments.py",
    ),
    "EURO_CARD_PAYMENTS_MERCHANT_CATEGORY": _euro(
        "Electronic card payments sent by merchant category.csv",
        "euro_card_payments_by_merchant_category",
        "tools/eu/euro_card_payments_by_merchant_category.py",
    ),
    "EURO_COMPOSITE_SYSTEMIC_STRESS": _euro(
        "Composite Indicator of Systemic Stress.csv",
        "euro_composite_indicator_stress",
        "tools/eu/euro_composite_indicator_stress.py",
    ),
    "EURO_COUNTRY_FINANCIAL_STRESS": _euro(
        "Country-Level Index of Financial Stress.csv",
        "euro_country_level_financial_stress",
        "tools/eu/euro_country_level_financial_stress.py",
    ),
    "EURO_CREDIT_TRANSFERS": _euro(
        "Credit transfers (including fraud).csv",
        "euro_credit_transfers",
        "tools/eu/euro_credit_transfers.py",
    ),
    "EURO_DIRECT_DEBITS": _euro(
        "Direct debits (including fraud).csv",
        "euro_direct_debits",
        "tools/eu/euro_direct_debits.py",
    ),
    "EURO_EMONEY_PAYMENTS": _euro(
        "E-money payment transactions (including fraud data).csv",
        "euro_emoney_payment_transactions",
        "tools/eu/euro_emoney_payment_transactions.py",
    ),
    "EURO_GOVERNMENT_FINANCE": _euro(
        "Government Finance Statistics.csv",
        "euro_government_finance_statistics",
        "tools/legacy/government_finance_statistics.py",
    ),
    "EURO_CONSUMER_PRICES": _euro(
        "Indices of Consumer Prices_euro.csv",
        "euro_indices_consumer_prices",
        "tools/eu/euro_indices_consumer_prices.py",
    ),
    "EURO_FRAUD_LOSSES": _euro(
        "Losses due to fraud by liability bearer.csv",
        "euro_losses_due_to_fraud",
        "tools/eu/euro_losses_due_to_fraud.py",
    ),
    "EURO_NATIONAL_ACCOUNTS": _euro(
        "Main aggregates, national accounts_euro.csv",
        "euro_main_aggregates_national_accounts",
        "tools/eu/euro_main_aggregates_national_accounts.py",
    ),
    "EURO_MFI_INTEREST_RATES": _euro(
        "MFI Interest Rate Statistics.csv",
        "euro_mfi_interest_rate_statistics",
        "tools/eu/euro_mfi_interest_rate_statistics.py",
    ),
    "EURO_RETAIL_INTEREST_RATES": _euro(
        "Retail Interest Rates.csv",
        "euro_retail_interest_rates",
        "tools/eu/euro_retail_interest_rates.py",
    ),
    "EURO_PAYMENT_SYSTEM_TRANSACTIONS": _euro(
        "Transactions in payments systems.csv",
        "euro_transactions_payments_systems",
        "tools/eu/euro_transactions_payments_systems.py",
    ),
}


def get_macro_import(import_key):
    key = str(import_key).upper()
    if key not in MACRO_IMPORTS:
        raise KeyError(f"Unknown macro import: {key}")
    return dict(MACRO_IMPORTS[key])


def get_macro_import_keys(group=None):
    if group is None:
        return list(MACRO_IMPORTS)
    normalized = str(group).upper()
    return [
        key
        for key, contract in MACRO_IMPORTS.items()
        if contract["group"] == normalized
    ]
