# =========================
# MACRO CONFIG
# =========================
# Central configuration for macro indicators loaded in SQL.
#
# Adapted version after macro_sql_inventory_report.csv.
#
# Current strategy:
# 1. FED / US remains operational.
# 2. EURO / EU remains registered as a complex layer, but does NOT enter MACRO_ASSETS yet.
# 3. MACRO_ASSETS contains only simple and safe series.
# 4. Macro scripts should start by testing FED series.
#
# Reason:
# EURO/EU tables are multidimensional and require filters by country,
# metric, unit, frequency, sector, instrument, etc.
# They should not be treated yet as simple date/value series.


# =========================
# FED / US - SIMPLE SERIES
# =========================

FED_MACRO = {
    "FED_FUNDS_RATE": {
        "display_name": "Federal Funds Effective Rate",
        "table_name": "fed_federal_funds_rate",
        "date_col": "observation_date",
        "value_col": "federal_funds_rate",
        "category": "rates",
        "region": "US",
        "unit": "%",
        "enabled": True,
        "needs_filter": False,
        "description": "Effective Federal Funds Rate."
    },

    "FED_M2": {
        "display_name": "US M2 Money Supply",
        "table_name": "fed_m2",
        "date_col": "observation_date",
        "value_col": "m2",
        "category": "liquidity",
        "region": "US",
        "unit": "USD",
        "enabled": True,
        "needs_filter": False,
        "description": "US M2 monetary aggregate."
    },

    "FED_TOTAL_ASSETS": {
        "display_name": "Fed Total Assets",
        "table_name": "fed_total_assets",
        "date_col": "observation_date",
        "value_col": "total_assets",
        "category": "liquidity",
        "region": "US",
        "unit": "USD",
        "enabled": True,
        "needs_filter": False,
        "description": "Total assets on the Federal Reserve balance sheet."
    },

    "FED_RESERVE_BANK_CREDIT": {
        "display_name": "Reserve Bank Credit",
        "table_name": "fed_reserve_bank_credit",
        "date_col": "observation_date",
        "value_col": "reserve_bank_credit",
        "category": "liquidity",
        "region": "US",
        "unit": "USD",
        "enabled": True,
        "needs_filter": False,
        "description": "Federal Reserve Bank credit."
    },

    "FED_DEPOSITS": {
        "display_name": "Deposits, All Commercial Banks",
        "table_name": "fed_deposits",
        "date_col": "observation_date",
        "value_col": "deposits",
        "category": "banking",
        "region": "US",
        "unit": "USD",
        "enabled": True,
        "needs_filter": False,
        "description": "Deposits at US commercial banks."
    },

    "FED_BANK_CREDIT": {
        "display_name": "Bank Credit, All Commercial Banks",
        "table_name": "fed_bank_credit",
        "date_col": "observation_date",
        "value_col": "totbkcr",
        "category": "credit",
        "region": "US",
        "unit": "USD",
        "enabled": True,
        "needs_filter": False,
        "description": "Total bank credit from US commercial banks."
    },

    "FED_LOANS_LEASES": {
        "display_name": "Loans and Leases in Bank Credit",
        "table_name": "fed_loans_leases",
        "date_col": "observation_date",
        "value_col": "total_loans_leases",
        "category": "credit",
        "region": "US",
        "unit": "USD",
        "enabled": True,
        "needs_filter": False,
        "description": "Loans and leases in bank credit."
    },

    "FED_SECURITIES_BANK_CREDIT": {
        "display_name": "Securities in Bank Credit",
        "table_name": "fed_securities_bank_credit",
        "date_col": "observation_date",
        "value_col": "securities_in_bank_credit",
        "category": "credit",
        "region": "US",
        "unit": "USD",
        "enabled": True,
        "needs_filter": False,
        "description": "Securities included in bank credit."
    },

    "FED_CONSUMER_LOANS_CREDIT_CARDS": {
        "display_name": "Consumer Loans: Credit Cards and Other Revolving Plans",
        "table_name": "fed_consumer_loans_credit_cards",
        "date_col": "observation_date",
        "value_col": "consumer_loans",
        "category": "consumer_credit",
        "region": "US",
        "unit": "USD",
        "enabled": True,
        "needs_filter": False,
        "description": "Consumer credit through credit cards and other revolving plans."
    },

    "FED_CREDIT_CARD_DELINQUENCY": {
        "display_name": "Delinquency Rate on Credit Card Loans",
        "table_name": "fed_credit_card_delinquency",
        "date_col": "observation_date",
        "value_col": "delinquency_rate",
        "category": "consumer_stress",
        "region": "US",
        "unit": "%",
        "enabled": True,
        "needs_filter": False,
        "description": "Delinquency rate on credit card loans."
    },

    "FED_CHARGE_OFF_RATE_CREDIT_CARDS": {
        "display_name": "Charge-Off Rate on Credit Card Loans",
        "table_name": "fed_charge_off_rate_credit_cards",
        "date_col": "observation_date",
        "value_col": "charge_off_rate",
        "category": "consumer_stress",
        "region": "US",
        "unit": "%",
        "enabled": True,
        "needs_filter": False,
        "description": "Charge-off/loss rate on credit card loans."
    }
}


# =========================
# EURO / EU - COMPLEX LAYER
# =========================
# These tables exist, but they do NOT enter MACRO_ASSETS yet.
#
# Reason:
# These tables are multidimensional. Selecting date_col/value_col is not enough.
# They require filters by country, metric, unit, frequency, sector, etc.
#
# They are kept here as inventory for a future phase.

EURO_COMPLEX_MACRO = {
    "EURO_CONSUMER_PRICES": {
        "display_name": "Euro Area Consumer Prices",
        "table_name": "euro_indices_consumer_prices",
        "date_col": None,
        "value_col": None,
        "category": "inflation",
        "region": "EURO",
        "unit": "index",
        "enabled": False,
        "needs_filter": True,
        "description": "Euro-area consumer price indices. Requires filters before use."
    },

    "EURO_COMPOSITE_SYSTEMIC_STRESS": {
        "display_name": "Euro Composite Indicator of Systemic Stress",
        "table_name": "euro_composite_indicator_stress",
        "date_col": None,
        "value_col": None,
        "category": "stress",
        "region": "EURO",
        "unit": "index",
        "enabled": False,
        "needs_filter": True,
        "description": "Composite systemic stress indicator. Confirm structure before use."
    },

    "EURO_COUNTRY_FINANCIAL_STRESS": {
        "display_name": "Euro Country-Level Financial Stress",
        "table_name": "euro_country_level_financial_stress",
        "date_col": None,
        "value_col": None,
        "category": "stress",
        "region": "EURO",
        "unit": "index",
        "enabled": False,
        "needs_filter": True,
        "description": "Country-level financial stress indicator. Requires country/series selection."
    },

    "EURO_BANK_LENDING_SURVEY": {
        "display_name": "Euro Bank Lending Survey",
        "table_name": "euro_bank_lending_survey",
        "date_col": None,
        "value_col": None,
        "category": "credit",
        "region": "EURO",
        "unit": "index",
        "enabled": False,
        "needs_filter": True,
        "description": "Bank lending survey. Requires filters by question/sector/country."
    },

    "EURO_BALANCE_SHEET_ITEMS": {
        "display_name": "Euro Balance Sheet Items",
        "table_name": "euro_balance_sheet_items",
        "date_col": None,
        "value_col": None,
        "category": "banking",
        "region": "EURO",
        "unit": "value",
        "enabled": False,
        "needs_filter": True,
        "description": "Balance sheet items. Large multidimensional table."
    },

    "EURO_MFI_INTEREST_RATES": {
        "display_name": "Euro MFI Interest Rate Statistics",
        "table_name": "euro_mfi_interest_rate_statistics",
        "date_col": None,
        "value_col": None,
        "category": "rates",
        "region": "EURO",
        "unit": "%",
        "enabled": False,
        "needs_filter": True,
        "description": "MFI rates. Requires filters by rate type, country, maturity and instrument."
    },

    "EURO_RETAIL_INTEREST_RATES": {
        "display_name": "Euro Retail Interest Rates",
        "table_name": "euro_retail_interest_rates",
        "date_col": None,
        "value_col": None,
        "category": "rates",
        "region": "EURO",
        "unit": "%",
        "enabled": False,
        "needs_filter": True,
        "description": "Retail rates. Requires filters by country/instrument."
    },

    "EURO_GOVERNMENT_FINANCE": {
        "display_name": "Euro Government Finance Statistics",
        "table_name": "euro_government_finance_statistics",
        "date_col": None,
        "value_col": None,
        "category": "fiscal",
        "region": "EURO",
        "unit": "value",
        "enabled": False,
        "needs_filter": True,
        "description": "Public finance statistics. Large multidimensional table."
    },

    "EURO_NATIONAL_ACCOUNTS": {
        "display_name": "Euro Main Aggregates National Accounts",
        "table_name": "euro_main_aggregates_national_accounts",
        "date_col": None,
        "value_col": None,
        "category": "growth",
        "region": "EURO",
        "unit": "value",
        "enabled": False,
        "needs_filter": True,
        "description": "National accounts. Requires a specific aggregate choice."
    },

    "EURO_ATM_POS_TRANSACTIONS": {
        "display_name": "Euro ATM, OTC and POS Transactions",
        "table_name": "euro_atm_pos_transactions",
        "date_col": None,
        "value_col": None,
        "category": "payments",
        "region": "EURO",
        "unit": "transactions",
        "enabled": False,
        "needs_filter": True,
        "description": "ATM/OTC/POS transactions. Requires filters by category/geography."
    },

    "EURO_CARD_PAYMENTS": {
        "display_name": "Euro Card Payments and Cash Withdrawals",
        "table_name": "euro_card_payments",
        "date_col": None,
        "value_col": None,
        "category": "payments_fraud",
        "region": "EURO",
        "unit": "transactions",
        "enabled": False,
        "needs_filter": True,
        "description": "Card payments and withdrawals. Requires filters before use."
    },

    "EURO_CARD_PAYMENTS_BY_MERCHANT_CATEGORY": {
        "display_name": "Euro Card Payments by Merchant Category",
        "table_name": "euro_card_payments_by_merchant_category",
        "date_col": None,
        "value_col": None,
        "category": "payments",
        "region": "EURO",
        "unit": "transactions",
        "enabled": False,
        "needs_filter": True,
        "description": "Payments by merchant category. Requires filters."
    },

    "EURO_CREDIT_TRANSFERS": {
        "display_name": "Euro Credit Transfers",
        "table_name": "euro_credit_transfers",
        "date_col": None,
        "value_col": None,
        "category": "payments",
        "region": "EURO",
        "unit": "transactions",
        "enabled": False,
        "needs_filter": True,
        "description": "Credit transfers. Requires filters."
    },

    "EURO_DIRECT_DEBITS": {
        "display_name": "Euro Direct Debits",
        "table_name": "euro_direct_debits",
        "date_col": None,
        "value_col": None,
        "category": "payments",
        "region": "EURO",
        "unit": "transactions",
        "enabled": False,
        "needs_filter": True,
        "description": "Direct debits. Requires filters."
    },

    "EURO_EMONEY_PAYMENTS": {
        "display_name": "Euro E-money Payment Transactions",
        "table_name": "euro_emoney_payment_transactions",
        "date_col": None,
        "value_col": None,
        "category": "payments",
        "region": "EURO",
        "unit": "transactions",
        "enabled": False,
        "needs_filter": True,
        "description": "E-money payment transactions. Requires filters."
    },

    "EURO_LOSSES_FRAUD": {
        "display_name": "Euro Losses Due to Fraud",
        "table_name": "euro_losses_due_to_fraud",
        "date_col": None,
        "value_col": None,
        "category": "payments_fraud",
        "region": "EURO",
        "unit": "value",
        "enabled": False,
        "needs_filter": True,
        "description": "Fraud losses. Requires filters by instrument/responsibility/geography."
    },

    "EURO_PAYMENT_SYSTEMS": {
        "display_name": "Euro Transactions in Payment Systems",
        "table_name": "euro_transactions_payments_systems",
        "date_col": None,
        "value_col": None,
        "category": "payments",
        "region": "EURO",
        "unit": "transactions",
        "enabled": False,
        "needs_filter": True,
        "description": "Transactions in payment systems. Requires filters."
    }
}


# =========================
# FINAL ACTIVE CONFIG
# =========================
# IMPORTANT:
# MACRO_ASSETS contains only simple and safe series.
# For now: FED only.
#
# This prevents macro_summary_report.py, macro_data_loader.py
# and macro_macro_market_selector.py from trying to load complex EURO tables.

MACRO_ASSETS = {
    **FED_MACRO
}


# =========================
# TOTAL CONFIG / INVENTORY
# =========================
# Useful for documentation or future expansion.
# Do not use directly in simple loaders.

ALL_MACRO_CONFIGS = {
    **FED_MACRO,
    **EURO_COMPLEX_MACRO
}


# =========================
# ACTIVE MACRO GROUPS
# =========================

MACRO_GROUPS = {
    "fed_liquidity": {
        "name": "Fed Liquidity",
        "description": "Fed balance sheet, M2, Federal Reserve credit and liquidity.",
        "assets": [
            "FED_M2",
            "FED_TOTAL_ASSETS",
            "FED_RESERVE_BANK_CREDIT"
        ]
    },

    "fed_banking_credit": {
        "name": "Fed Banking & Credit",
        "description": "Bank credit, deposits, loans and securities.",
        "assets": [
            "FED_BANK_CREDIT",
            "FED_DEPOSITS",
            "FED_LOANS_LEASES",
            "FED_SECURITIES_BANK_CREDIT"
        ]
    },

    "fed_consumer_stress": {
        "name": "Fed Consumer Credit Stress",
        "description": "Credit cards, delinquencies and charge-offs.",
        "assets": [
            "FED_CONSUMER_LOANS_CREDIT_CARDS",
            "FED_CREDIT_CARD_DELINQUENCY",
            "FED_CHARGE_OFF_RATE_CREDIT_CARDS"
        ]
    },

    "fed_rates": {
        "name": "Fed Rates",
        "description": "Federal Reserve interest rates.",
        "assets": [
            "FED_FUNDS_RATE"
        ]
    },

    "fed_core": {
        "name": "Core Fed Macro Indicators",
        "description": "Core US macro indicators.",
        "assets": [
            "FED_FUNDS_RATE",
            "FED_M2",
            "FED_TOTAL_ASSETS",
            "FED_RESERVE_BANK_CREDIT",
            "FED_DEPOSITS",
            "FED_BANK_CREDIT",
            "FED_LOANS_LEASES",
            "FED_CREDIT_CARD_DELINQUENCY",
            "FED_CHARGE_OFF_RATE_CREDIT_CARDS"
        ]
    }
}


# =========================
# FUTURE EURO GROUPS
# =========================
# Kept separate so they do not enter simple validators/loaders.

EURO_COMPLEX_GROUPS = {
    "euro_rates_inflation": {
        "name": "Euro Rates & Inflation",
        "description": "European consumer prices and interest rates. Requires filters.",
        "assets": [
            "EURO_CONSUMER_PRICES",
            "EURO_MFI_INTEREST_RATES",
            "EURO_RETAIL_INTEREST_RATES"
        ]
    },

    "euro_financial_stress": {
        "name": "Euro Financial Stress",
        "description": "Systemic stress, country-level stress and bank credit. Requires filters.",
        "assets": [
            "EURO_COMPOSITE_SYSTEMIC_STRESS",
            "EURO_COUNTRY_FINANCIAL_STRESS",
            "EURO_BANK_LENDING_SURVEY"
        ]
    },

    "euro_banking_macro": {
        "name": "Euro Banking & Macro",
        "description": "Balance sheets, public finance and national accounts. Requires filters.",
        "assets": [
            "EURO_BALANCE_SHEET_ITEMS",
            "EURO_GOVERNMENT_FINANCE",
            "EURO_NATIONAL_ACCOUNTS"
        ]
    },

    "euro_payments_fraud": {
        "name": "Euro Payments & Fraud",
        "description": "Payments, cards, transfers, debits and fraud. Requires filters.",
        "assets": [
            "EURO_ATM_POS_TRANSACTIONS",
            "EURO_CARD_PAYMENTS",
            "EURO_CARD_PAYMENTS_BY_MERCHANT_CATEGORY",
            "EURO_CREDIT_TRANSFERS",
            "EURO_DIRECT_DEBITS",
            "EURO_EMONEY_PAYMENTS",
            "EURO_LOSSES_FRAUD",
            "EURO_PAYMENT_SYSTEMS"
        ]
    }
}


# =========================
# ACTIVE MACRO / MARKET PAIRS
# =========================
# For now, only safe FED pairs.
# EURO pairs return after specific filters are created.

MACRO_MARKET_PAIRS = {
    "fed_m2_btc": {
        "name": "Fed M2 vs BTC",
        "macro_asset": "FED_M2",
        "market_asset": "BTC",
        "description": "US monetary liquidity compared with Bitcoin."
    },

    "fed_m2_nasdaq": {
        "name": "Fed M2 vs NASDAQ 100",
        "macro_asset": "FED_M2",
        "market_asset": "NASDAQ100",
        "description": "US monetary liquidity compared with technology/growth stocks."
    },

    "fed_total_assets_sp500": {
        "name": "Fed Total Assets vs S&P 500",
        "macro_asset": "FED_TOTAL_ASSETS",
        "market_asset": "SP500",
        "description": "Fed balance sheet compared with the US equity market."
    },

    "fed_total_assets_nasdaq": {
        "name": "Fed Total Assets vs NASDAQ 100",
        "macro_asset": "FED_TOTAL_ASSETS",
        "market_asset": "NASDAQ100",
        "description": "Fed balance sheet compared with technology/growth stocks."
    },

    "fed_reserve_bank_credit_sp500": {
        "name": "Reserve Bank Credit vs S&P 500",
        "macro_asset": "FED_RESERVE_BANK_CREDIT",
        "market_asset": "SP500",
        "description": "Federal Reserve credit compared with US equities."
    },

    "fed_funds_sp500": {
        "name": "Fed Funds Rate vs S&P 500",
        "macro_asset": "FED_FUNDS_RATE",
        "market_asset": "SP500",
        "description": "Federal Funds Rate compared with US equities."
    },

    "fed_funds_nasdaq": {
        "name": "Fed Funds Rate vs NASDAQ 100",
        "macro_asset": "FED_FUNDS_RATE",
        "market_asset": "NASDAQ100",
        "description": "Federal Funds Rate compared with technology/growth stocks."
    },

    "fed_funds_btc": {
        "name": "Fed Funds Rate vs BTC",
        "macro_asset": "FED_FUNDS_RATE",
        "market_asset": "BTC",
        "description": "Federal Funds Rate compared with Bitcoin."
    },

    "fed_funds_dxy": {
        "name": "Fed Funds Rate vs DXY",
        "macro_asset": "FED_FUNDS_RATE",
        "market_asset": "DXY",
        "description": "Federal Funds Rate compared with dollar strength."
    },

    "fed_credit_sp500": {
        "name": "Fed Bank Credit vs S&P 500",
        "macro_asset": "FED_BANK_CREDIT",
        "market_asset": "SP500",
        "description": "US bank credit compared with the S&P 500."
    },

    "fed_loans_leases_sp500": {
        "name": "Loans and Leases vs S&P 500",
        "macro_asset": "FED_LOANS_LEASES",
        "market_asset": "SP500",
        "description": "Loans and leases in bank credit compared with US equities."
    },

    "fed_deposits_sp500": {
        "name": "Commercial Bank Deposits vs S&P 500",
        "macro_asset": "FED_DEPOSITS",
        "market_asset": "SP500",
        "description": "Commercial bank deposits compared with US equities."
    },

    "fed_delinquency_vix": {
        "name": "Credit Card Delinquency vs VIX",
        "macro_asset": "FED_CREDIT_CARD_DELINQUENCY",
        "market_asset": "VIX",
        "description": "Credit card delinquency compared with equity volatility."
    },

    "fed_charge_off_vix": {
        "name": "Credit Card Charge-Off Rate vs VIX",
        "macro_asset": "FED_CHARGE_OFF_RATE_CREDIT_CARDS",
        "market_asset": "VIX",
        "description": "Credit card losses compared with equity volatility."
    },

    "fed_consumer_loans_nasdaq": {
        "name": "Consumer Credit Card Loans vs NASDAQ 100",
        "macro_asset": "FED_CONSUMER_LOANS_CREDIT_CARDS",
        "market_asset": "NASDAQ100",
        "description": "Consumer revolving credit compared with growth/technology assets."
    }
}


# =========================
# HELPER FUNCTIONS
# =========================

def get_macro_config(macro_key, include_disabled=False):
    macro_key = macro_key.upper()

    configs = ALL_MACRO_CONFIGS if include_disabled else MACRO_ASSETS

    if macro_key not in configs:
        raise ValueError(
            f"Macro indicator not found or inactive: {macro_key}"
        )

    return configs[macro_key]


def get_all_macro_keys(include_disabled=False):
    if include_disabled:
        return list(ALL_MACRO_CONFIGS.keys())

    return list(MACRO_ASSETS.keys())


def get_enabled_macro_keys():
    return [
        key for key, cfg in MACRO_ASSETS.items()
        if cfg.get("enabled", True) is True
    ]


def get_disabled_macro_keys():
    return [
        key for key, cfg in ALL_MACRO_CONFIGS.items()
        if cfg.get("enabled", False) is False
    ]


def get_macro_groups(include_disabled=False):
    if include_disabled:
        return {
            **MACRO_GROUPS,
            **EURO_COMPLEX_GROUPS
        }

    return MACRO_GROUPS


def get_macro_group_assets(group_key, include_disabled=False):
    groups = get_macro_groups(include_disabled=include_disabled)

    if group_key not in groups:
        raise ValueError(f"Macro group not found: {group_key}")

    return groups[group_key]["assets"]


def get_macro_by_category(category, include_disabled=False):
    configs = ALL_MACRO_CONFIGS if include_disabled else MACRO_ASSETS

    return [
        key for key, cfg in configs.items()
        if cfg["category"].lower() == category.lower()
    ]


def get_macro_by_region(region, include_disabled=False):
    configs = ALL_MACRO_CONFIGS if include_disabled else MACRO_ASSETS

    return [
        key for key, cfg in configs.items()
        if cfg["region"].lower() == region.lower()
    ]


def get_macro_market_pairs():
    return MACRO_MARKET_PAIRS


def get_macro_table_name(macro_key):
    return get_macro_config(macro_key)["table_name"]


def get_macro_display_name(macro_key):
    return get_macro_config(macro_key)["display_name"]


def get_macro_date_col(macro_key):
    return get_macro_config(macro_key)["date_col"]


def get_macro_value_col(macro_key):
    return get_macro_config(macro_key)["value_col"]


def is_macro_enabled(macro_key):
    cfg = get_macro_config(
        macro_key,
        include_disabled=True
    )

    return cfg.get("enabled", False) is True


def macro_needs_filter(macro_key):
    cfg = get_macro_config(
        macro_key,
        include_disabled=True
    )

    return cfg.get("needs_filter", False) is True


def print_macro_status():
    print("\n" + "=" * 100)
    print("MACRO CONFIG STATUS")
    print("=" * 100)
    print(f"Active macro assets: {len(MACRO_ASSETS)}")
    print(f"Total macro assets in inventory: {len(ALL_MACRO_CONFIGS)}")
    print(f"Disabled/complex macro assets: {len(get_disabled_macro_keys())}")

    print("\nActive assets:")
    for macro_key in get_enabled_macro_keys():
        cfg = MACRO_ASSETS[macro_key]
        print(
            f"- {macro_key:40s} | "
            f"{cfg['display_name']} | "
            f"{cfg['table_name']}.{cfg['value_col']}"
        )

    print("\nDisabled/complex assets:")
    for macro_key in get_disabled_macro_keys():
        cfg = ALL_MACRO_CONFIGS[macro_key]
        print(
            f"- {macro_key:40s} | "
            f"{cfg['display_name']} | "
            f"needs_filter={cfg.get('needs_filter')}"
        )

    print("=" * 100)


# =========================
# QUICK TEST
# =========================

if __name__ == "__main__":
    print_macro_status()
