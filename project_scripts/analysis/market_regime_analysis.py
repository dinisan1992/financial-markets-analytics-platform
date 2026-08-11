from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import plotly.io as pio

from config import get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# SETTINGS
# =========================

START_DATE = "2020-01-01"
END_DATE = None

ROLLING_WINDOW = 30

EXPORT_REPORT = True

pio.renderers.default = "browser"


# =========================
# ASSETS USED IN THE REGIME
# =========================

REGIME_ASSETS = [
    "SP500",
    "NASDAQ100",
    "BTC",
    "VIX",
    "DXY",
    "US10Y",
    "GOLD",
    "BRENT_OIL",
    "FINANCIAL_CONDITIONS"
]


# =========================
# DATABASE CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# LOAD PRICES
# =========================

def load_asset(asset_key, start_date=None, end_date=None):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Asset not found: {asset_key}")

    asset = ASSETS[asset_key]
    table_name = asset["table_name"]

    query = f"""
    SELECT
        snapped_at,
        price
    FROM `{table_name}`
    ORDER BY snapped_at;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError(f"Empty table: {table_name}")

    df["snapped_at"] = pd.to_datetime(
        df["snapped_at"],
        errors="coerce"
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    df = df.dropna(subset=["snapped_at", "price"])
    df = df.sort_values("snapped_at").reset_index(drop=True)

    if start_date is not None:
        df = df[df["snapped_at"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["snapped_at"] <= pd.to_datetime(end_date)]

    if df.empty:
        raise ValueError(f"No data after filters: {asset_key}")

    df = df[["snapped_at", "price"]].copy()
    df = df.rename(columns={"price": asset_key})

    print(
        f"{asset_key:25s} | "
        f"{asset['display_name']:40s} | "
        f"{len(df):7d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# JUNTAR DADOS
# =========================

def load_data_regime(asset_keys):
    merged_df = None

    print("\nLoading assets para regime analysis:")
    print("-" * 120)

    for asset_key in asset_keys:
        try:
            df_asset = load_asset(
                asset_key=asset_key,
                start_date=START_DATE,
                end_date=END_DATE
            )

            if merged_df is None:
                merged_df = df_asset

            else:
                merged_df = pd.merge(
                    merged_df,
                    df_asset,
                    on="snapped_at",
                    how="outer"
                )

        except Exception as e:
            print(f"ERROR in {asset_key}: {e}")

    if merged_df is None or merged_df.empty:
        raise ValueError("No data was loaded.")

    merged_df = merged_df.sort_values("snapped_at").reset_index(drop=True)

    asset_cols = [
        col for col in merged_df.columns
        if col != "snapped_at"
    ]

    # For the daily regime, use forward fill to align calendars.
    merged_df[asset_cols] = merged_df[asset_cols].ffill()

    merged_df = merged_df.dropna(
        subset=[
            "SP500",
            "NASDAQ100",
            "VIX",
            "DXY",
            "US10Y"
        ]
    ).reset_index(drop=True)

    return merged_df


# =========================
# INDICADORES DE REGIME
# =========================

def calcular_features_regime(df):
    df = df.copy()

    price_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in price_cols:
        df[f"{col}_return_1d"] = df[col].pct_change()
        df[f"{col}_return_30d"] = df[col].pct_change(ROLLING_WINDOW)

    # Volatilidade realizada do S&P 500
    df["sp500_realized_vol_30d"] = (
        df["SP500_return_1d"]
        .rolling(ROLLING_WINDOW)
        .std()
        * (252 ** 0.5)
    )

    # Simple rolling averages for trend
    for col in ["SP500", "NASDAQ100", "BTC", "GOLD", "DXY", "BRENT_OIL"]:
        if col in df.columns:
            df[f"{col}_ma_30"] = df[col].rolling(30).mean()
            df[f"{col}_ma_90"] = df[col].rolling(90).mean()

    # Absolute changes in yields / stress
    if "US10Y" in df.columns:
        df["US10Y_change_30d"] = df["US10Y"] - df["US10Y"].shift(ROLLING_WINDOW)

    if "VIX" in df.columns:
        df["VIX_change_30d"] = df["VIX"] - df["VIX"].shift(ROLLING_WINDOW)

    if "FINANCIAL_CONDITIONS" in df.columns:
        df["FINANCIAL_CONDITIONS_change_30d"] = (
            df["FINANCIAL_CONDITIONS"]
            - df["FINANCIAL_CONDITIONS"].shift(ROLLING_WINDOW)
        )

    return df


# =========================
# CLASSIFICAR REGIME
# =========================

def classificar_linha(row):
    scores = {
        "risk_on": 0,
        "risk_off": 0,
        "high_volatility": 0,
        "dollar_strength": 0,
        "yield_pressure": 0,
        "commodity_shock": 0,
        "financial_stress": 0
    }

    # =========================
    # RISK ON
    # =========================

    if row.get("SP500_return_30d", 0) > 0.03:
        scores["risk_on"] += 1

    if row.get("NASDAQ100_return_30d", 0) > 0.04:
        scores["risk_on"] += 1

    if row.get("BTC_return_30d", 0) > 0.08:
        scores["risk_on"] += 1

    if row.get("VIX", 999) < 20:
        scores["risk_on"] += 1

    # =========================
    # RISK OFF
    # =========================

    if row.get("SP500_return_30d", 0) < -0.05:
        scores["risk_off"] += 1

    if row.get("NASDAQ100_return_30d", 0) < -0.06:
        scores["risk_off"] += 1

    if row.get("BTC_return_30d", 0) < -0.12:
        scores["risk_off"] += 1

    if row.get("VIX", 0) > 25:
        scores["risk_off"] += 1

    # =========================
    # HIGH VOLATILITY
    # =========================

    if row.get("VIX", 0) > 25:
        scores["high_volatility"] += 1

    if row.get("VIX_change_30d", 0) > 5:
        scores["high_volatility"] += 1

    if row.get("sp500_realized_vol_30d", 0) > 0.25:
        scores["high_volatility"] += 1

    # =========================
    # DOLLAR STRENGTH
    # =========================

    if row.get("DXY_return_30d", 0) > 0.02:
        scores["dollar_strength"] += 1

    if row.get("GOLD_return_30d", 0) < 0:
        scores["dollar_strength"] += 1

    if row.get("BTC_return_30d", 0) < 0:
        scores["dollar_strength"] += 1

    # =========================
    # YIELD PRESSURE
    # =========================

    if row.get("US10Y_change_30d", 0) > 0.25:
        scores["yield_pressure"] += 1

    if row.get("NASDAQ100_return_30d", 0) < -0.04:
        scores["yield_pressure"] += 1

    if row.get("GOLD_return_30d", 0) < 0:
        scores["yield_pressure"] += 1

    # =========================
    # COMMODITY SHOCK
    # =========================

    if row.get("BRENT_OIL_return_30d", 0) > 0.10:
        scores["commodity_shock"] += 1

    if row.get("BRENT_OIL_return_30d", 0) < -0.15:
        scores["commodity_shock"] += 1

    # =========================
    # FINANCIAL STRESS
    # =========================

    if row.get("FINANCIAL_CONDITIONS_change_30d", 0) > 0.15:
        scores["financial_stress"] += 1

    if row.get("VIX", 0) > 30:
        scores["financial_stress"] += 1

    if row.get("SP500_return_30d", 0) < -0.07:
        scores["financial_stress"] += 1

    # =========================
    # FINAL DECISION
    # =========================

    max_score = max(scores.values())

    if max_score == 0:
        return "neutral"

    winners = [
        regime for regime, score in scores.items()
        if score == max_score
    ]

    if len(winners) > 1:
        return "mixed_" + "_".join(winners[:2])

    return winners[0]


def classificar_regimes(df):
    df = df.copy()

    df["market_regime"] = df.apply(
        classificar_linha,
        axis=1
    )

    return df


# =========================
# SUMMARY
# =========================

def mostrar_summary_regimes(df):
    print("\n" + "=" * 120)
    print("SUMMARY DE REGIMES")
    print("=" * 120)

    regime_counts = (
        df["market_regime"]
        .value_counts()
        .reset_index()
    )

    regime_counts.columns = [
        "market_regime",
        "days"
    ]

    regime_counts["pct"] = (
        regime_counts["days"] / len(df) * 100
    ).round(2)

    print(regime_counts)

    print("\nLast 30 classified days:")
    print(
        df[
            [
                "snapped_at",
                "SP500_return_30d",
                "NASDAQ100_return_30d",
                "BTC_return_30d",
                "VIX",
                "DXY_return_30d",
                "US10Y_change_30d",
                "BRENT_OIL_return_30d",
                "market_regime"
            ]
        ]
        .tail(30)
        .round(4)
    )

    print("=" * 120)

    return regime_counts


# =========================
# MAPA DE REGIMES PARA CHART
# =========================

def regime_to_numeric(regime):
    mapping = {
        "neutral": 0,
        "risk_on": 1,
        "risk_off": -1,
        "high_volatility": -2,
        "dollar_strength": -3,
        "yield_pressure": -4,
        "commodity_shock": 2,
        "financial_stress": -5
    }

    if regime in mapping:
        return mapping[regime]

    if regime.startswith("mixed"):
        return -0.5

    return 0


# =========================
# CHART
# =========================

def gerar_grafico_regimes(df):
    df = df.copy()

    df["regime_numeric"] = df["market_regime"].apply(regime_to_numeric)

    fig = go.Figure()

    # Linha SP500 normalizada
    sp500_base = df["SP500"].dropna().iloc[0]
    df["SP500_base100"] = (df["SP500"] / sp500_base) * 100

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df["SP500_base100"],
            mode="lines",
            name="S&P 500 Base 100",
            yaxis="y1",
            hovertemplate=(
                "<b>S&P 500</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Base 100: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )

    # Regime como linha separada
    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df["regime_numeric"],
            mode="lines",
            name="Market Regime Score",
            yaxis="y2",
            line=dict(
                width=2,
                dash="dot"
            ),
            hovertemplate=(
                "<b>Market Regime</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Score: %{y:.2f}<br>"
                "<extra></extra>"
            )
        )
    )

    # Pontos por regime
    regimes = df["market_regime"].dropna().unique()

    for regime in regimes:
        regime_df = df[df["market_regime"] == regime]

        fig.add_trace(
            go.Scatter(
                x=regime_df["snapped_at"],
                y=regime_df["SP500_base100"],
                mode="markers",
                name=f"Regime: {regime}",
                marker=dict(
                    size=5
                ),
                yaxis="y1",
                hovertemplate=(
                    f"<b>{regime}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "S&P 500 Base 100: %{y:.2f}"
                    "<extra></extra>"
                )
            )
        )

    fig.update_layout(
        title=dict(
            text=(
                "Market Regime Analysis"
                f" | From {START_DATE if START_DATE else 'Start'}"
            ),
            x=0.5,
            xanchor="center",
            font=dict(
                size=20,
                color="white"
            )
        ),
        template="plotly_dark",
        height=850,
        width=1550,
        hovermode="x unified",
        xaxis=dict(
            title="Date",
            gridcolor="rgba(255,255,255,0.12)"
        ),
        yaxis=dict(
            title="S&P 500 Base 100",
            side="left",
            gridcolor="rgba(255,255,255,0.12)"
        ),
        yaxis2=dict(
            title="Regime Score",
            overlaying="y",
            side="right",
            range=[-5.5, 2.5],
            showgrid=False
        ),
        margin=dict(
            l=80,
            r=220,
            t=100,
            b=70
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(
                size=10,
                color="white"
            ),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.25)",
            borderwidth=1
        ),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117"
    )

    fig.update_xaxes(
        rangeslider_visible=False,
        rangeselector=dict(
            bgcolor="#1E1E1E",
            activecolor="#4A90E2",
            bordercolor="#FFFFFF",
            borderwidth=1,
            font=dict(
                color="#FFFFFF",
                size=12
            ),
            x=0.01,
            y=1.08,
            buttons=list([
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=3, label="3Y", step="year", stepmode="backward"),
                dict(count=5, label="5Y", step="year", stepmode="backward"),
                dict(count=10, label="10Y", step="year", stepmode="backward"),
                dict(step="all", label="ALL")
            ])
        )
    )

    fig.show(
        config={
            "scrollZoom": True,
            "displayModeBar": True
        }
    )

    return fig


# =========================
# EXPORTAR
# =========================

def export_resultados(df, regime_counts):
    if not EXPORT_REPORT:
        return

    df.to_csv(
        "market_regime_analysis.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    regime_counts.to_csv(
        "market_regime_summary.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nReports exported:")
    print("market_regime_analysis.csv")
    print("market_regime_summary.csv")


# =========================
# MAIN
# =========================

def main():
    print("\nA iniciar Market Regime Analysis...")
    print(f"Start date: {START_DATE}")
    print(f"End date: {END_DATE}")
    print(f"Rolling window: {ROLLING_WINDOW}")

    df = load_data_regime(REGIME_ASSETS)

    print("\nData combinados:")
    print(f"Rows: {len(df)}")
    print(f"Minimum date: {df['snapped_at'].min().date()}")
    print(f"Maximum date: {df['snapped_at'].max().date()}")

    print("\nA calcular features de regime...")
    df = calcular_features_regime(df)

    print("A classificar regimes...")
    df = classificar_regimes(df)

    regime_counts = mostrar_summary_regimes(df)

    print("\nGenerating chart...")
    gerar_grafico_regimes(df)

    export_resultados(
        df=df,
        regime_counts=regime_counts
    )

    print("\nMarket Regime Analysis completed.")


if __name__ == "__main__":
    main()
