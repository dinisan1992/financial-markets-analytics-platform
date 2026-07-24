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
# SETTINGS
# =========================

PAIR_CONFIGS = [
    {
        "asset_a": "BTC",
        "asset_b": "NASDAQ100",
        "label": "BTC vs NASDAQ 100"
    },
    {
        "asset_a": "BTC",
        "asset_b": "GOLD",
        "label": "BTC vs Gold"
    },
    {
        "asset_a": "BTC",
        "asset_b": "DXY",
        "label": "BTC vs DXY"
    },
    {
        "asset_a": "SP500",
        "asset_b": "VIX",
        "label": "S&P 500 vs VIX"
    },
    {
        "asset_a": "NASDAQ100",
        "asset_b": "US10Y",
        "label": "NASDAQ 100 vs US 10Y"
    },
    {
        "asset_a": "GOLD",
        "asset_b": "DXY",
        "label": "Gold vs DXY"
    },
    {
        "asset_a": "BRENT_OIL",
        "asset_b": "DXY",
        "label": "Brent Oil vs DXY"
    },
    {
        "asset_a": "BRENT_OIL",
        "asset_b": "US10Y",
        "label": "Brent Oil vs US 10Y"
    }
]

START_DATE = "2020-01-01"
END_DATE = None

ROLLING_WINDOWS = [30, 90, 180]

MIN_PERIODS_RATIO = 0.7

EXPORT_REPORT = True

pio.renderers.default = "browser"


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

def load_precos(asset_key, start_date=None, end_date=None):
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
            f"No data after filters: {asset_key}"
        )

    df = df[["snapped_at", "price"]].copy()
    df = df.rename(columns={"price": asset_key})

    print(
        f"{asset_key:15s} | "
        f"{display_name:35s} | "
        f"{len(df):7d} prices | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# CALCULAR RETORNOS DE UM PAR
# =========================

def preparar_returns_par(asset_a, asset_b, start_date=None, end_date=None):
    print("\n" + "=" * 100)
    print(f"A preparar par: {asset_a} vs {asset_b}")
    print("=" * 100)

    df_a = load_precos(
        asset_key=asset_a,
        start_date=start_date,
        end_date=end_date
    )

    df_b = load_precos(
        asset_key=asset_b,
        start_date=start_date,
        end_date=end_date
    )

    merged = pd.merge(
        df_a,
        df_b,
        on="snapped_at",
        how="inner"
    )

    merged = merged.sort_values("snapped_at").reset_index(drop=True)

    if merged.empty:
        raise ValueError(
            f"Sem datas comuns para {asset_a} vs {asset_b}"
        )

    merged[f"{asset_a}_return"] = merged[asset_a].pct_change()
    merged[f"{asset_b}_return"] = merged[asset_b].pct_change()

    returns_df = merged[
        [
            "snapped_at",
            f"{asset_a}_return",
            f"{asset_b}_return"
        ]
    ].copy()

    returns_df = returns_df.dropna().reset_index(drop=True)

    print(f"Datas comuns: {len(merged)}")
    print(f"Returns valid: {len(returns_df)}")
    print(f"Common minimum date: {returns_df['snapped_at'].min().date()}")
    print(f"Common maximum date: {returns_df['snapped_at'].max().date()}")

    return returns_df


# =========================
# CALCULAR ROLLING CORRELATION
# =========================

def calcular_rolling_correlation(returns_df, asset_a, asset_b):
    df = returns_df.copy()

    col_a = f"{asset_a}_return"
    col_b = f"{asset_b}_return"

    for window in ROLLING_WINDOWS:
        min_periods = max(
            2,
            int(window * MIN_PERIODS_RATIO)
        )

        corr_col = f"rolling_corr_{window}d"

        df[corr_col] = (
            df[col_a]
            .rolling(
                window=window,
                min_periods=min_periods
            )
            .corr(df[col_b])
        )

    return df


# =========================
# SUMMARY
# =========================

def resumir_rolling_corr(df, pair_label):
    corr_cols = [
        col for col in df.columns
        if col.startswith("rolling_corr_")
    ]

    rows = []

    for col in corr_cols:
        series = df[col].dropna()

        if series.empty:
            continue

        rows.append({
            "pair": pair_label,
            "window": col.replace("rolling_corr_", "").replace("d", ""),
            "observations": len(series),
            "mean_corr": round(series.mean(), 4),
            "median_corr": round(series.median(), 4),
            "min_corr": round(series.min(), 4),
            "max_corr": round(series.max(), 4),
            "latest_corr": round(series.iloc[-1], 4),
            "positive_pct": round((series > 0).mean() * 100, 2),
            "negative_pct": round((series < 0).mean() * 100, 2)
        })

    return pd.DataFrame(rows)


# =========================
# CHART DE UM PAR
# =========================

def gerar_grafico_par(df, asset_a, asset_b, pair_label):
    fig = go.Figure()

    corr_cols = [
        col for col in df.columns
        if col.startswith("rolling_corr_")
    ]

    for col in corr_cols:
        window_label = col.replace("rolling_corr_", "").replace("d", "")

        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df[col],
                mode="lines",
                name=f"{window_label}D Rolling Corr",
                hovertemplate=(
                    f"<b>{pair_label}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    f"Window: {window_label}D<br>"
                    "Correlation: %{y:.3f}"
                    "<extra></extra>"
                )
            )
        )

    fig.add_hline(
        y=0,
        line_dash="dash",
        opacity=0.7,
        annotation_text="Zero correlation",
        annotation_position="bottom right"
    )

    fig.add_hline(
        y=0.5,
        line_dash="dot",
        opacity=0.4
    )

    fig.add_hline(
        y=-0.5,
        line_dash="dot",
        opacity=0.4
    )

    fig.update_layout(
        title=dict(
            text=(
                f"Rolling Correlation - {pair_label}"
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
        height=750,
        width=1450,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Rolling Correlation",
        yaxis=dict(
            range=[-1, 1]
        ),
        margin=dict(
            l=80,
            r=180,
            t=100,
            b=70
        ),
        legend=dict(
            title="Windows",
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
# EXECUTAR TODOS OS PARES
# =========================

def executar_analise():
    print("\nA iniciar analysis de rolling correlation...")
    print(f"Start date: {START_DATE}")
    print(f"End date: {END_DATE}")
    print(f"Janelas: {ROLLING_WINDOWS}")

    summaries = []

    for pair in PAIR_CONFIGS:
        asset_a = pair["asset_a"]
        asset_b = pair["asset_b"]
        pair_label = pair["label"]

        try:
            returns_df = preparar_returns_par(
                asset_a=asset_a,
                asset_b=asset_b,
                start_date=START_DATE,
                end_date=END_DATE
            )

            rolling_df = calcular_rolling_correlation(
                returns_df=returns_df,
                asset_a=asset_a,
                asset_b=asset_b
            )

            summary_df = resumir_rolling_corr(
                df=rolling_df,
                pair_label=pair_label
            )

            summaries.append(summary_df)

            print("\nSummary rolling correlation:")
            print(summary_df)

            gerar_grafico_par(
                df=rolling_df,
                asset_a=asset_a,
                asset_b=asset_b,
                pair_label=pair_label
            )

        except Exception as e:
            print(f"\nERROR no par {pair_label}: {e}")

    if summaries:
        final_summary = pd.concat(
            summaries,
            ignore_index=True
        )

        print("\n" + "=" * 120)
        print("SUMMARY FINAL - ROLLING CORRELATION")
        print("=" * 120)
        print(final_summary)
        print("=" * 120)

        if EXPORT_REPORT:
            final_summary.to_csv(
                "rolling_correlation_summary.csv",
                index=False,
                sep=";",
                encoding="utf-8-sig"
            )

            print("\nReport saved to: rolling_correlation_summary.csv")

    print("\nAnalysis completed.")


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    executar_analise()
