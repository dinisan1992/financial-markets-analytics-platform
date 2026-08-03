# Data Source Registry

The executable market-source contract lives in `market_source_manifest.py` and
is merged into every entry in `asset_config.py`. It records provider, dataset or
ticker, source URL, native frequency, acquisition method, OHLC expectation and
identity-verification status. Local CSV files and MySQL are storage layers; they
do not define the financial identity of a series.

## Market Assets

| Asset | Provider | Dataset / ticker | Frequency | Identity |
| --- | --- | --- | --- | --- |
| BTC | CoinGecko | `bitcoin` | Daily | Verified |
| SP500 | Yahoo Finance | `^GSPC` | Trading days | Inferred; confirm on refresh |
| STOXX600 | Investing.com | STOXX 600 historical data | Trading days | Verified |
| FTSE100 | Investing.com | FTSE 100 historical data | Trading days | Verified |
| GOLD | Yahoo Finance | `GC=F` | Trading days | Inferred; confirm on refresh |
| DXY | Yahoo Finance | `DX-Y.NYB` | Trading days | Inferred; confirm on refresh |
| EURO | Yahoo Finance | `EURUSD=X` | Trading days | Inferred; confirm on refresh |
| YUAN | Yahoo Finance | `CNY=X` | Trading days | Inferred; confirm on refresh |
| LIBRA | Yahoo Finance | `GBPUSD=X` | Trading days | Inferred; confirm on refresh |
| SSECOMPOSITE | Yahoo Finance | `000001.SS` | Trading days | Inferred; confirm on refresh |
| NASDAQ100 | Yahoo Finance | `^NDX` | Trading days | Verified by file fingerprint |
| DOWJONES | Yahoo Finance | `^DJI` | Trading days | Verified by file fingerprint |
| RUSSELL2000 | Yahoo Finance | `^RUT` | Trading days | Verified by file fingerprint |
| EUROSTOXX50 | Yahoo Finance | `^STOXX50E` | Trading days | Verified by file fingerprint |
| DAX | Yahoo Finance | `^GDAXI` | Trading days | Verified by file fingerprint |
| CAC40 | Yahoo Finance | `^FCHI` | Trading days | Verified by file fingerprint |
| NIKKEI225 | Yahoo Finance | `^N225` | Trading days | Verified by file fingerprint |
| EMERGING_MARKETS | Yahoo Finance | `EEM` | Trading days | Verified by file fingerprint |
| VIX | Yahoo Finance | `^VIX` | Trading days | Verified by file fingerprint |
| MOVE_INDEX | Yahoo Finance | `^MOVE` | Trading days | Verified by file fingerprint |
| BRENT_OIL | Yahoo Finance | `BZ=F` | Trading days | Verified by file fingerprint |
| WTI_OIL | Yahoo Finance | `CL=F` | Trading days | Verified by file fingerprint |
| NATURAL_GAS | Yahoo Finance | `NG=F` | Trading days | Verified by file fingerprint |
| COPPER | Yahoo Finance | `HG=F` | Trading days | Verified by file fingerprint |
| SILVER | Yahoo Finance | `SI=F` | Trading days | Verified by file fingerprint |
| WHEAT | Yahoo Finance | `ZW=F` | Trading days | Verified by file fingerprint |
| CORN | Yahoo Finance | `ZC=F` | Trading days | Verified by file fingerprint |
| YEN | Yahoo Finance | `JPY=X` | Trading days | Verified by file fingerprint |
| SWISS_FRANC | Yahoo Finance | `CHF=X` | Trading days | Verified by file fingerprint |
| US3M | Yahoo Finance | `^IRX` (13-week Treasury bill) | Trading days | Verified by exact overlap |
| US2Y | Federal Reserve H.15 | `RIFLGFCY02_N.B` / FRED `DGS2` | Trading days | Verified official series |
| US10Y | Yahoo Finance | `^TNX` | Trading days | Verified by file fingerprint |
| US30Y | Yahoo Finance | `^TYX` | Trading days | Verified by file fingerprint |
| GERMANY10Y | FRED / OECD | `IRLTLT01DEM156N` | Monthly | Verified by file fingerprint |
| UK10Y | FRED / OECD | `IRLTLT01GBM156N` | Monthly | Verified by file fingerprint |
| JAPAN10Y | FRED / OECD | `IRLTLT01JPM156N` | Monthly | Verified by file fingerprint |
| FINANCIAL_CONDITIONS | FRED | `NFCI` | Weekly | Verified by file fingerprint |
| TED_SPREAD | FRED | `TEDRATE` | Daily, discontinued | Verified by file fingerprint |

The exact URLs are kept in `market_source_manifest.py` so the Data Quality page
can expose a clickable source for every configured asset.

## Treasury Identity Correction

The historical file previously named `US2Y` was matched against Yahoo `^IRX` on
337 overlapping observations: all 337 values matched within `1e-6`. Yahoo
identifies `^IRX` as the 13-week Treasury bill, not a two-year yield.

Version 0.5.1 therefore applies these contracts:

- `US3M`: the preserved `^IRX` history, with native Yahoo OHLC;
- `US2Y`: Federal Reserve H.15 `RIFLGFCY02_N.B`, also exposed by FRED as `DGS2`;
- official US2Y OHLC remains null in storage and is labelled synthetic only when
  the analytical engine constructs it.

## FED Macro Sources

The 11 configured US macro files are FRED CSV downloads. Their exact series IDs
are: `FEDFUNDS`, `M2SL`, `WALCL`, `RSBKCRNS`, `DPSACBW027SBOG`, `TOTBKCR`,
`TOTLLNSA`, `SBCACBW027SBOG`, `CCLACBW027SBOG`, `DRCCLACBS` and `CORCCACBS`.
The canonical page for each is `https://fred.stlouisfed.org/series/<SERIES_ID>`.

## ECB Sources

The active ECB layer uses 12 monthly series from the ECB Data Portal:

- HICP: `ICP.M.U2.N.FOODPR.4.INX`, `ICP.M.U2.N.X02200.3.CTG`,
  `ICP.M.U2.Y.SERV00.3.INX`, `ICP.M.U2.Y.IGOODS.3.INX` and
  `ICP.M.U2.N.ADMEF0.4.INX`;
- MFI rates: `MIR.M.AT.B.A2A.A.R.A.2240.EUR.N`,
  `MIR.M.AT.B.A2B.A.R.A.2250.EUR.N`, `MIR.M.AT.B.A2C.A.R.A.2250.EUR.N`,
  `MIR.M.AT.B.A2Z.A.R.A.2240.EUR.N`, `MIR.M.AT.B.A2Z.A.R.A.2250.EUR.N`,
  `MIR.M.AT.B.L21.A.R.A.2240.EUR.N` and `MIR.M.AT.B.L21.A.R.A.2250.EUR.N`.

Four semiannual fraud series are registered but disabled until the analytical
layer is implemented: `PLB.H.B0.W0.CP0.1.1.F.N.EUR`,
`PLB.H.B0.W0.CT0.1.1.F.N.EUR`, `PLB.H.B0.W0.DD.2.1.F.N.EUR` and
`PLB.H.B0.W0.EMP0.1.1.F.N.EUR`.

## Refresh Workflow

Official US2Y refresh, validation only:

```powershell
.\Scripts\python.exe project_scripts\assets\refresh_official_sources.py US2Y
```

Replace only the local CSV after reviewing the output:

```powershell
.\Scripts\python.exe project_scripts\assets\refresh_official_sources.py US2Y --write-csv
```

Then review the SQL plan and explicitly apply one asset:

```powershell
.\Scripts\python.exe project_scripts\assets\sync_market_data.py US2Y
.\Scripts\python.exe project_scripts\assets\sync_market_data.py US2Y --update-sql
```

The refresh command never writes to MySQL. The synchronization command remains
read-only unless `--update-sql` is supplied.
