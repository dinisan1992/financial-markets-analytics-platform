from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# GENERAL SETTINGS
# =========================

DEFAULT_START_DATE = "2020-01-01"
DEFAULT_END_DATE = None

LIMIT_LAST_ROWS = None

USE_LOG_SCALE = False


# =========================
# ANALYSIS GROUPS
# =========================

GROUPS = {
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
# DATABASE CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# GROUP MENU
# =========================

def mostrar_menu_grupos():
    print("\n" + "=" * 110)
    print("SELETOR DE PERFORMANCE NORMALIZADA - GROUPS DE MERCADO")
    print("=" * 110)

    group_items = list(GROUPS.items())

    for i, (group_key, group_data) in enumerate(group_items, start=1):
        print(
            f"{i:02d} - "
            f"{group_data['name']} "
            f"| {group_data['description']}"
        )

    print("=" * 110)
    print("0 - Exit")
    print("=" * 110)

    return group_items


def chooser_grupo(group_items):
    while True:
        choice = input("\nChoose the group number: ").strip()

        if choice == "0":
            return None

        if not choice.isdigit():
            print("Invalid choice. Enter the number only.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(group_items):
            print("Number outside the list.")
            continue

        return group_items[choice_num - 1]


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
# CARREGAR UM ATIVO
# =========================

def load_asset(asset_key, start_date=None, end_date=None):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Asset not found in ASSETS: {asset_key}")

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

    df = pd.read_sql(
        query,
        engine
    )

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
    df = df.sort_values("snapped_at")

    if start_date is not None:
        df = df[df["snapped_at"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["snapped_at"] <= pd.to_datetime(end_date)]

    if LIMIT_LAST_ROWS is not None:
        df = df.tail(LIMIT_LAST_ROWS)

    if df.empty:
        raise ValueError(
            f"No data after applied filters: {asset_key}"
        )

    df = df[["snapped_at", "price"]].copy()
    df = df.rename(columns={"price": asset_key})

    print(
        f"{asset_key:25s} | "
        f"{display_name:40s} | "
        f"{len(df):7d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# MERGE ASSETS
# =========================

def load_todos_assets(asset_keys, start_date=None, end_date=None):
    merged_df = None

    print("\nLoading assets:")
    print("-" * 120)

    loaded_assets = []

    for asset_key in asset_keys:
        try:
            df_asset = load_asset(
                asset_key=asset_key,
                start_date=start_date,
                end_date=end_date
            )

            loaded_assets.append(asset_key)

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
        raise ValueError("No asset was loaded.")

    merged_df = merged_df.sort_values("snapped_at").reset_index(drop=True)

    return merged_df, loaded_assets


# =========================
# NORMALIZE BASE 100
# =========================

def normalizar_base_100(df):
    df = df.copy()

    asset_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    normalized_df = pd.DataFrame()
    normalized_df["snapped_at"] = df["snapped_at"]

    for col in asset_cols:
        series = df[col].copy()

        # Alinhar datas de markets diferentes.
        series = series.ffill()

        first_valid = series.dropna()

        if first_valid.empty:
            print(f"Warning: {col} has no valid values.")
            continue

        base_value = first_valid.iloc[0]

        if base_value == 0:
            print(f"Warning: {col} has a zero base value.")
            continue

        normalized_df[col] = (series / base_value) * 100

    return normalized_df


# =========================
# STATISTICAL SUMMARY
# =========================

def mostrar_summary(normalized_df):
    asset_cols = [
        col for col in normalized_df.columns
        if col != "snapped_at"
    ]

    summary = []

    for col in asset_cols:
        series = normalized_df[col].dropna()

        if series.empty:
            continue

        final_value = series.iloc[-1]
        total_return_pct = final_value - 100
        max_value = series.max()
        min_value = series.min()

        summary.append({
            "asset": col,
            "display_name": ASSETS.get(col, {}).get("display_name", col),
            "market_type": ASSETS.get(col, {}).get("market_type", "unknown"),
            "start_value": round(series.iloc[0], 2),
            "final_value": round(final_value, 2),
            "total_return_pct": round(total_return_pct, 2),
            "max_value": round(max_value, 2),
            "min_value": round(min_value, 2)
        })

    summary_df = pd.DataFrame(summary)

    if not summary_df.empty:
        summary_df = summary_df.sort_values(
            "total_return_pct",
            ascending=False
        )

    print("\n" + "=" * 120)
    print("SUMMARY PERFORMANCE NORMALIZADA")
    print("=" * 120)
    print(summary_df)
    print("=" * 120)

    return summary_df


# =========================
# CHART
# =========================

def gerar_grafico(normalized_df, group_key, group_data, period_label):
    fig = go.Figure()

    asset_cols = [
        col for col in normalized_df.columns
        if col != "snapped_at"
    ]

    for col in asset_cols:
        asset = ASSETS.get(col, {})
        display_name = asset.get("display_name", col)
        market_type = asset.get("market_type", "unknown")

        fig.add_trace(
            go.Scatter(
                x=normalized_df["snapped_at"],
                y=normalized_df[col],
                mode="lines",
                name=display_name,
                hovertemplate=(
                    f"<b>{display_name}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Base 100: %{y:.2f}<br>"
                    f"Type: {market_type}"
                    "<extra></extra>"
                )
            )
        )

    fig.add_hline(
        y=100,
        line_dash="dash",
        opacity=0.7,
        annotation_text="Base 100",
        annotation_position="bottom right"
    )

    yaxis_config = dict(
        title="Normalized Performance"
    )

    if USE_LOG_SCALE:
        yaxis_config["type"] = "log"

    fig.update_layout(
        title=dict(
            text=(
                f"{group_data['name']} - Normalized Performance Base 100"
                f" | {period_label}"
            ),
            x=0.5,
            xanchor="center",
            font=dict(
                size=19,
                color="white"
            )
        ),
        template="plotly_dark",
        height=850,
        width=1550,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis=yaxis_config,
        margin=dict(
            l=80,
            r=280,
            t=100,
            b=70
        ),
        legend=dict(
            title="Assets",
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
                dict(
                    count=1,
                    label="1Y",
                    step="year",
                    stepmode="backward"
                ),
                dict(
                    count=3,
                    label="3Y",
                    step="year",
                    stepmode="backward"
                ),
                dict(
                    count=5,
                    label="5Y",
                    step="year",
                    stepmode="backward"
                ),
                dict(
                    count=10,
                    label="10Y",
                    step="year",
                    stepmode="backward"
                ),
                dict(
                    step="all",
                    label="ALL"
                )
            ])
        ),
        gridcolor="rgba(255,255,255,0.12)",
        tickfont=dict(
            color="white"
        ),
        title_font=dict(
            color="white"
        )
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.12)",
        tickfont=dict(
            color="white"
        ),
        title_font=dict(
            color="white"
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
# RUN GROUP
# =========================

def executar_grupo(group_key, group_data):
    start_date, end_date, period_label = chooser_periodo()

    print("\n" + "=" * 120)
    print(f"GROUP: {group_data['name']}")
    print(f"Description: {group_data['description']}")
    print(f"Assets: {group_data['assets']}")
    print(f"Period: {period_label}")
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print(f"Logarithmic scale: {USE_LOG_SCALE}")
    print("=" * 120)

    merged_df, loaded_assets = load_todos_assets(
        asset_keys=group_data["assets"],
        start_date=start_date,
        end_date=end_date
    )

    print("\nData combinados:")
    print(f"Loaded assets: {loaded_assets}")
    print(f"Rows totais: {len(merged_df)}")
    print(f"Minimum date: {merged_df['snapped_at'].min().date()}")
    print(f"Maximum date: {merged_df['snapped_at'].max().date()}")

    normalized_df = normalizar_base_100(merged_df)

    mostrar_summary(normalized_df)

    print("\nGenerating chart...")

    gerar_grafico(
        normalized_df=normalized_df,
        group_key=group_key,
        group_data=group_data,
        period_label=period_label
    )

    print("\nChart completed.")


# =========================
# MAIN
# =========================

def main():
    while True:
        group_items = mostrar_menu_grupos()

        selected_group = chooser_grupo(group_items)

        if selected_group is None:
            print("\nExiting the group selector.")
            break

        group_key, group_data = selected_group

        try:
            executar_grupo(group_key, group_data)

        except Exception as e:
            print("\nERROR while running group:")
            print(e)

        input("\nPressiona ENTER para voltar ao menu...")


if __name__ == "__main__":
    main()

