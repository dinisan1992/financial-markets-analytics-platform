"""Canonical source contracts for configured market assets.

The manifest separates a financial series identity from its local CSV filename.
An ``identity_status`` of ``verified`` means the current file was matched to the
provider series or confirmed from download history. ``inferred`` entries are
usable source contracts, but should still be confirmed during the next refresh.
"""


FEDERAL_RESERVE_H15_URL = (
    "https://www.federalreserve.gov/datadownload/Output.aspx?"
    "filetype=csv&from=&label=include&lastobs=&layout=seriescolumn&rel=H15&"
    "series=bf17364827e38702b42a58cf8eaa3f78&to=&type=package"
)


def _source(
    provider,
    identifier,
    url,
    frequency,
    acquisition_method,
    identity_status="verified",
    native_ohlc_expected=True,
    notes="",
):
    return {
        "source_provider": provider,
        "source_identifier": identifier,
        "source_reference": url,
        "source_frequency": frequency,
        "source_type": acquisition_method,
        "source_identity_status": identity_status,
        "source_native_ohlc_expected": native_ohlc_expected,
        "source_notes": notes,
    }


MARKET_SOURCE_MANIFEST = {
    "BTC": _source(
        "CoinGecko",
        "bitcoin",
        "https://www.coingecko.com/en/coins/bitcoin/historical_data",
        "daily",
        "manual_csv_download",
        native_ohlc_expected=False,
    ),
    "SP500": _source(
        "Yahoo Finance",
        "^GSPC",
        "https://finance.yahoo.com/quote/%5EGSPC/history/",
        "trading_days",
        "manual_csv_download",
        identity_status="inferred",
        notes="Confirm the provider when the legacy source is refreshed.",
    ),
    "STOXX600": _source(
        "Investing.com",
        "STOXX 600 historical data",
        "https://www.investing.com/indices/stoxx-600-historical-data",
        "trading_days",
        "manual_csv_download",
    ),
    "FTSE100": _source(
        "Investing.com",
        "FTSE 100 historical data",
        "https://www.investing.com/indices/uk-100-historical-data",
        "trading_days",
        "manual_csv_download",
    ),
    "GOLD": _source(
        "Yahoo Finance",
        "GC=F",
        "https://finance.yahoo.com/quote/GC%3DF/history/",
        "trading_days",
        "manual_csv_download",
        identity_status="inferred",
    ),
    "DXY": _source(
        "Yahoo Finance",
        "DX-Y.NYB",
        "https://finance.yahoo.com/quote/DX-Y.NYB/history/",
        "trading_days",
        "manual_csv_download",
        identity_status="inferred",
    ),
    "EURO": _source(
        "Yahoo Finance",
        "EURUSD=X",
        "https://finance.yahoo.com/quote/EURUSD%3DX/history/",
        "trading_days",
        "manual_csv_download",
        identity_status="inferred",
    ),
    "YUAN": _source(
        "Yahoo Finance",
        "CNY=X",
        "https://finance.yahoo.com/quote/CNY%3DX/history/",
        "trading_days",
        "manual_csv_download",
        identity_status="inferred",
    ),
    "LIBRA": _source(
        "Yahoo Finance",
        "GBPUSD=X",
        "https://finance.yahoo.com/quote/GBPUSD%3DX/history/",
        "trading_days",
        "manual_csv_download",
        identity_status="inferred",
    ),
    "SSECOMPOSITE": _source(
        "Yahoo Finance",
        "000001.SS",
        "https://finance.yahoo.com/quote/000001.SS/history/",
        "trading_days",
        "manual_csv_download",
        identity_status="inferred",
    ),
    "NASDAQ100": _source(
        "Yahoo Finance", "^NDX", "https://finance.yahoo.com/quote/%5ENDX/history/",
        "trading_days", "manual_csv_download"
    ),
    "DOWJONES": _source(
        "Yahoo Finance", "^DJI", "https://finance.yahoo.com/quote/%5EDJI/history/",
        "trading_days", "manual_csv_download"
    ),
    "RUSSELL2000": _source(
        "Yahoo Finance", "^RUT", "https://finance.yahoo.com/quote/%5ERUT/history/",
        "trading_days", "manual_csv_download"
    ),
    "EUROSTOXX50": _source(
        "Yahoo Finance", "^STOXX50E",
        "https://finance.yahoo.com/quote/%5ESTOXX50E/history/",
        "trading_days", "manual_csv_download"
    ),
    "DAX": _source(
        "Yahoo Finance", "^GDAXI",
        "https://finance.yahoo.com/quote/%5EGDAXI/history/",
        "trading_days", "manual_csv_download"
    ),
    "CAC40": _source(
        "Yahoo Finance", "^FCHI", "https://finance.yahoo.com/quote/%5EFCHI/history/",
        "trading_days", "manual_csv_download"
    ),
    "NIKKEI225": _source(
        "Yahoo Finance", "^N225", "https://finance.yahoo.com/quote/%5EN225/history/",
        "trading_days", "manual_csv_download"
    ),
    "EMERGING_MARKETS": _source(
        "Yahoo Finance", "EEM", "https://finance.yahoo.com/quote/EEM/history/",
        "trading_days", "manual_csv_download"
    ),
    "VIX": _source(
        "Yahoo Finance", "^VIX", "https://finance.yahoo.com/quote/%5EVIX/history/",
        "trading_days", "manual_csv_download"
    ),
    "MOVE_INDEX": _source(
        "Yahoo Finance", "^MOVE", "https://finance.yahoo.com/quote/%5EMOVE/history/",
        "trading_days", "manual_csv_download"
    ),
    "BRENT_OIL": _source(
        "Yahoo Finance", "BZ=F", "https://finance.yahoo.com/quote/BZ%3DF/history/",
        "trading_days", "manual_csv_download"
    ),
    "WTI_OIL": _source(
        "Yahoo Finance", "CL=F", "https://finance.yahoo.com/quote/CL%3DF/history/",
        "trading_days", "manual_csv_download",
        notes="Negative settlement values are historically possible, including April 2020."
    ),
    "NATURAL_GAS": _source(
        "Yahoo Finance", "NG=F", "https://finance.yahoo.com/quote/NG%3DF/history/",
        "trading_days", "manual_csv_download"
    ),
    "COPPER": _source(
        "Yahoo Finance", "HG=F", "https://finance.yahoo.com/quote/HG%3DF/history/",
        "trading_days", "manual_csv_download"
    ),
    "SILVER": _source(
        "Yahoo Finance", "SI=F", "https://finance.yahoo.com/quote/SI%3DF/history/",
        "trading_days", "manual_csv_download"
    ),
    "WHEAT": _source(
        "Yahoo Finance", "ZW=F", "https://finance.yahoo.com/quote/ZW%3DF/history/",
        "trading_days", "manual_csv_download"
    ),
    "CORN": _source(
        "Yahoo Finance", "ZC=F", "https://finance.yahoo.com/quote/ZC%3DF/history/",
        "trading_days", "manual_csv_download"
    ),
    "YEN": _source(
        "Yahoo Finance", "JPY=X", "https://finance.yahoo.com/quote/JPY%3DX/history/",
        "trading_days", "manual_csv_download"
    ),
    "SWISS_FRANC": _source(
        "Yahoo Finance", "CHF=X", "https://finance.yahoo.com/quote/CHF%3DX/history/",
        "trading_days", "manual_csv_download"
    ),
    "US3M": _source(
        "Yahoo Finance",
        "^IRX",
        "https://finance.yahoo.com/quote/%5EIRX/history/",
        "trading_days",
        "manual_csv_download",
        notes="Yahoo labels ^IRX as the 13-week Treasury bill yield.",
    ),
    "US2Y": _source(
        "Federal Reserve Board H.15",
        "RIFLGFCY02_N.B (FRED alias DGS2)",
        FEDERAL_RESERVE_H15_URL,
        "trading_days",
        "official_csv_download",
        native_ohlc_expected=False,
        notes="Market yield on 2-year Treasury constant maturity, percent per year.",
    ),
    "US10Y": _source(
        "Yahoo Finance", "^TNX", "https://finance.yahoo.com/quote/%5ETNX/history/",
        "trading_days", "manual_csv_download"
    ),
    "US30Y": _source(
        "Yahoo Finance", "^TYX", "https://finance.yahoo.com/quote/%5ETYX/history/",
        "trading_days", "manual_csv_download"
    ),
    "GERMANY10Y": _source(
        "FRED/OECD", "IRLTLT01DEM156N",
        "https://fred.stlouisfed.org/series/IRLTLT01DEM156N",
        "monthly", "manual_csv_download", native_ohlc_expected=False
    ),
    "UK10Y": _source(
        "FRED/OECD", "IRLTLT01GBM156N",
        "https://fred.stlouisfed.org/series/IRLTLT01GBM156N",
        "monthly", "manual_csv_download", native_ohlc_expected=False
    ),
    "JAPAN10Y": _source(
        "FRED/OECD", "IRLTLT01JPM156N",
        "https://fred.stlouisfed.org/series/IRLTLT01JPM156N",
        "monthly", "manual_csv_download", native_ohlc_expected=False
    ),
    "FINANCIAL_CONDITIONS": _source(
        "FRED", "NFCI", "https://fred.stlouisfed.org/series/NFCI",
        "weekly", "manual_csv_download", native_ohlc_expected=False
    ),
    "TED_SPREAD": _source(
        "FRED", "TEDRATE", "https://fred.stlouisfed.org/series/TEDRATE",
        "daily", "manual_csv_download", native_ohlc_expected=False,
        notes="The source series was discontinued in January 2022."
    ),
}


def get_market_source(asset_key):
    """Return a defensive copy of one source contract."""
    key = str(asset_key).upper()
    if key not in MARKET_SOURCE_MANIFEST:
        raise KeyError(f"No market source contract for asset: {key}")
    return dict(MARKET_SOURCE_MANIFEST[key])
