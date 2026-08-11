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

EXPORT_REPORT = True

pio.renderers.default = "browser"


# =========================
# PARES PREDEFINIDOS
# =========================

OVERLAY_CONFIGS = {
    "nasdaq_us10y": {
        "market_asset": "NASDAQ100",
        "macro_asset": "US10Y",
        "label": "NASDAQ 100 vs US 10Y Yield",
        "description": "Tecnologia/growth stocks contra yields longas."
    },

    "sp500_vix": {
        "market_asset": "SP500",
        "macro_asset": "VIX",
        "label": "S&P 500 vs VIX",
        "description": "Market acionista contra volatilidade/stress."
    },

    "sp500_financial_conditions": {
        "market_asset": "SP500",
        "macro_asset": "FINANCIAL_CONDITIONS",
        "label": "S&P 500 vs Financial Conditions",
        "description": "Equity market vs financial conditions."
    },

    "btc_dxy": {
        "market_asset": "BTC",
        "macro_asset": "DXY",
        "label": "BTC vs DXY",
        "description": "Bitcoin vs dollar strength."
    },

    "btc_us10y": {
        "market_asset": "BTC",
        "macro_asset": "US10Y",
        "label": "BTC vs US 10Y Yield",
        "description": "Bitcoin contra yields longas."
    },

    "gold_dxy": {
        "market_asset": "GOLD",
        "macro_asset": "DXY",
        "label": "Gold vs DXY",
        "description": "Gold vs dollar."
    },

    "gold_us10y": {
        "market_asset": "GOLD",
        "macro_asset": "US10Y",
        "label": "Gold vs US 10Y Yield",
        "description": "Ouro contra yields longas."
    },

    "brent_dxy": {
        "market_asset": "BRENT_OIL",
        "macro_asset": "DXY",
        "label": "Brent Oil vs DXY",
        "description": "Oil vs dollar."
    },

    "brent_us10y": {
        "market_asset": "BRENT_OIL",
        "macro_asset": "US10Y",
        "label": "Brent Oil vs US 10Y Yield",
        "description": "Oil vs long yields."
    },

    "nasdaq_move": {
        "market_asset": "NASDAQ100",
        "macro_asset": "MOVE_INDEX",
        "label": "NASDAQ 100 vs MOVE Index",
        "description": "Tecnologia contra volatilidade obrigacionista."
    },

    "sp500_us10y": {
        "market_asset": "SP500",
        "macro_asset": "US10Y",
        "label": "S&P 500 vs US 10Y Yield",
        "description": "Market acionista contra yields longas."
    },

    "vix_move": {
        "market_asset": "VIX",
        "macro_asset": "MOVE_INDEX",
        "label": "VIX vs MOVE Index",
        "description": "Volatilidade acionista contra volatilidade obrigacionista."
    }
}


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# MENU DE PARES
# =========================

def mostrar_menu_overlays():
    print("\n" + "=" * 110)
    print("SELETOR MACRO-MARKET OVERLAY")
    print("=" * 110)

    overlay_items = list(OVERLAY_CONFIGS.items())

    for i, (overlay_key, overlay_data) in enumerate(overlay_items, start=1):
        print(
            f"{i:02d} - "
            f"{overlay_data['label']} "
            f"| {overlay_data['description']}"
        )

    print("=" * 110)
    print("98 - Par personalizado")
    print("0  - Exit")
    print("=" * 110)

    return overlay_items


def chooser_overlay(overlay_items):
    while True:
        choice = input("\nChoose o overlay: ").strip()

        if choice == "0":
            return None

        if choice == "98":
            return chooser_overlay_personalizado()

        if not choice.isdigit():
            print("Invalid choice. Enter the number only.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(overlay_items):
            print("Number outside the list.")
            continue

        return overlay_items[choice_num - 1]


def chooser_overlay_personalizado():
    print("\nAvailable assets:")
    print("-" * 100)

    asset_keys = list(ASSETS.keys())

    for i, asset_key in enumerate(asset_keys, start=1):
        asset = ASSETS[asset_key]

        print(
            f"{i:02d} - "
            f"{asset_key:22s} | "
            f"{asset['display_name']} | "
            f"{asset['market_type']}"
        )

    print("-" * 100)

    market_asset = chooser_asset_key(
        asset_keys=asset_keys,
        label="asset de market / eixo esquerdo"
    )

    macro_asset = chooser_asset_key(
        asset_keys=asset_keys,
        label="indicador macro / eixo direito"
    )

    overlay_key = f"custom_{market_asset.lower()}_{macro_asset.lower()}"

    overlay_data = {
        "market_asset": market_asset,
        "macro_asset": macro_asset,
        "label": (
            f"{ASSETS[market_asset]['display_name']} "
            f"vs {ASSETS[macro_asset]['display_name']}"
        ),
        "description": "Overlay personalizado escolhido manualmente."
    }

    return overlay_key, overlay_data


def chooser_asset_key(asset_keys, label):
    while True:
        choice = input(f"\nChoose the number for {label}: ").strip()

        if not choice.isdigit():
            print("Invalid choice. Enter the number only.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(asset_keys):
            print("Number outside the list.")
            continue

        return asset_keys[choice_num - 1]


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
# CARREGAR ATIVO
# =========================

def load_asset(asset_key, start_date=None, end_date=None):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Asset not found: {asset_key}")

    asset = ASSETS[asset_key]
    table_name = asset["table_name"]
    display_name = asset["display_name"]

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
        f"{asset_key:22s} | "
        f"{display_name:40s} | "
        f"{len(df):7d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# PREPARAR OVERLAY
# =========================

def preparar_overlay(market_asset, macro_asset, start_date=None, end_date=None):
    print("\n" + "=" * 110)
    print(f"A preparar overlay: {market_asset} vs {macro_asset}")
    print("=" * 110)

    df_market = load_asset(
        asset_key=market_asset,
        start_date=start_date,
        end_date=end_date
    )

    df_macro = load_asset(
        asset_key=macro_asset,
        start_date=start_date,
        end_date=end_date
    )

    merged = pd.merge(
        df_market,
        df_macro,
        on="snapped_at",
        how="outer"
    )

    merged = merged.sort_values("snapped_at").reset_index(drop=True)

    merged[[market_asset, macro_asset]] = (
        merged[[market_asset, macro_asset]]
        .ffill()
    )

    merged = merged.dropna(
        subset=[market_asset, macro_asset]
    ).reset_index(drop=True)

    if merged.empty:
        raise ValueError(
            f"No data comuns after alinhamento: {market_asset} vs {macro_asset}"
        )

    market_base = merged[market_asset].dropna().iloc[0]

    if market_base == 0:
        raise ValueError(f"Base value is zero para {market_asset}")

    merged[f"{market_asset}_base100"] = (
        merged[market_asset] / market_base
    ) * 100

    merged[f"{market_asset}_return_30d"] = (
        merged[market_asset]
        .pct_change(30)
    )

    merged[f"{macro_asset}_change_30d"] = (
        merged[macro_asset]
        - merged[macro_asset].shift(30)
    )

    merged[f"{macro_asset}_return_30d"] = (
        merged[macro_asset]
        .pct_change(30)
    )

    print(f"Rows combinadas: {len(merged)}")
    print(f"Minimum date: {merged['snapped_at'].min().date()}")
    print(f"Maximum date: {merged['snapped_at'].max().date()}")

    return merged


# =========================
# SUMMARY
# =========================

def mostrar_summary_overlay(df, market_asset, macro_asset, label):
    print("\n" + "=" * 110)
    print(f"SUMMARY OVERLAY - {label}")
    print("=" * 110)

    market_return_total = (
        (df[market_asset].iloc[-1] / df[market_asset].iloc[0]) - 1
    ) * 100

    macro_start = df[macro_asset].iloc[0]
    macro_end = df[macro_asset].iloc[-1]
    macro_change = macro_end - macro_start

    market_return_30_col = f"{market_asset}_return_30d"
    macro_change_30_col = f"{macro_asset}_change_30d"
    macro_return_30_col = f"{macro_asset}_return_30d"

    summary = {
        "market_asset": market_asset,
        "macro_asset": macro_asset,
        "start_date": df["snapped_at"].min().date(),
        "end_date": df["snapped_at"].max().date(),
        "market_start": round(df[market_asset].iloc[0], 4),
        "market_end": round(df[market_asset].iloc[-1], 4),
        "market_total_return_pct": round(market_return_total, 2),
        "macro_start": round(macro_start, 4),
        "macro_end": round(macro_end, 4),
        "macro_absolute_change": round(macro_change, 4),
        "market_30d_return_mean_pct": round(
            df[market_return_30_col].mean() * 100,
            2
        ),
        "macro_30d_change_mean": round(
            df[macro_change_30_col].mean(),
            4
        )
    }

    summary_df = pd.DataFrame([summary])

    print(summary_df)

    print("\nCorrelation between 30D market return and 30D macro change:")

    corr_df = df[
        [
            market_return_30_col,
            macro_change_30_col,
            macro_return_30_col
        ]
    ].dropna()

    corr_change = None
    corr_return = None

    if len(corr_df) >= 30:
        corr_change = corr_df[market_return_30_col].corr(
            corr_df[macro_change_30_col]
        )

        corr_return = corr_df[market_return_30_col].corr(
            corr_df[macro_return_30_col]
        )

        print(f"Corr market return 30D vs macro change 30D: {corr_change:.4f}")
        print(f"Corr market return 30D vs macro return 30D: {corr_return:.4f}")

    else:
        print("Observations insuficientes.")

    print("=" * 110)

    return summary_df, corr_change, corr_return


# =========================
# CHART
# =========================

def gerar_grafico_overlay(
    df,
    market_asset,
    macro_asset,
    label,
    description,
    period_label
):
    market_name = ASSETS[market_asset]["display_name"]
    macro_name = ASSETS[macro_asset]["display_name"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df[f"{market_asset}_base100"],
            mode="lines",
            name=f"{market_name} Base 100",
            yaxis="y1",
            hovertemplate=(
                f"<b>{market_name}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Base 100: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df[macro_asset],
            mode="lines",
            name=macro_name,
            yaxis="y2",
            line=dict(
                dash="dot",
                width=2
            ),
            hovertemplate=(
                f"<b>{macro_name}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Value: %{y:.4f}"
                "<extra></extra>"
            )
        )
    )

    fig.add_hline(
        y=100,
        line_dash="dash",
        opacity=0.5,
        annotation_text="Market Base 100",
        annotation_position="bottom right",
        yref="y1"
    )

    fig.update_layout(
        title=dict(
            text=(
                f"Macro-Market Overlay - {label}"
                f" | {period_label}"
            ),
            x=0.5,
            xanchor="center",
            font=dict(
                size=20,
                color="white"
            )
        ),
        template="plotly_dark",
        height=800,
        width=1500,
        hovermode="x unified",
        xaxis=dict(
            title="Date",
            gridcolor="rgba(255,255,255,0.12)"
        ),
        yaxis=dict(
            title=f"{market_name} Base 100",
            side="left",
            gridcolor="rgba(255,255,255,0.12)"
        ),
        yaxis2=dict(
            title=macro_name,
            overlaying="y",
            side="right",
            showgrid=False
        ),
        margin=dict(
            l=80,
            r=230,
            t=115,
            b=70
        ),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(
                size=11,
                color="white"
            ),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.25)",
            borderwidth=1
        ),
        annotations=[
            dict(
                text=description,
                xref="paper",
                yref="paper",
                x=0,
                y=1.11,
                showarrow=False,
                font=dict(
                    size=11,
                    color="white"
                ),
                bgcolor="rgba(0,0,0,0.45)",
                bordercolor="rgba(255,255,255,0.25)",
                borderwidth=1
            )
        ],
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
        ),
        gridcolor="rgba(255,255,255,0.12)",
        tickfont=dict(color="white"),
        title_font=dict(color="white")
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.12)",
        tickfont=dict(color="white"),
        title_font=dict(color="white")
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

def export_resultados(df, summary_df, market_asset, macro_asset, period_label):
    if not EXPORT_REPORT:
        return

    safe_period = (
        period_label
        .replace(" ", "_")
        .replace("/", "_")
        .replace(":", "_")
        .lower()
    )

    safe_name = f"{market_asset.lower()}_{macro_asset.lower()}_{safe_period}"

    overlay_output = f"macro_market_overlay_{safe_name}.csv"
    summary_output = f"macro_market_overlay_summary_{safe_name}.csv"

    df.to_csv(
        overlay_output,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    summary_df.to_csv(
        summary_output,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nReports exported:")
    print(overlay_output)
    print(summary_output)


# =========================
# EXECUTAR
# =========================

def executar_overlay(overlay_key, overlay_data):
    start_date, end_date, period_label = chooser_periodo()

    market_asset = overlay_data["market_asset"]
    macro_asset = overlay_data["macro_asset"]
    label = overlay_data["label"]
    description = overlay_data["description"]

    print("\n" + "=" * 120)
    print("MACRO-MARKET OVERLAY")
    print("=" * 120)
    print(f"Overlay: {label}")
    print(f"Description: {description}")
    print(f"Market asset: {market_asset} | {ASSETS[market_asset]['display_name']}")
    print(f"Macro asset: {macro_asset} | {ASSETS[macro_asset]['display_name']}")
    print(f"Period: {period_label}")
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print("=" * 120)

    df = preparar_overlay(
        market_asset=market_asset,
        macro_asset=macro_asset,
        start_date=start_date,
        end_date=end_date
    )

    summary_df, corr_change, corr_return = mostrar_summary_overlay(
        df=df,
        market_asset=market_asset,
        macro_asset=macro_asset,
        label=label
    )

    gerar_grafico_overlay(
        df=df,
        market_asset=market_asset,
        macro_asset=macro_asset,
        label=label,
        description=description,
        period_label=period_label
    )

    export_resultados(
        df=df,
        summary_df=summary_df,
        market_asset=market_asset,
        macro_asset=macro_asset,
        period_label=period_label
    )

    print("\nMacro-Market Overlay completed.")


# =========================
# MAIN
# =========================

def main():
    while True:
        overlay_items = mostrar_menu_overlays()

        selected_overlay = chooser_overlay(overlay_items)

        if selected_overlay is None:
            print("\nExiting the Macro-Market Overlay selector.")
            break

        overlay_key, overlay_data = selected_overlay

        try:
            executar_overlay(
                overlay_key=overlay_key,
                overlay_data=overlay_data
            )

        except Exception as e:
            print("\nERROR while running Macro-Market Overlay:")
            print(e)

        input("\nPressiona ENTER para voltar ao menu...")


if __name__ == "__main__":
    main()
