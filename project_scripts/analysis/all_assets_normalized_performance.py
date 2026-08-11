from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go

from config import get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# SETTINGS
# =========================

SELECTED_ASSETS = [
    "BTC",
    "SP500",
    "NASDAQ100",
    "GOLD",
    "DXY",
    "BRENT_OIL"
]

# Use None to load everything.
LIMIT_LAST_ROWS = None

# Recommended start date to avoid BTC dominating the comparison.
START_DATE = "2020-01-01"

# Use None to read until the end of the dataset.
END_DATE = None

# Logarithmic scale greatly improves comparisons between assets with very different values.
USE_LOG_SCALE = False


# =========================
# DATABASE CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# CARREGAR UM ATIVO
# =========================

def load_asset(asset_key):
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

    if START_DATE is not None:
        df = df[df["snapped_at"] >= pd.to_datetime(START_DATE)]

    if END_DATE is not None:
        df = df[df["snapped_at"] <= pd.to_datetime(END_DATE)]

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
        f"{display_name:35s} | "
        f"{len(df):7d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# MERGE ASSETS
# =========================

def load_todos_assets(asset_keys):
    merged_df = None

    print("\nLoading assets:")
    print("-" * 110)

    for asset_key in asset_keys:
        try:
            df_asset = load_asset(asset_key)

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

    return merged_df


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

        # Forward fill para alinhar datas diferentes entre markets.
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
# GENERATE CHART
# =========================

def gerar_grafico(normalized_df):
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
        opacity=0.6,
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
                "Normalized Performance Comparison - Base 100"
                f" | From {START_DATE if START_DATE else 'Start'}"
            ),
            x=0.5,
            xanchor="center",
            font=dict(
                size=20
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

    summary_df = summary_df.sort_values(
        "total_return_pct",
        ascending=False
    )

    print("\n" + "=" * 110)
    print("SUMMARY PERFORMANCE NORMALIZADA")
    print("=" * 110)
    print(summary_df)
    print("=" * 110)

    return summary_df


# =========================
# MAIN
# =========================

def main():
    print("\nStarting global comparison analysis...")
    print(f"Assets selecionados: {SELECTED_ASSETS}")
    print(f"Start date: {START_DATE}")
    print(f"End date: {END_DATE}")
    print(f"Logarithmic scale: {USE_LOG_SCALE}")

    merged_df = load_todos_assets(SELECTED_ASSETS)

    print("\nData combinados:")
    print(f"Rows totais: {len(merged_df)}")
    print(f"Minimum date: {merged_df['snapped_at'].min().date()}")
    print(f"Maximum date: {merged_df['snapped_at'].max().date()}")

    normalized_df = normalizar_base_100(merged_df)

    mostrar_summary(normalized_df)

    print("\nGenerating comparison chart...")
    gerar_grafico(normalized_df)

    print("\nAnalysis completed.")


if __name__ == "__main__":
    main()

