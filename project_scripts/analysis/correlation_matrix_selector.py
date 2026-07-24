from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import plotly.io as pio

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# GENERAL SETTINGS
# =========================

MIN_OBSERVATIONS = 30

CORRELATION_METHOD = "pearson"
# Options:
# "pearson"  -> correlation linear normal
# "spearman" -> correlation por ranking

# Force browser opening
pio.renderers.default = "browser"


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
    },

    "inflation_energy_risk": {
        "name": "Inflation / Energy / Risk",
        "description": "Oil, gas, metals, yields, dollar and Nasdaq.",
        "assets": [
            "BRENT_OIL",
            "WTI_OIL",
            "NATURAL_GAS",
            "COPPER",
            "GOLD",
            "DXY",
            "US10Y",
            "NASDAQ100"
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
    print("CORRELATION MATRIX SELECTOR - MARKET GROUPS")
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
# LOAD PRICES FOR ONE ASSET
# =========================

def load_precos_asset(asset_key, start_date=None, end_date=None):
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
    df = df.sort_values("snapped_at").reset_index(drop=True)

    if start_date is not None:
        df = df[df["snapped_at"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["snapped_at"] <= pd.to_datetime(end_date)]

    if df.empty:
        raise ValueError(
            f"No data after applied filters: {asset_key}"
        )

    print(
        f"{asset_key:25s} | "
        f"{display_name:40s} | "
        f"{len(df):7d} prices | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# CALCULATE INDIVIDUAL RETURN
# =========================

def calcular_return_asset(asset_key, start_date=None, end_date=None):
    df = load_precos_asset(
        asset_key=asset_key,
        start_date=start_date,
        end_date=end_date
    )

    df = df[["snapped_at", "price"]].copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    df[asset_key] = df["price"].pct_change()

    df = df[["snapped_at", asset_key]].copy()

    df = df.replace([float("inf"), float("-inf")], pd.NA)
    df = df.dropna(subset=[asset_key])

    print(
        f"{asset_key:25s} | "
        f"{len(df):7d} returns valid"
    )

    return df


# =========================
# MERGE RETURNS
# =========================

def load_returns(asset_keys, start_date=None, end_date=None):
    merged_returns = None
    loaded_assets = []

    print("\nLoading prices and calculating individual returns:")
    print("-" * 120)

    for asset_key in asset_keys:
        try:
            returns_asset = calcular_return_asset(
                asset_key=asset_key,
                start_date=start_date,
                end_date=end_date
            )

            loaded_assets.append(asset_key)

            if merged_returns is None:
                merged_returns = returns_asset

            else:
                merged_returns = pd.merge(
                    merged_returns,
                    returns_asset,
                    on="snapped_at",
                    how="inner"
                )

        except Exception as e:
            print(f"ERROR in {asset_key}: {e}")

    if merged_returns is None or merged_returns.empty:
        raise ValueError("No return was loaded.")

    merged_returns = merged_returns.sort_values("snapped_at").reset_index(drop=True)

    return merged_returns, loaded_assets


# =========================
# CALCULATE CORRELATION
# =========================

def calcular_correlacao(returns_df):
    asset_cols = [
        col for col in returns_df.columns
        if col != "snapped_at"
    ]

    clean_returns = returns_df[["snapped_at"] + asset_cols].copy()

    # Remove rows where all returns are null
    clean_returns = clean_returns.dropna(
        how="all",
        subset=asset_cols
    )

    valid_counts = clean_returns[asset_cols].count()

    valid_assets = [
        col for col in asset_cols
        if valid_counts[col] >= MIN_OBSERVATIONS
    ]

    if len(valid_assets) < 2:
        raise ValueError(
            "There are not enough assets with valid observations "
            f"minimums ({MIN_OBSERVATIONS})."
        )

    clean_returns = clean_returns[["snapped_at"] + valid_assets].copy()

    corr_matrix = clean_returns[valid_assets].corr(
        method=CORRELATION_METHOD
    )

    return corr_matrix, clean_returns


# =========================
# STRONGEST / WEAKEST PAIRS
# =========================

def extrair_pares_correlacao(corr_matrix):
    pairs = []

    cols = list(corr_matrix.columns)

    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            asset_a = cols[i]
            asset_b = cols[j]
            corr_value = corr_matrix.loc[asset_a, asset_b]

            if pd.isna(corr_value):
                continue

            pairs.append({
                "asset_a": asset_a,
                "asset_b": asset_b,
                "asset_a_name": ASSETS.get(asset_a, {}).get("display_name", asset_a),
                "asset_b_name": ASSETS.get(asset_b, {}).get("display_name", asset_b),
                "correlation": round(float(corr_value), 4)
            })

    pairs_df = pd.DataFrame(pairs)

    if pairs_df.empty:
        return pairs_df, pairs_df

    strongest_positive = pairs_df.sort_values(
        "correlation",
        ascending=False
    ).head(10)

    strongest_negative = pairs_df.sort_values(
        "correlation",
        ascending=True
    ).head(10)

    return strongest_positive, strongest_negative


def mostrar_summary_correlacao(corr_matrix, returns_df):
    asset_cols = [
        col for col in returns_df.columns
        if col != "snapped_at"
    ]

    print("\n" + "=" * 120)
    print("CORRELATION MATRIX")
    print("=" * 120)
    print(corr_matrix.round(3))
    print("=" * 120)

    print("\nValid observations by asset:")
    print(returns_df[asset_cols].count().sort_values(ascending=False))

    strongest_positive, strongest_negative = extrair_pares_correlacao(corr_matrix)

    print("\n" + "=" * 120)
    print("TOP 10 POSITIVE CORRELATIONS")
    print("=" * 120)
    print(strongest_positive)
    print("=" * 120)

    print("\n" + "=" * 120)
    print("TOP 10 NEGATIVE CORRELATIONS")
    print("=" * 120)
    print(strongest_negative)
    print("=" * 120)


# =========================
# HEATMAP
# =========================

def gerar_heatmap(corr_matrix, group_data, period_label):
    labels = []

    for col in corr_matrix.columns:
        display_name = ASSETS.get(col, {}).get("display_name", col)
        labels.append(display_name)

    text_values = corr_matrix.round(2).astype(str)

    fig = go.Figure(
        data=go.Heatmap(
            z=corr_matrix.values,
            x=labels,
            y=labels,
            zmin=-1,
            zmax=1,
            colorscale=[
                [0.0, "#8B0000"],
                [0.25, "#D94E4E"],
                [0.5, "#1E1E1E"],
                [0.75, "#3FA7D6"],
                [1.0, "#00BFFF"]
            ],
            colorbar=dict(
                title=dict(
                    text="Correlation",
                    font=dict(color="white")
                ),
                tickfont=dict(color="white")
            ),
            text=text_values.values,
            texttemplate="%{text}",
            hovertemplate=(
                "<b>%{y}</b><br>"
                "vs<br>"
                "<b>%{x}</b><br>"
                "Correlation: %{z:.3f}"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        title=dict(
            text=(
                f"{group_data['name']} - Daily Return Correlation Matrix"
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
        height=850,
        width=1100,
        margin=dict(
            l=220,
            r=120,
            t=100,
            b=220
        ),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        xaxis=dict(
            tickangle=-45,
            tickfont=dict(
                color="white",
                size=11
            )
        ),
        yaxis=dict(
            tickfont=dict(
                color="white",
                size=11
            )
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
    print(f"Correlation method: {CORRELATION_METHOD}")
    print("Calculation method: returns by asset first, then merge on common dates")
    print("=" * 120)

    returns_df, loaded_assets = load_returns(
        asset_keys=group_data["assets"],
        start_date=start_date,
        end_date=end_date
    )

    print("\nCombined returns data:")
    print(f"Loaded assets: {loaded_assets}")
    print(f"Total common rows: {len(returns_df)}")
    print(f"Common minimum date: {returns_df['snapped_at'].min().date()}")
    print(f"Common maximum date: {returns_df['snapped_at'].max().date()}")

    corr_matrix, clean_returns = calcular_correlacao(returns_df)

    mostrar_summary_correlacao(
        corr_matrix=corr_matrix,
        returns_df=clean_returns
    )

    print("\nGenerating correlation heatmap...")

    gerar_heatmap(
        corr_matrix=corr_matrix,
        group_data=group_data,
        period_label=period_label
    )

    print("\nCorrelation matrix completed.")


# =========================
# MAIN
# =========================

def main():
    while True:
        group_items = mostrar_menu_grupos()

        selected_group = chooser_grupo(group_items)

        if selected_group is None:
            print("\nExiting the correlation selector.")
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

