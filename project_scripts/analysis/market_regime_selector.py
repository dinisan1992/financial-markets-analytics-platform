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
# GENERAL SETTINGS
# =========================

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
# REFERENCE ASSETS FOR CHART
# =========================

REFERENCE_ASSETS = [
    "SP500",
    "NASDAQ100",
    "BTC",
    "GOLD",
    "DXY",
    "BRENT_OIL",
    "VIX",
    "US10Y"
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
# PERIOD MENU
# =========================

def calcular_data_inicio_anos(anos):
    hoje = pd.Timestamp.today().normalize()
    data_inicio = hoje - pd.DateOffset(years=anos)

    return data_inicio.strftime("%Y-%m-%d")


def chooser_periodo_personalizado():
    print("\nRecommended format: YYYY-MM-DD")
    print("Example: 2015-01-01")

    while True:
        start_date = input("\nStart date: ").strip()

        try:
            pd.to_datetime(start_date)
            break

        except Exception:
            print("Invalid start date. Use the YYYY-MM-DD format.")

    end_date = input("End date or ENTER to use the end: ").strip()

    if end_date == "":
        end_date = None

    else:
        try:
            pd.to_datetime(end_date)

        except Exception:
            print("Invalid end date. Using the end.")
            end_date = None

    label = f"{start_date} until {end_date if end_date else 'end'}"

    return start_date, end_date, label


def chooser_periodo():
    print("\n" + "=" * 80)
    print("CHOOSE PERIOD")
    print("=" * 80)
    print("1 - Since 2020")
    print("2 - Last 1 year")
    print("3 - Last 3 years")
    print("4 - Last 5 years")
    print("5 - Last 10 years")
    print("6 - Full available history")
    print("7 - Custom date")
    print("=" * 80)

    while True:
        choice = input("\nChoose the period: ").strip()

        if choice == "1":
            return "2020-01-01", None, "Since 2020"

        elif choice == "2":
            return calcular_data_inicio_anos(1), None, "Last 1 year"

        elif choice == "3":
            return calcular_data_inicio_anos(3), None, "Last 3 years"

        elif choice == "4":
            return calcular_data_inicio_anos(5), None, "Last 5 years"

        elif choice == "5":
            return calcular_data_inicio_anos(10), None, "Last 10 years"

        elif choice == "6":
            return None, None, "Full history"

        elif choice == "7":
            return chooser_periodo_personalizado()

        else:
            print("Invalid choice. Enter a number from 1 to 7.")


# =========================
# MENU DE WINDOW
# =========================

def chooser_rolling_window():
    print("\n" + "=" * 80)
    print("ESCOLHER JANELA DE REGIME")
    print("=" * 80)
    print("1 - 20 dias")
    print("2 - 30 dias")
    print("3 - 60 dias")
    print("4 - 90 dias")
    print("5 - Personalizado")
    print("=" * 80)

    while True:
        choice = input("\nChoose a janela: ").strip()

        if choice == "1":
            return 20, "20D"

        elif choice == "2":
            return 30, "30D"

        elif choice == "3":
            return 60, "60D"

        elif choice == "4":
            return 90, "90D"

        elif choice == "5":
            return chooser_rolling_window_personalizada()

        else:
            print("Invalid choice. Enter a number de 1 a 5.")


def chooser_rolling_window_personalizada():
    while True:
        texto = input("\nIntroduz a janela em dias: ").strip()

        try:
            window = int(texto)

            if window < 5:
                print("A janela deve ser pelo menos 5 dias.")
                continue

            return window, f"{window}D"

        except Exception:
            print("Invalid value. Enter a number inteiro.")


# =========================
# REFERENCE ASSET MENU
# =========================

def chooser_reference_asset():
    print("\n" + "=" * 90)
    print("CHOOSE REFERENCE ASSET FOR THE CHART")
    print("=" * 90)

    for i, asset_key in enumerate(REFERENCE_ASSETS, start=1):
        asset = ASSETS[asset_key]

        print(
            f"{i:02d} - "
            f"{asset_key:15s} | "
            f"{asset['display_name']} | "
            f"{asset['market_type']}"
        )

    print("=" * 90)

    while True:
        choice = input("\nChoose the reference asset: ").strip()

        if not choice.isdigit():
            print("Invalid choice. Enter the number only.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(REFERENCE_ASSETS):
            print("Number outside the list.")
            continue

        return REFERENCE_ASSETS[choice_num - 1]


# =========================
# CARREGAR ATIVO
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

def load_data_regime(asset_keys, start_date=None, end_date=None):
    merged_df = None

    print("\nLoading assets para regime analysis:")
    print("-" * 120)

    for asset_key in asset_keys:
        try:
            df_asset = load_asset(
                asset_key=asset_key,
                start_date=start_date,
                end_date=end_date
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

    merged_df[asset_cols] = merged_df[asset_cols].ffill()

    required_cols = [
        "SP500",
        "NASDAQ100",
        "VIX",
        "DXY",
        "US10Y"
    ]

    available_required = [
        col for col in required_cols
        if col in merged_df.columns
    ]

    merged_df = merged_df.dropna(
        subset=available_required
    ).reset_index(drop=True)

    return merged_df


# =========================
# FEATURES DE REGIME
# =========================

def calcular_features_regime(df, rolling_window):
    df = df.copy()

    price_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in price_cols:
        df[f"{col}_return_1d"] = df[col].pct_change()
        df[f"{col}_return_window"] = df[col].pct_change(rolling_window)

    df["sp500_realized_vol_window"] = (
        df["SP500_return_1d"]
        .rolling(rolling_window)
        .std()
        * (252 ** 0.5)
    )

    for col in ["SP500", "NASDAQ100", "BTC", "GOLD", "DXY", "BRENT_OIL"]:
        if col in df.columns:
            df[f"{col}_ma_short"] = df[col].rolling(rolling_window).mean()
            df[f"{col}_ma_long"] = df[col].rolling(rolling_window * 3).mean()

    if "US10Y" in df.columns:
        df["US10Y_change_window"] = (
            df["US10Y"] - df["US10Y"].shift(rolling_window)
        )

    if "VIX" in df.columns:
        df["VIX_change_window"] = (
            df["VIX"] - df["VIX"].shift(rolling_window)
        )

    if "FINANCIAL_CONDITIONS" in df.columns:
        df["FINANCIAL_CONDITIONS_change_window"] = (
            df["FINANCIAL_CONDITIONS"]
            - df["FINANCIAL_CONDITIONS"].shift(rolling_window)
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

    # Risk-on
    if row.get("SP500_return_window", 0) > 0.03:
        scores["risk_on"] += 1

    if row.get("NASDAQ100_return_window", 0) > 0.04:
        scores["risk_on"] += 1

    if row.get("BTC_return_window", 0) > 0.08:
        scores["risk_on"] += 1

    if row.get("VIX", 999) < 20:
        scores["risk_on"] += 1

    # Risk-off
    if row.get("SP500_return_window", 0) < -0.05:
        scores["risk_off"] += 1

    if row.get("NASDAQ100_return_window", 0) < -0.06:
        scores["risk_off"] += 1

    if row.get("BTC_return_window", 0) < -0.12:
        scores["risk_off"] += 1

    if row.get("VIX", 0) > 25:
        scores["risk_off"] += 1

    # High volatility
    if row.get("VIX", 0) > 25:
        scores["high_volatility"] += 1

    if row.get("VIX_change_window", 0) > 5:
        scores["high_volatility"] += 1

    if row.get("sp500_realized_vol_window", 0) > 0.25:
        scores["high_volatility"] += 1

    # Dollar strength
    if row.get("DXY_return_window", 0) > 0.02:
        scores["dollar_strength"] += 1

    if row.get("GOLD_return_window", 0) < 0:
        scores["dollar_strength"] += 1

    if row.get("BTC_return_window", 0) < 0:
        scores["dollar_strength"] += 1

    # Yield pressure
    if row.get("US10Y_change_window", 0) > 0.25:
        scores["yield_pressure"] += 1

    if row.get("NASDAQ100_return_window", 0) < -0.04:
        scores["yield_pressure"] += 1

    if row.get("GOLD_return_window", 0) < 0:
        scores["yield_pressure"] += 1

    # Commodity shock
    if row.get("BRENT_OIL_return_window", 0) > 0.10:
        scores["commodity_shock"] += 1

    if row.get("BRENT_OIL_return_window", 0) < -0.15:
        scores["commodity_shock"] += 1

    # Financial stress
    if row.get("FINANCIAL_CONDITIONS_change_window", 0) > 0.15:
        scores["financial_stress"] += 1

    if row.get("VIX", 0) > 30:
        scores["financial_stress"] += 1

    if row.get("SP500_return_window", 0) < -0.07:
        scores["financial_stress"] += 1

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

def mostrar_summary_regimes(df, rolling_window):
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

    cols = [
        "snapped_at",
        "SP500_return_window",
        "NASDAQ100_return_window",
        "BTC_return_window",
        "VIX",
        "DXY_return_window",
        "US10Y_change_window",
        "BRENT_OIL_return_window",
        "market_regime"
    ]

    existing_cols = [
        col for col in cols
        if col in df.columns
    ]

    print(f"\nLast 30 classified days | janela {rolling_window}D:")
    print(
        df[existing_cols]
        .tail(30)
        .round(4)
    )

    print("=" * 120)

    return regime_counts


# =========================
# NUMERIC REGIME
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

    if isinstance(regime, str) and regime.startswith("mixed"):
        return -0.5

    return 0


# =========================
# CHART
# =========================

def gerar_grafico_regimes(df, reference_asset, period_label, window_label):
    df = df.copy()

    df["regime_numeric"] = df["market_regime"].apply(regime_to_numeric)

    fig = go.Figure()

    reference_name = ASSETS[reference_asset]["display_name"]

    ref_base = df[reference_asset].dropna().iloc[0]
    df[f"{reference_asset}_base100"] = (
        df[reference_asset] / ref_base
    ) * 100

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df[f"{reference_asset}_base100"],
            mode="lines",
            name=f"{reference_name} Base 100",
            yaxis="y1",
            hovertemplate=(
                f"<b>{reference_name}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Base 100: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )

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
                "<b>Market Regime Score</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Score: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )

    regimes = df["market_regime"].dropna().unique()

    for regime in regimes:
        regime_df = df[df["market_regime"] == regime]

        fig.add_trace(
            go.Scatter(
                x=regime_df["snapped_at"],
                y=regime_df[f"{reference_asset}_base100"],
                mode="markers",
                name=f"Regime: {regime}",
                marker=dict(
                    size=5
                ),
                yaxis="y1",
                hovertemplate=(
                    f"<b>{regime}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    f"{reference_name} Base 100: "
                    "%{y:.2f}"
                    "<extra></extra>"
                )
            )
        )

    fig.update_layout(
        title=dict(
            text=(
                f"Market Regime Analysis - {reference_name}"
                f" | {period_label}"
                f" | Window: {window_label}"
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
            title=f"{reference_name} Base 100",
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
            r=240,
            t=110,
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

def export_resultados(df, regime_counts, reference_asset, window_label):
    if not EXPORT_REPORT:
        return

    safe_ref = reference_asset.lower()
    safe_window = window_label.lower().replace("/", "_")

    analysis_output = f"market_regime_analysis_{safe_ref}_{safe_window}.csv"
    summary_output = f"market_regime_summary_{safe_ref}_{safe_window}.csv"

    df.to_csv(
        analysis_output,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    regime_counts.to_csv(
        summary_output,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nReports exported:")
    print(analysis_output)
    print(summary_output)


# =========================
# EXECUTAR
# =========================

def executar_regime_analysis():
    start_date, end_date, period_label = chooser_periodo()
    rolling_window, window_label = chooser_rolling_window()
    reference_asset = chooser_reference_asset()

    print("\n" + "=" * 120)
    print("MARKET REGIME ANALYSIS")
    print("=" * 120)
    print(f"Period: {period_label}")
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print(f"Rolling window: {rolling_window}")
    print(f"Reference asset: {reference_asset} | {ASSETS[reference_asset]['display_name']}")
    print(f"Assets usados no regime: {REGIME_ASSETS}")
    print("=" * 120)

    assets_to_load = list(set(REGIME_ASSETS + [reference_asset]))

    df = load_data_regime(
        asset_keys=assets_to_load,
        start_date=start_date,
        end_date=end_date
    )

    print("\nData combinados:")
    print(f"Rows: {len(df)}")
    print(f"Minimum date: {df['snapped_at'].min().date()}")
    print(f"Maximum date: {df['snapped_at'].max().date()}")

    print("\nA calcular features de regime...")
    df = calcular_features_regime(
        df=df,
        rolling_window=rolling_window
    )

    print("A classificar regimes...")
    df = classificar_regimes(df)

    regime_counts = mostrar_summary_regimes(
        df=df,
        rolling_window=rolling_window
    )

    print("\nGenerating chart...")
    gerar_grafico_regimes(
        df=df,
        reference_asset=reference_asset,
        period_label=period_label,
        window_label=window_label
    )

    export_resultados(
        df=df,
        regime_counts=regime_counts,
        reference_asset=reference_asset,
        window_label=window_label
    )

    print("\nMarket Regime Analysis completed.")


# =========================
# MAIN
# =========================

def main():
    while True:
        print("\n" + "=" * 90)
        print("SELETOR DE MARKET REGIME ANALYSIS")
        print("=" * 90)
        print("1 - Executar analysis de regime")
        print("0 - Exit")
        print("=" * 90)

        choice = input("\nChoose an option: ").strip()

        if choice == "0":
            print("\nExiting the regime selector.")
            break

        elif choice == "1":
            try:
                executar_regime_analysis()

            except Exception as e:
                print("\nERROR while running Market Regime Analysis:")
                print(e)

            input("\nPressiona ENTER para voltar ao menu...")

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
