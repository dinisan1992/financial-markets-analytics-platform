from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from asset_config import ASSETS
from euro_series_config import EURO_SERIES, EURO_MARKET_PAIRS
from euro_data_loader import (
    get_engine,
    alinhar_euro_com_market,
    normalizar_base_100,
    calcular_variacoes,
    summary_dataset
)


# =========================
# SETTINGS
# =========================

START_DATE = "2000-01-01"
END_DATE = None

EXPORT_REPORT = True

# "single" = run only the pair defined in SELECTED_PAIR_KEY
# "all"    = corre todos os pares
RUN_MODE = "single"

SELECTED_PAIR_KEY = "euro_mfi_corporate_loans_stoxx600"

GENERATE_DUAL_AXIS_CHART = True
GENERATE_BASE100_CHART = False
GENERATE_ROLLING_CORR_CHART = True

ROLLING_CORR_WINDOWS = [90, 180, 252]

pio.renderers.default = "browser"


# =========================
# VALIDATION
# =========================

def validar_par(config):
    euro_series = config["euro_series"]
    market_asset = config["market_asset"]

    if euro_series not in EURO_SERIES:
        raise ValueError(
            f"EURO series not configured: {euro_series}"
        )

    if market_asset not in ASSETS:
        raise ValueError(
            f"Market asset not configured: {market_asset}"
        )

    euro_cfg = EURO_SERIES[euro_series]

    if euro_cfg.get("enabled", True) is not True:
        raise ValueError(
            f"EURO series is disabled: {euro_series}"
        )


# =========================
# ROLLING CORRELATION
# =========================

def calcular_rolling_correlations(df, euro_series, market_asset):
    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    df[f"{euro_series}_abs_change_90obs"] = (
        df[euro_series] - df[euro_series].shift(90)
    )

    df[f"{euro_series}_pct_change_90obs"] = (
        df[euro_series].pct_change(90)
    )

    df[f"{market_asset}_return_90obs"] = (
        df[market_asset].pct_change(90)
    )

    euro_abs_col = f"{euro_series}_abs_change_90obs"
    euro_pct_col = f"{euro_series}_pct_change_90obs"
    market_return_col = f"{market_asset}_return_90obs"

    for window in ROLLING_CORR_WINDOWS:
        abs_corr_col = f"rolling_corr_abs_{window}obs"
        pct_corr_col = f"rolling_corr_pct_{window}obs"

        df[abs_corr_col] = (
            df[euro_abs_col]
            .rolling(
                window=window,
                min_periods=max(20, int(window * 0.6))
            )
            .corr(df[market_return_col])
        )

        df[pct_corr_col] = (
            df[euro_pct_col]
            .rolling(
                window=window,
                min_periods=max(20, int(window * 0.6))
            )
            .corr(df[market_return_col])
        )

    return df


# =========================
# SUMMARY
# =========================

def gerar_summary(df, euro_series, market_asset, label):
    euro_cfg = EURO_SERIES[euro_series]
    market_cfg = ASSETS[market_asset]

    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    euro_data = df[euro_series].dropna()
    market_data = df[market_asset].dropna()

    if euro_data.empty or market_data.empty:
        raise ValueError("EURO series or market series has no valid data.")

    euro_start = euro_data.iloc[0]
    euro_end = euro_data.iloc[-1]

    market_start = market_data.iloc[0]
    market_end = market_data.iloc[-1]

    euro_absolute_change = euro_end - euro_start

    euro_total_change_pct = (
        ((euro_end / euro_start) - 1) * 100
        if euro_start != 0
        else None
    )

    market_total_return_pct = (
        ((market_end / market_start) - 1) * 100
        if market_start != 0
        else None
    )

    df_changes = calcular_variacoes(
        df[["snapped_at", euro_series, market_asset]].copy(),
        windows=[90, 180, 252]
    )

    correlations = {}

    for window in [90, 180, 252]:
        euro_pct_col = f"{euro_series}_pct_change_{window}obs"
        euro_abs_col = f"{euro_series}_abs_change_{window}obs"
        market_col = f"{market_asset}_pct_change_{window}obs"

        if euro_pct_col in df_changes.columns and market_col in df_changes.columns:
            corr_pct_df = df_changes[[euro_pct_col, market_col]].dropna()

            if len(corr_pct_df) >= 30:
                correlations[f"corr_{window}obs_euro_pct_vs_market_return"] = round(
                    corr_pct_df[euro_pct_col].corr(corr_pct_df[market_col]),
                    4
                )
            else:
                correlations[f"corr_{window}obs_euro_pct_vs_market_return"] = None
        else:
            correlations[f"corr_{window}obs_euro_pct_vs_market_return"] = None

        if euro_abs_col in df_changes.columns and market_col in df_changes.columns:
            corr_abs_df = df_changes[[euro_abs_col, market_col]].dropna()

            if len(corr_abs_df) >= 30:
                correlations[f"corr_{window}obs_euro_abs_vs_market_return"] = round(
                    corr_abs_df[euro_abs_col].corr(corr_abs_df[market_col]),
                    4
                )
            else:
                correlations[f"corr_{window}obs_euro_abs_vs_market_return"] = None
        else:
            correlations[f"corr_{window}obs_euro_abs_vs_market_return"] = None

    summary = {
        "label": label,
        "euro_series": euro_series,
        "euro_display_name": euro_cfg["display_name"],
        "euro_table": euro_cfg["table_name"],
        "euro_key_code": euro_cfg["key_code"],
        "euro_category": euro_cfg["category"],
        "euro_region": euro_cfg["region"],
        "euro_frequency": euro_cfg["frequency"],
        "market_asset": market_asset,
        "market_display_name": market_cfg["display_name"],
        "start_date": df["snapped_at"].min().date(),
        "end_date": df["snapped_at"].max().date(),
        "observations": len(df),
        "euro_start": round(euro_start, 4),
        "euro_end": round(euro_end, 4),
        "euro_absolute_change": round(euro_absolute_change, 4),
        "euro_total_change_pct": round(euro_total_change_pct, 2) if euro_total_change_pct is not None else None,
        "market_start": round(market_start, 4),
        "market_end": round(market_end, 4),
        "market_total_return_pct": round(market_total_return_pct, 2) if market_total_return_pct is not None else None,
        **correlations
    }

    summary_df = pd.DataFrame([summary])

    print("\n" + "=" * 130)
    print(f"SUMMARY - {label}")
    print("=" * 130)
    print(summary_df)
    print("=" * 130)

    return summary_df


# =========================
# DUAL-AXIS CHART
# =========================

def gerar_grafico_dual_axis(df, euro_series, market_asset, label, description):
    euro_cfg = EURO_SERIES[euro_series]
    market_cfg = ASSETS[market_asset]

    market_base = df[market_asset].dropna().iloc[0]

    if market_base == 0:
        print("Warning: market base value is zero. Not foi possible gerar dual axis.")
        return None

    plot_df = df.copy()
    plot_df[f"{market_asset}_base100"] = (
        plot_df[market_asset] / market_base
    ) * 100

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df[f"{market_asset}_base100"],
            mode="lines",
            name=f"{market_cfg['display_name']} Base 100",
            yaxis="y1",
            hovertemplate=(
                f"<b>{market_cfg['display_name']}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Base 100: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df[euro_series],
            mode="lines",
            name=f"{euro_cfg['display_name']} ({euro_cfg['unit']})",
            yaxis="y2",
            line=dict(
                dash="dot",
                width=2
            ),
            hovertemplate=(
                f"<b>{euro_cfg['display_name']}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Value: %{y:.4f}<br>"
                f"Unit: {euro_cfg['unit']}"
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
            text=f"Euro Macro vs Market - {label}",
            x=0.5,
            xanchor="center",
            font=dict(size=20, color="white")
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
            title=f"{market_cfg['display_name']} Base 100",
            side="left",
            gridcolor="rgba(255,255,255,0.12)"
        ),
        yaxis2=dict(
            title=f"{euro_cfg['display_name']} ({euro_cfg['unit']})",
            overlaying="y",
            side="right",
            showgrid=False
        ),
        margin=dict(l=80, r=280, t=115, b=70),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=11, color="white"),
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
                y=1.10,
                showarrow=False,
                font=dict(size=11, color="white"),
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
            font=dict(color="#FFFFFF", size=12),
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
# BASE 100 CHART
# =========================

def gerar_grafico_base100(df, euro_series, market_asset, label):
    euro_cfg = EURO_SERIES[euro_series]
    market_cfg = ASSETS[market_asset]

    norm_df = normalizar_base_100(
        df[["snapped_at", euro_series, market_asset]].copy()
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=norm_df["snapped_at"],
            y=norm_df[euro_series],
            mode="lines",
            name=f"{euro_cfg['display_name']} Base 100",
            hovertemplate=(
                f"<b>{euro_cfg['display_name']}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Base 100: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )

    fig.add_trace(
        go.Scatter(
            x=norm_df["snapped_at"],
            y=norm_df[market_asset],
            mode="lines",
            name=f"{market_cfg['display_name']} Base 100",
            hovertemplate=(
                f"<b>{market_cfg['display_name']}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Base 100: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )

    fig.add_hline(
        y=100,
        line_dash="dash",
        opacity=0.5,
        annotation_text="Base 100",
        annotation_position="bottom right"
    )

    fig.update_layout(
        title=dict(
            text=f"Base 100 Comparison - {label}",
            x=0.5,
            xanchor="center",
            font=dict(size=20, color="white")
        ),
        template="plotly_dark",
        height=780,
        width=1500,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Base 100",
        margin=dict(l=80, r=240, t=100, b=70),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=11, color="white"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.25)",
            borderwidth=1
        ),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117"
    )

    fig.update_xaxes(
        rangeslider_visible=False,
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
# ROLLING CORRELATION CHART
# =========================

def gerar_grafico_rolling_corr(df, euro_series, market_asset, label):
    fig = go.Figure()

    corr_cols = [
        col for col in df.columns
        if col.startswith("rolling_corr_abs_")
    ]

    if not corr_cols:
        print("Warning: sem columns de rolling correlation para mostrar.")
        return None

    for col in corr_cols:
        window_label = (
            col.replace("rolling_corr_abs_", "")
            .replace("obs", "")
        )

        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df[col],
                mode="lines",
                name=f"{window_label} obs Corr Abs Change",
                hovertemplate=(
                    f"<b>{label}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    f"Window: {window_label} observations<br>"
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
        opacity=0.35,
        annotation_text="+0.5",
        annotation_position="top right"
    )

    fig.add_hline(
        y=-0.5,
        line_dash="dot",
        opacity=0.35,
        annotation_text="-0.5",
        annotation_position="bottom right"
    )

    fig.update_layout(
        title=dict(
            text=f"Rolling Correlation - Euro Macro Change vs Market Return | {label}",
            x=0.5,
            xanchor="center",
            font=dict(size=19, color="white")
        ),
        template="plotly_dark",
        height=750,
        width=1500,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Rolling Correlation",
        yaxis=dict(range=[-1, 1]),
        margin=dict(l=80, r=220, t=110, b=70),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=11, color="white"),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.25)",
            borderwidth=1
        ),
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117"
    )

    fig.update_xaxes(
        rangeslider_visible=False,
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

def export_resultados(df, summary_df, pair_key, euro_series, market_asset):
    if not EXPORT_REPORT:
        return

    safe_name = f"{pair_key}_{euro_series.lower()}_{market_asset.lower()}"

    data_output = f"euro_market_analysis_{safe_name}.csv"
    summary_output = f"euro_market_analysis_summary_{safe_name}.csv"

    df.to_csv(
        data_output,
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
    print(data_output)
    print(summary_output)


# =========================
# EXECUTAR UM PAR
# =========================

def executar_par(pair_key, config, engine):
    validar_par(config)

    euro_series = config["euro_series"]
    market_asset = config["market_asset"]
    label = config["label"]
    description = config["description"]

    print("\n" + "=" * 130)
    print(f"EURO MARKET ANALYSIS - {label}")
    print("=" * 130)
    print(f"Par: {pair_key}")
    print(f"EURO: {euro_series} | {EURO_SERIES[euro_series]['display_name']}")
    print(f"Market: {market_asset} | {ASSETS[market_asset]['display_name']}")
    print(f"Period: {START_DATE} -> {END_DATE if END_DATE else 'end'}")
    print("=" * 130)

    df = alinhar_euro_com_market(
        euro_series_key=euro_series,
        market_asset=market_asset,
        engine=engine,
        start_date=START_DATE,
        end_date=END_DATE,
        how="outer",
        forward_fill=True
    )

    summary_dataset(df)

    df = calcular_rolling_correlations(
        df=df,
        euro_series=euro_series,
        market_asset=market_asset
    )

    summary_df = gerar_summary(
        df=df,
        euro_series=euro_series,
        market_asset=market_asset,
        label=label
    )

    if GENERATE_DUAL_AXIS_CHART:
        gerar_grafico_dual_axis(
            df=df,
            euro_series=euro_series,
            market_asset=market_asset,
            label=label,
            description=description
        )

    if GENERATE_BASE100_CHART:
        gerar_grafico_base100(
            df=df,
            euro_series=euro_series,
            market_asset=market_asset,
            label=label
        )

    if GENERATE_ROLLING_CORR_CHART:
        gerar_grafico_rolling_corr(
            df=df,
            euro_series=euro_series,
            market_asset=market_asset,
            label=label
        )

    export_resultados(
        df=df,
        summary_df=summary_df,
        pair_key=pair_key,
        euro_series=euro_series,
        market_asset=market_asset
    )

    return summary_df


# =========================
# MAIN
# =========================

def main():
    print("\nA iniciar Euro Market Analysis...")
    print(f"Run mode: {RUN_MODE}")
    print(f"Start date: {START_DATE}")
    print(f"End date: {END_DATE}")
    print(f"Pares configurados: {len(EURO_MARKET_PAIRS)}")

    engine = get_engine()

    final_summaries = []

    if RUN_MODE == "single":
        if SELECTED_PAIR_KEY not in EURO_MARKET_PAIRS:
            raise ValueError(
                f"SELECTED_PAIR_KEY does not exist: {SELECTED_PAIR_KEY}"
            )

        config = EURO_MARKET_PAIRS[SELECTED_PAIR_KEY]

        summary_df = executar_par(
            pair_key=SELECTED_PAIR_KEY,
            config=config,
            engine=engine
        )

        final_summaries.append(summary_df)

    elif RUN_MODE == "all":
        for idx, (pair_key, config) in enumerate(EURO_MARKET_PAIRS.items(), start=1):
            print("\n" + "#" * 130)
            print(f"[{idx}/{len(EURO_MARKET_PAIRS)}] {pair_key}")
            print("#" * 130)

            try:
                summary_df = executar_par(
                    pair_key=pair_key,
                    config=config,
                    engine=engine
                )

                final_summaries.append(summary_df)

            except Exception as e:
                print(f"\nERROR no par {pair_key} | {config.get('label')}: {e}")

    else:
        raise ValueError(
            f"Invalid RUN_MODE: {RUN_MODE}. Use 'single' or 'all'."
        )

    if final_summaries:
        final_summary_df = pd.concat(
            final_summaries,
            ignore_index=True
        )

        final_summary_df.to_csv(
            "euro_market_analysis_summary_all.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print("\nSummary final exportado:")
        print("euro_market_analysis_summary_all.csv")

    print("\nEuro Market Analysis completed.")


if __name__ == "__main__":
    main()

