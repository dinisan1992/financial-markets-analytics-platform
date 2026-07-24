# =========================
# ASSET GROUPS FOR ANALYSIS
# =========================

ASSET_GROUPS = {
    "risk_assets": {
        "name": "Risk Assets",
        "description": "BTC, major US indices and small caps.",
        "assets": [
            "BTC",
            "SP500",
            "NASDAQ100",
            "DOWJONES",
            "RUSSELL2000"
        ]
    },

    "global_equities": {
        "name": "Global Equity Indices",
        "description": "Major global equity indices.",
        "assets": [
            "SP500",
            "NASDAQ100",
            "DOWJONES",
            "RUSSELL2000",
            "STOXX600",
            "EUROSTOXX50",
            "DAX",
            "CAC40",
            "FTSE100",
            "NIKKEI225",
            "SSECOMPOSITE",
            "EMERGING_MARKETS"
        ]
    },

    "safe_havens_fx": {
        "name": "Safe Havens / FX",
        "description": "Gold, US dollar, yen and Swiss franc.",
        "assets": [
            "GOLD",
            "DXY",
            "YEN",
            "SWISS_FRANC"
        ]
    },

    "commodities": {
        "name": "Commodities",
        "description": "Energy, metals and agricultural commodities.",
        "assets": [
            "GOLD",
            "SILVER",
            "BRENT_OIL",
            "WTI_OIL",
            "NATURAL_GAS",
            "COPPER",
            "WHEAT",
            "CORN"
        ]
    },

    "energy": {
        "name": "Energy",
        "description": "Oil and natural gas.",
        "assets": [
            "BRENT_OIL",
            "WTI_OIL",
            "NATURAL_GAS"
        ]
    },

    "metals": {
        "name": "Metals",
        "description": "Gold, silver and copper.",
        "assets": [
            "GOLD",
            "SILVER",
            "COPPER"
        ]
    },

    "agriculture": {
        "name": "Agriculture",
        "description": "Agricultural commodities.",
        "assets": [
            "WHEAT",
            "CORN"
        ]
    },

    "stress_indicators": {
        "name": "Stress Indicators",
        "description": "Volatility, financial stress and spreads.",
        "assets": [
            "VIX",
            "MOVE_INDEX",
            "FINANCIAL_CONDITIONS",
            "TED_SPREAD"
        ]
    },

    "yields": {
        "name": "Government Bond Yields",
        "description": "US, Germany, UK and Japan yields.",
        "assets": [
            "US2Y",
            "US10Y",
            "US30Y",
            "GERMANY10Y",
            "UK10Y",
            "JAPAN10Y"
        ]
    },

    "us_yield_curve": {
        "name": "US Yield Curve",
        "description": "US 2Y, 10Y and 30Y yields.",
        "assets": [
            "US2Y",
            "US10Y",
            "US30Y"
        ]
    },

    "core_macro_view": {
        "name": "Core Macro View",
        "description": "Core macro view: risk, dollar, gold, oil, stress and yields.",
        "assets": [
            "BTC",
            "NASDAQ100",
            "GOLD",
            "DXY",
            "BRENT_OIL",
            "VIX",
            "US10Y"
        ]
    },

    "btc_macro_view": {
        "name": "BTC Macro View",
        "description": "BTC compared with Nasdaq, gold, dollar, VIX and yields.",
        "assets": [
            "BTC",
            "NASDAQ100",
            "GOLD",
            "DXY",
            "VIX",
            "US10Y"
        ]
    }
}


# =========================
# IMPORTANT ANALYSIS PAIRS
# =========================

IMPORTANT_PAIRS = {
    "btc_nasdaq": {
        "name": "BTC vs NASDAQ 100",
        "asset_a": "BTC",
        "asset_b": "NASDAQ100"
    },

    "btc_gold": {
        "name": "BTC vs Gold",
        "asset_a": "BTC",
        "asset_b": "GOLD"
    },

    "btc_dxy": {
        "name": "BTC vs DXY",
        "asset_a": "BTC",
        "asset_b": "DXY"
    },

    "sp500_vix": {
        "name": "S&P 500 vs VIX",
        "asset_a": "SP500",
        "asset_b": "VIX"
    },

    "nasdaq_us10y": {
        "name": "NASDAQ 100 vs US 10Y",
        "asset_a": "NASDAQ100",
        "asset_b": "US10Y"
    },

    "gold_dxy": {
        "name": "Gold vs DXY",
        "asset_a": "GOLD",
        "asset_b": "DXY"
    },

    "gold_us10y": {
        "name": "Gold vs US 10Y",
        "asset_a": "GOLD",
        "asset_b": "US10Y"
    },

    "brent_dxy": {
        "name": "Brent Oil vs DXY",
        "asset_a": "BRENT_OIL",
        "asset_b": "DXY"
    },

    "brent_us10y": {
        "name": "Brent Oil vs US 10Y",
        "asset_a": "BRENT_OIL",
        "asset_b": "US10Y"
    },

    "vix_move": {
        "name": "VIX vs MOVE Index",
        "asset_a": "VIX",
        "asset_b": "MOVE_INDEX"
    }
}


# =========================
# HELPER FUNCTIONS
# =========================

def get_asset_groups():
    return ASSET_GROUPS


def get_group_assets(group_key):
    if group_key not in ASSET_GROUPS:
        raise ValueError(f"Group not found: {group_key}")

    return ASSET_GROUPS[group_key]["assets"]


def get_group_name(group_key):
    if group_key not in ASSET_GROUPS:
        raise ValueError(f"Group not found: {group_key}")

    return ASSET_GROUPS[group_key]["name"]


def get_important_pairs():
    return IMPORTANT_PAIRS