# =========================
# EURO SERIES CONFIG - V1
# =========================
# EURO series selected from euro_series_inventory.csv
# Goal: transform complex EURO tables into simple, usable series.
#
# Expected structure for each loaded series:
# snapped_at | value
#
# This layer is independent from the FED layer.


EURO_SERIES = {
    # ==========================================================
    # INFLATION / PRICES - EURO AREA
    # ==========================================================

    "EURO_HICP_PROCESSED_FOOD": {
        "display_name": "Euro Area HICP - Processed Food",
        "description": "HICP - Processed food incl. alcohol and tobacco",
        "table_name": "euro_indices_consumer_prices",
        "key_code": "ICP.M.U2.N.FOODPR.4.INX",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "monthly",
        "region": "Euro Area",
        "category": "inflation",
        "unit": "index",
        "base100_recommended": True,
        "enabled": True
    },

    "EURO_HICP_EX_TOBACCO": {
        "display_name": "Euro Area HICP - All-items excluding tobacco",
        "description": "HICP - All-items excluding tobacco",
        "table_name": "euro_indices_consumer_prices",
        "key_code": "ICP.M.U2.N.X02200.3.CTG",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "monthly",
        "region": "Euro Area",
        "category": "inflation",
        "unit": "points",
        "base100_recommended": False,
        "enabled": True
    },

    "EURO_HICP_SERVICES": {
        "display_name": "Euro Area HICP - Services",
        "description": "HICP - Services",
        "table_name": "euro_indices_consumer_prices",
        "key_code": "ICP.M.U2.Y.SERV00.3.INX",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "monthly",
        "region": "Euro Area",
        "category": "inflation",
        "unit": "index",
        "base100_recommended": True,
        "enabled": True
    },

    "EURO_HICP_INDUSTRIAL_GOODS": {
        "display_name": "Euro Area HICP - Industrial Goods",
        "description": "HICP - Industrial goods",
        "table_name": "euro_indices_consumer_prices",
        "key_code": "ICP.M.U2.Y.IGOODS.3.INX",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "monthly",
        "region": "Euro Area",
        "category": "inflation",
        "unit": "index",
        "base100_recommended": True,
        "enabled": True
    },

    "EURO_HICP_ADMINISTERED_ENERGY_FOOD": {
        "display_name": "Euro Area HICP - Administered Energy & Food",
        "description": "HICP - Administered prices of energy and food products",
        "table_name": "euro_indices_consumer_prices",
        "key_code": "ICP.M.U2.N.ADMEF0.4.INX",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "monthly",
        "region": "Euro Area",
        "category": "inflation",
        "unit": "index",
        "base100_recommended": True,
        "enabled": True
    },

    # ==========================================================
    # BANK RATES / CREDIT - AUSTRIA AS EURO PROXY
    # ==========================================================

    "EURO_MFI_CORPORATE_LOANS_AT": {
        "display_name": "Euro MFI Rates - Corporate Loans Austria",
        "description": "Bank interest rates - loans to corporations",
        "table_name": "euro_mfi_interest_rate_statistics",
        "key_code": "MIR.M.AT.B.A2A.A.R.A.2240.EUR.N",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA",
        "frequency": "monthly",
        "region": "Austria",
        "category": "interest_rates",
        "unit": "percent",
        "base100_recommended": False,
        "enabled": True
    },

    "EURO_MFI_HOUSEHOLD_CONSUMPTION_LOANS_AT": {
        "display_name": "Euro MFI Rates - Household Consumption Loans Austria",
        "description": "Bank interest rates - loans to households for consumption",
        "table_name": "euro_mfi_interest_rate_statistics",
        "key_code": "MIR.M.AT.B.A2B.A.R.A.2250.EUR.N",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA",
        "frequency": "monthly",
        "region": "Austria",
        "category": "interest_rates",
        "unit": "percent",
        "base100_recommended": False,
        "enabled": True
    },

    "EURO_MFI_HOUSE_PURCHASE_LOANS_AT": {
        "display_name": "Euro MFI Rates - House Purchase Loans Austria",
        "description": "Bank interest rates - loans to households for house purchase",
        "table_name": "euro_mfi_interest_rate_statistics",
        "key_code": "MIR.M.AT.B.A2C.A.R.A.2250.EUR.N",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA",
        "frequency": "monthly",
        "region": "Austria",
        "category": "interest_rates",
        "unit": "percent",
        "base100_recommended": False,
        "enabled": True
    },

    "EURO_MFI_REVOLVING_LOANS_CORPORATE_AT": {
        "display_name": "Euro MFI Rates - Corporate Revolving Loans Austria",
        "description": "Bank interest rates - revolving loans and overdrafts to corporations",
        "table_name": "euro_mfi_interest_rate_statistics",
        "key_code": "MIR.M.AT.B.A2Z.A.R.A.2240.EUR.N",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA",
        "frequency": "monthly",
        "region": "Austria",
        "category": "interest_rates",
        "unit": "percent",
        "base100_recommended": False,
        "enabled": True
    },

    "EURO_MFI_REVOLVING_LOANS_HOUSEHOLDS_AT": {
        "display_name": "Euro MFI Rates - Household Revolving Loans Austria",
        "description": "Bank interest rates - revolving loans and overdrafts to households",
        "table_name": "euro_mfi_interest_rate_statistics",
        "key_code": "MIR.M.AT.B.A2Z.A.R.A.2250.EUR.N",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA",
        "frequency": "monthly",
        "region": "Austria",
        "category": "interest_rates",
        "unit": "percent",
        "base100_recommended": False,
        "enabled": True
    },

    "EURO_MFI_CORPORATE_DEPOSITS_AT": {
        "display_name": "Euro MFI Rates - Corporate Overnight Deposits Austria",
        "description": "Bank interest rates - overnight deposits from corporations",
        "table_name": "euro_mfi_interest_rate_statistics",
        "key_code": "MIR.M.AT.B.L21.A.R.A.2240.EUR.N",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA",
        "frequency": "monthly",
        "region": "Austria",
        "category": "interest_rates",
        "unit": "percent",
        "base100_recommended": False,
        "enabled": True
    },

    "EURO_MFI_HOUSEHOLD_DEPOSITS_AT": {
        "display_name": "Euro MFI Rates - Household Overnight Deposits Austria",
        "description": "Bank interest rates - overnight deposits from households",
        "table_name": "euro_mfi_interest_rate_statistics",
        "key_code": "MIR.M.AT.B.L21.A.R.A.2250.EUR.N",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA",
        "frequency": "monthly",
        "region": "Austria",
        "category": "interest_rates",
        "unit": "percent",
        "base100_recommended": False,
        "enabled": True
    },

    # ==========================================================
    # FRAUD / PAYMENTS - EU AGGREGATE
    # ==========================================================

    "EURO_CARD_FRAUD_LOSSES": {
        "display_name": "Euro Card Fraud Losses",
        "description": "Total value of losses due to fraud - card payments",
        "table_name": "euro_losses_due_to_fraud",
        "key_code": "PLB.H.B0.W0.CP0.1.1.F.N.EUR",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit_measure",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "semiannual",
        "region": "EU aggregate",
        "category": "fraud",
        "unit": "EUR",
        "base100_recommended": False,
        "enabled": False  # TODO: reactivate after euro_fraud_analysis.py is created
    },

    "EURO_CREDIT_TRANSFER_FRAUD_LOSSES": {
        "display_name": "Euro Credit Transfer Fraud Losses",
        "description": "Total value of losses due to fraud - credit transfers",
        "table_name": "euro_losses_due_to_fraud",
        "key_code": "PLB.H.B0.W0.CT0.1.1.F.N.EUR",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit_measure",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "semiannual",
        "region": "EU aggregate",
        "category": "fraud",
        "unit": "EUR",
        "base100_recommended": False,
        "enabled": False  # TODO: reactivate after euro_fraud_analysis.py is created
    },

    "EURO_DIRECT_DEBIT_FRAUD_LOSSES": {
        "display_name": "Euro Direct Debit Fraud Losses",
        "description": "Total value of losses due to fraud - direct debits",
        "table_name": "euro_losses_due_to_fraud",
        "key_code": "PLB.H.B0.W0.DD.2.1.F.N.EUR",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit_measure",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "semiannual",
        "region": "EU aggregate",
        "category": "fraud",
        "unit": "EUR",
        "base100_recommended": False,
        "enabled": False  # TODO: reactivate after euro_fraud_analysis.py is created
    },

    "EURO_EMONEY_FRAUD_LOSSES": {
        "display_name": "Euro E-money Fraud Losses",
        "description": "Total value of losses due to fraud - e-money payments",
        "table_name": "euro_losses_due_to_fraud",
        "key_code": "PLB.H.B0.W0.EMP0.1.1.F.N.EUR",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit_measure",
        "freq_col": "freq",
        "area_col": "ref_area",
        "frequency": "semiannual",
        "region": "EU aggregate",
        "category": "fraud",
        "unit": "EUR",
        "base100_recommended": False,
        "enabled": False  # TODO: reactivate after euro_fraud_analysis.py is created
    }
}


EURO_SERIES_GROUPS = {
    "inflation": [
        "EURO_HICP_PROCESSED_FOOD",
        "EURO_HICP_EX_TOBACCO",
        "EURO_HICP_SERVICES",
        "EURO_HICP_INDUSTRIAL_GOODS",
        "EURO_HICP_ADMINISTERED_ENERGY_FOOD"
    ],

    "interest_rates": [
        "EURO_MFI_CORPORATE_LOANS_AT",
        "EURO_MFI_HOUSEHOLD_CONSUMPTION_LOANS_AT",
        "EURO_MFI_HOUSE_PURCHASE_LOANS_AT",
        "EURO_MFI_REVOLVING_LOANS_CORPORATE_AT",
        "EURO_MFI_REVOLVING_LOANS_HOUSEHOLDS_AT",
        "EURO_MFI_CORPORATE_DEPOSITS_AT",
        "EURO_MFI_HOUSEHOLD_DEPOSITS_AT"
    ],


    # TODO: fraud remains in the backlog for a dedicated euro_fraud_analysis.py module
    # These series are important for Risk/Fraud Analytics, but do not belong
    # in the main macro/market analysis until the key_codes are fixed.
    "fraud": [
        "EURO_CARD_FRAUD_LOSSES",
        "EURO_CREDIT_TRANSFER_FRAUD_LOSSES",
        "EURO_DIRECT_DEBIT_FRAUD_LOSSES",
        "EURO_EMONEY_FRAUD_LOSSES"
    ]
}


EURO_MARKET_PAIRS = {
    # ==========================================================
    # INFLATION VS MARKETS
    # ==========================================================

    "euro_hicp_food_stoxx600": {
        "euro_series": "EURO_HICP_PROCESSED_FOOD",
        "market_asset": "STOXX600",
        "label": "Euro HICP Processed Food vs STOXX 600",
        "description": "Compares processed food prices in the euro area with European equities."
    },

    "euro_hicp_food_gold": {
        "euro_series": "EURO_HICP_PROCESSED_FOOD",
        "market_asset": "GOLD",
        "label": "Euro HICP Processed Food vs Gold",
        "description": "Compares euro-area food inflation/prices with gold."
    },

    "euro_hicp_ex_tobacco_stoxx600": {
        "euro_series": "EURO_HICP_EX_TOBACCO",
        "market_asset": "STOXX600",
        "label": "Euro HICP Ex Tobacco vs STOXX 600",
        "description": "Compares aggregate inflation excluding tobacco with European equities."
    },

    "euro_hicp_services_stoxx600": {
        "euro_series": "EURO_HICP_SERVICES",
        "market_asset": "STOXX600",
        "label": "Euro HICP Services vs STOXX 600",
        "description": "Compares services inflation/index with European equities."
    },

    "euro_hicp_industrial_goods_stoxx600": {
        "euro_series": "EURO_HICP_INDUSTRIAL_GOODS",
        "market_asset": "STOXX600",
        "label": "Euro HICP Industrial Goods vs STOXX 600",
        "description": "Compares industrial goods prices with European equities."
    },

    "euro_admin_energy_food_gold": {
        "euro_series": "EURO_HICP_ADMINISTERED_ENERGY_FOOD",
        "market_asset": "GOLD",
        "label": "Euro Administered Energy & Food Prices vs Gold",
        "description": "Compares administered energy/food prices with gold."
    },

    # ==========================================================
    # RATES / CREDIT VS MARKETS
    # ==========================================================

    "euro_mfi_corporate_loans_stoxx600": {
        "euro_series": "EURO_MFI_CORPORATE_LOANS_AT",
        "market_asset": "STOXX600",
        "label": "Euro MFI Corporate Loan Rates vs STOXX 600",
        "description": "Compares corporate loan rates with European equities."
    },

    "euro_mfi_corporate_loans_euro": {
        "euro_series": "EURO_MFI_CORPORATE_LOANS_AT",
        "market_asset": "EURO",
        "label": "Euro MFI Corporate Loan Rates vs EUR FX",
        "description": "Compares corporate credit rates with euro FX behaviour."
    },

    "euro_mfi_household_consumption_stoxx600": {
        "euro_series": "EURO_MFI_HOUSEHOLD_CONSUMPTION_LOANS_AT",
        "market_asset": "STOXX600",
        "label": "Euro MFI Household Consumption Loan Rates vs STOXX 600",
        "description": "Compares consumer credit rates with European equities."
    },

    "euro_mfi_house_purchase_stoxx600": {
        "euro_series": "EURO_MFI_HOUSE_PURCHASE_LOANS_AT",
        "market_asset": "STOXX600",
        "label": "Euro MFI House Purchase Loan Rates vs STOXX 600",
        "description": "Compares housing credit rates with European equities."
    },

    "euro_mfi_revolving_corporate_stoxx600": {
        "euro_series": "EURO_MFI_REVOLVING_LOANS_CORPORATE_AT",
        "market_asset": "STOXX600",
        "label": "Euro MFI Corporate Revolving Loan Rates vs STOXX 600",
        "description": "Compares corporate revolving/overdraft rates with European equities."
    },

    "euro_mfi_deposits_euro": {
        "euro_series": "EURO_MFI_HOUSEHOLD_DEPOSITS_AT",
        "market_asset": "EURO",
        "label": "Euro MFI Household Deposit Rates vs EUR FX",
        "description": "Compares household deposit rates with euro FX behaviour."
    }
    }
    # ==========================================================
    # FRAUD / PAYMENTS
    # ==========================================================

    # TODO: move to euro_fraud_analysis.py after fraud key_codes are fixed.
    # Fraud series have few observations and should be analysed as
    # a dedicated descriptive module, not as rolling correlation against markets.

    # "euro_card_fraud_financial_conditions": {
    #     "euro_series": "EURO_CARD_FRAUD_LOSSES",
    #     "market_asset": "FINANCIAL_CONDITIONS",
    #     "label": "Euro Card Fraud Losses vs Financial Conditions",
    #     "description": "Compares card fraud losses with financial conditions. Series has few observations."
    # },

    # "euro_credit_transfer_fraud_financial_conditions": {
    #     "euro_series": "EURO_CREDIT_TRANSFER_FRAUD_LOSSES",
    #     "market_asset": "FINANCIAL_CONDITIONS",
    #     "label": "Euro Credit Transfer Fraud Losses vs Financial Conditions",
    #     "description": "Compares transfer fraud losses with financial conditions. Series has few observations."
    # }


def get_euro_series_config(series_key):
    return EURO_SERIES[series_key]


def get_all_euro_series_keys():
    return list(EURO_SERIES.keys())


def get_enabled_euro_series_keys():
    return [
        key for key, cfg in EURO_SERIES.items()
        if cfg.get("enabled", True)
    ]


def get_euro_series_by_category(category):
    return [
        key for key, cfg in EURO_SERIES.items()
        if cfg.get("category") == category
    ]


def get_euro_market_pairs():
    return EURO_MARKET_PAIRS


def should_generate_base100(series_key):
    cfg = EURO_SERIES[series_key]
    return cfg.get("base100_recommended", True)


def print_euro_series_status():
    print("\nEURO SERIES CONFIG STATUS")
    print("=" * 120)
    print(f"Configured series: {len(EURO_SERIES)}")
    print(f"Active series: {len(get_enabled_euro_series_keys())}")
    print(f"Configured market pairs: {len(EURO_MARKET_PAIRS)}")

    print("\nGroups:")
    for group_name, series_keys in EURO_SERIES_GROUPS.items():
        print(f"- {group_name}: {len(series_keys)} series")

    print("\nSeries:")
    for key, cfg in EURO_SERIES.items():
        print(
            f"- {key} | {cfg['display_name']} | "
            f"{cfg['table_name']} | {cfg['key_code']} | "
            f"{cfg['category']} | base100={cfg.get('base100_recommended')} | "
            f"enabled={cfg.get('enabled', True)}"
        )

    print("=" * 120)


if __name__ == "__main__":
    print_euro_series_status()
