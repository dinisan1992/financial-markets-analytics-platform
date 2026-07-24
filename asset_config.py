from config import CLEAN_DATA_DIR, NEW_MARKET_CLEAN_DIR


# =========================
# ASSET CONFIGURATION
# =========================

ASSETS = {
    # =========================
    # CORE / EXISTING ASSETS
    # =========================

    "BTC": {
        "display_name": "Bitcoin",
        "script_name": "project_scripts/assets/main.py",
        "csv_path": CLEAN_DATA_DIR / "btc_data.csv",
        "table_name": "btc_analysis",
        "market_type": "crypto",
        "symbol": "BTC"
    },

    "SP500": {
        "display_name": "S&P 500",
        "script_name": "project_scripts/assets/sp500.py",
        "csv_path": CLEAN_DATA_DIR / "sp500_data.csv",
        "table_name": "sp500_analysis_clean",
        "market_type": "equity_index",
        "symbol": "SP500"
    },

    "STOXX600": {
        "display_name": "STOXX 600",
        "script_name": "project_scripts/assets/stoxx600.py",
        "csv_path": CLEAN_DATA_DIR / "stoxx600_data.csv",
        "table_name": "stoxx600_analysis",
        "market_type": "equity_index",
        "symbol": "STOXX600"
    },

    "FTSE100": {
        "display_name": "FTSE 100",
        "script_name": "project_scripts/assets/ftse100.py",
        "csv_path": CLEAN_DATA_DIR / "ftse100_data.csv",
        "table_name": "ftse100_analysis",
        "market_type": "equity_index",
        "symbol": "FTSE100"
    },

    "GOLD": {
        "display_name": "Gold",
        "script_name": "project_scripts/assets/gold.py",
        "csv_path": CLEAN_DATA_DIR / "gold_data.csv",
        "table_name": "gold_analysis_clean",
        "market_type": "commodity",
        "symbol": "GOLD"
    },

    "DXY": {
        "display_name": "DXY / US Dollar Index",
        "script_name": "project_scripts/assets/dollaramericano.py",
        "csv_path": CLEAN_DATA_DIR / "dxy_data.csv",
        "table_name": "dxy_analysis_clean",
        "market_type": "currency_index",
        "symbol": "DXY"
    },

    "EURO": {
        "display_name": "Euro",
        "script_name": "project_scripts/assets/euro.py",
        "csv_path": CLEAN_DATA_DIR / "euro_data.csv",
        "table_name": "euro_analysis",
        "market_type": "currency",
        "symbol": "EUR"
    },

    "YUAN": {
        "display_name": "Chinese Yuan",
        "script_name": "project_scripts/assets/yuan.py",
        "csv_path": CLEAN_DATA_DIR / "yuan_data.csv",
        "table_name": "yuan_analysis",
        "market_type": "currency",
        "symbol": "CNY"
    },

    "LIBRA": {
        "display_name": "British Pound",
        "script_name": "project_scripts/assets/libra.py",
        "csv_path": CLEAN_DATA_DIR / "libra_data.csv",
        "table_name": "libra_analysis",
        "market_type": "currency",
        "symbol": "GBP"
    },

    "SSECOMPOSITE": {
        "display_name": "SSE Composite",
        "script_name": "project_scripts/assets/ssecomposite.py",
        "csv_path": CLEAN_DATA_DIR / "ssecomposite_data.csv",
        "table_name": "ssecomposite_analysis",
        "market_type": "equity_index",
        "symbol": "SSE"
    },

    # =========================
    # NEW EQUITY INDICES
    # =========================

    "NASDAQ100": {
        "display_name": "NASDAQ 100",
        "script_name": "project_scripts/assets/nasdaq100.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "nasdaq100_data_clean.csv",
        "table_name": "nasdaq100_analysis",
        "market_type": "equity_index",
        "symbol": "NASDAQ100"
    },

    "DOWJONES": {
        "display_name": "Dow Jones Industrial Average",
        "script_name": "project_scripts/assets/dowjones.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "dowjones_data_clean.csv",
        "table_name": "dowjones_analysis",
        "market_type": "equity_index",
        "symbol": "DOWJONES"
    },

    "RUSSELL2000": {
        "display_name": "Russell 2000",
        "script_name": "project_scripts/assets/russell2000.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "russell2000_data_clean.csv",
        "table_name": "russell2000_analysis",
        "market_type": "equity_index",
        "symbol": "RUSSELL2000"
    },

    "EUROSTOXX50": {
        "display_name": "Euro Stoxx 50",
        "script_name": "project_scripts/assets/eurostoxx50.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "eurostoxx50_data_clean.csv",
        "table_name": "eurostoxx50_analysis",
        "market_type": "equity_index",
        "symbol": "EUROSTOXX50"
    },

    "DAX": {
        "display_name": "DAX",
        "script_name": "project_scripts/assets/dax.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "dax_data_clean.csv",
        "table_name": "dax_analysis",
        "market_type": "equity_index",
        "symbol": "DAX"
    },

    "CAC40": {
        "display_name": "CAC 40",
        "script_name": "project_scripts/assets/cac40.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "cac40_data_clean.csv",
        "table_name": "cac40_analysis",
        "market_type": "equity_index",
        "symbol": "CAC40"
    },

    "NIKKEI225": {
        "display_name": "Nikkei 225",
        "script_name": "project_scripts/assets/nikkei225.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "nikkei225_data_clean.csv",
        "table_name": "nikkei225_analysis",
        "market_type": "equity_index",
        "symbol": "NIKKEI225"
    },

    "EMERGING_MARKETS": {
        "display_name": "MSCI Emerging Markets / EEM",
        "script_name": "project_scripts/assets/emerging_markets.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "emerging_markets_data_clean.csv",
        "table_name": "emerging_markets_analysis",
        "market_type": "equity_index",
        "symbol": "EEM"
    },

    # =========================
    # VOLATILITY / STRESS
    # =========================

    "VIX": {
        "display_name": "VIX Volatility Index",
        "script_name": "project_scripts/assets/vix.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "vix_data_clean.csv",
        "table_name": "vix_analysis",
        "market_type": "volatility",
        "symbol": "VIX"
    },

    "MOVE_INDEX": {
        "display_name": "MOVE Index",
        "script_name": "project_scripts/assets/move_index.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "move_index_data_clean.csv",
        "table_name": "move_index_analysis",
        "market_type": "volatility",
        "symbol": "MOVE"
    },

    # =========================
    # COMMODITIES
    # =========================

    "BRENT_OIL": {
        "display_name": "Brent Crude Oil",
        "script_name": "project_scripts/assets/brent_oil.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "brent_oil_data_clean.csv",
        "table_name": "brent_oil_analysis",
        "market_type": "commodity",
        "symbol": "BRENT"
    },

    "WTI_OIL": {
        "display_name": "WTI Crude Oil",
        "script_name": "project_scripts/assets/wti_oil.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "wti_oil_data_clean.csv",
        "table_name": "wti_oil_analysis",
        "market_type": "commodity",
        "symbol": "WTI"
    },

    "NATURAL_GAS": {
        "display_name": "Natural Gas",
        "script_name": "project_scripts/assets/natural_gas.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "natural_gas_data_clean.csv",
        "table_name": "natural_gas_analysis",
        "market_type": "commodity",
        "symbol": "NATGAS"
    },

    "COPPER": {
        "display_name": "Copper",
        "script_name": "project_scripts/assets/copper.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "copper_data_clean.csv",
        "table_name": "copper_analysis",
        "market_type": "commodity",
        "symbol": "COPPER"
    },

    "SILVER": {
        "display_name": "Silver",
        "script_name": "project_scripts/assets/silver.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "silver_data_clean.csv",
        "table_name": "silver_analysis",
        "market_type": "commodity",
        "symbol": "SILVER"
    },

    "WHEAT": {
        "display_name": "Wheat",
        "script_name": "project_scripts/assets/wheat.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "wheat_data_clean.csv",
        "table_name": "wheat_analysis",
        "market_type": "commodity",
        "symbol": "WHEAT"
    },

    "CORN": {
        "display_name": "Corn",
        "script_name": "project_scripts/assets/corn.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "corn_data_clean.csv",
        "table_name": "corn_analysis",
        "market_type": "commodity",
        "symbol": "CORN"
    },

    # =========================
    # FX / CURRENCIES
    # =========================

    "YEN": {
        "display_name": "Japanese Yen",
        "script_name": "project_scripts/assets/yen.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "yen_data_clean.csv",
        "table_name": "yen_analysis",
        "market_type": "currency",
        "symbol": "JPY"
    },

    "SWISS_FRANC": {
        "display_name": "Swiss Franc",
        "script_name": "project_scripts/assets/swiss_franc.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "swiss_franc_data_clean.csv",
        "table_name": "swiss_franc_analysis",
        "market_type": "currency",
        "symbol": "CHF"
    },

    # =========================
    # YIELDS / RATES
    # =========================

    "US10Y": {
        "display_name": "US 10-Year Treasury Yield",
        "script_name": "project_scripts/assets/us10y.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "us10y_data_clean.csv",
        "table_name": "us10y_analysis",
        "market_type": "yield",
        "symbol": "US10Y"
    },

    "US2Y": {
        "display_name": "US 2-Year Treasury Yield",
        "script_name": "project_scripts/assets/us2y.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "us2y_data_clean.csv",
        "table_name": "us2y_analysis",
        "market_type": "yield",
        "symbol": "US2Y"
    },

    "US30Y": {
        "display_name": "US 30-Year Treasury Yield",
        "script_name": "project_scripts/assets/us30y.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "us30y_data_clean.csv",
        "table_name": "us30y_analysis",
        "market_type": "yield",
        "symbol": "US30Y"
    },

    "GERMANY10Y": {
        "display_name": "Germany 10-Year Bund Yield",
        "script_name": "project_scripts/assets/germany10y.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "germany10y_data_clean.csv",
        "table_name": "germany10y_analysis",
        "market_type": "yield",
        "symbol": "GERMANY10Y"
    },

    "UK10Y": {
        "display_name": "UK 10-Year Gilt Yield",
        "script_name": "project_scripts/assets/uk10y.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "uk10y_data_clean.csv",
        "table_name": "uk10y_analysis",
        "market_type": "yield",
        "symbol": "UK10Y"
    },

    "JAPAN10Y": {
        "display_name": "Japan 10-Year Government Bond Yield",
        "script_name": "project_scripts/assets/japan10y.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "japan10y_data_clean.csv",
        "table_name": "japan10y_analysis",
        "market_type": "yield",
        "symbol": "JAPAN10Y"
    },

    # =========================
    # FINANCIAL STRESS / MACRO
    # =========================

    "FINANCIAL_CONDITIONS": {
        "display_name": "Financial Conditions Index",
        "script_name": "project_scripts/assets/financial_conditions.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "financial_conditions_data_clean.csv",
        "table_name": "financial_conditions_analysis",
        "market_type": "financial_stress",
        "symbol": "NFCI"
    },

    "TED_SPREAD": {
        "display_name": "TED Spread",
        "script_name": "project_scripts/assets/ted_spread.py",
        "csv_path": NEW_MARKET_CLEAN_DIR / "ted_spread_data_clean.csv",
        "table_name": "ted_spread_analysis",
        "market_type": "financial_stress",
        "symbol": "TED"
    },
}


# =========================
# HELPER FUNCTIONS
# =========================

def get_asset_config(asset_key):
    """
    Returns an asset configuration by code.
    Example:
        get_asset_config("BTC")
    """

    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Asset not found in ASSETS: {asset_key}")

    return ASSETS[asset_key]


def get_all_asset_keys():
    """
    Returns the list of configured asset codes.
    """

    return list(ASSETS.keys())


def get_all_script_names():
    """
    Returns the list of configured scripts.
    Useful for a future run_all_assets.py workflow.

    Note:
    Some new asset scripts may not exist yet.
    """

    return [
        asset_data["script_name"]
        for asset_data in ASSETS.values()
        if asset_data.get("script_name")
    ]


def get_existing_script_names():
    """
    Returns only scripts that already exist physically in the project.
    Useful to avoid run_all_assets.py errors while the new scripts
    have not been created yet.
    """

    from pathlib import Path
    from config import BASE_DIR

    scripts = []

    for asset_data in ASSETS.values():
        script_name = asset_data.get("script_name")

        if not script_name:
            continue

        script_path = BASE_DIR / Path(script_name)

        if script_path.exists():
            scripts.append(script_name)

    return scripts


def get_missing_script_names():
    """
    Returns configured scripts that do not yet exist physically in the project.
    Useful for planning new asset pipelines without breaking runners.
    """

    from pathlib import Path
    from config import BASE_DIR

    missing_scripts = []

    for asset_key, asset_data in ASSETS.items():
        script_name = asset_data.get("script_name")

        if not script_name:
            continue

        script_path = BASE_DIR / Path(script_name)

        if not script_path.exists():
            missing_scripts.append((asset_key, script_name))

    return missing_scripts


def get_table_name(asset_key):
    """
    Returns the SQL table name for an asset.
    """

    return get_asset_config(asset_key)["table_name"]


def get_csv_path(asset_key):
    """
    Returns the CSV path for an asset.
    """

    return get_asset_config(asset_key)["csv_path"]


def get_display_name(asset_key):
    """
    Returns the asset display name.
    """

    return get_asset_config(asset_key)["display_name"]


def get_market_type(asset_key):
    """
    Returns the asset market type.
    """

    return get_asset_config(asset_key)["market_type"]


def get_assets_by_market_type(market_type):
    """
    Returns all assets for a given market type.
    Example:
        get_assets_by_market_type("commodity")
    """

    return {
        key: value
        for key, value in ASSETS.items()
        if value["market_type"] == market_type
    }

