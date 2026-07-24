from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from asset_config import ASSETS
from macro_config import MACRO_ASSETS
from macro_data_loader import (
    get_engine,
    alinhar_macro_com_market,
    normalizar_base_100,
    calcular_variacoes,
    summary_dataset
)


# =========================
# SETTINGS
# =========================

START_DATE = "2020-01-01"
END_DATE = None

EXPORT_REPORT = True

# "single" = run only the pair defined in SELECTED_PAIR_KEY
# "all"    = corre todos os pares
RUN_MODE = "single"

SELECTED_PAIR_KEY = "fed_m2_btc"

GENERATE_BASE100_CHART = True
GENERATE_ROLLING_CORR_CHART = True

ROLLING_CORR_WINDOWS = [90, 180, 252]

pio.renderers.default = "browser"


# =========================
# PARES DE LIQUIDEZ / MERCADO
# =========================

LIQUIDITY_MARKET_PAIRS = {
    "fed_m2_btc": {
        "macro_asset": "FED_M2",
        "market_asset": "BTC",
        "label": "US M2 Money Supply vs BTC",
        "description": "Analyses whether US monetary liquidity expansion/contraction follows Bitcoin cycles."
    },

    "fed_m2_nasdaq": {
        "macro_asset": "FED_M2",
        "market_asset": "NASDAQ100",
        "label": "US M2 Money Supply vs NASDAQ 100",
        "description": "Analyses the relationship between monetary liquidity and growth/technology assets."
    },

    "fed_total_assets_sp500": {
        "macro_asset": "FED_TOTAL_ASSETS",
        "market_asset": "SP500",
        "label": "Fed Total Assets vs S&P 500",
        "description": "Compares the Fed balance sheet with the US equity market."
    },

    "fed_total_assets_nasdaq": {
        "macro_asset": "FED_TOTAL_ASSETS",
        "market_asset": "NASDAQ100",
        "label": "Fed Total Assets vs NASDAQ 100",
        "description": "Compares the Fed balance sheet with technology/growth stocks."
    },

    "fed_reserve_bank_credit_sp500": {
        "macro_asset": "FED_RESERVE_BANK_CREDIT",
        "market_asset": "SP500",
        "label": "Reserve Bank Credit vs S&P 500",
        "description": "Compares Federal Reserve credit with US equities."
    },

    "fed_deposits_sp500": {
        "macro_asset": "FED_DEPOSITS",
        "market_asset": "SP500",
        "label": "Commercial Bank Deposits vs S&P 500",
        "description": "Compares bank deposits with the equity market."
    },

    "fed_bank_credit_sp500": {
        "macro_asset": "FED_BANK_CREDIT",
        "market_asset": "SP500",
        "label": "Bank Credit vs S&P 500",
        "description": "Compares total bank credit with US equities."
    },

    "fed_loans_leases_nasdaq": {
        "macro_asset": "FED_LOANS_LEASES",
        "market_asset": "NASDAQ100",
        "label": "Loans and Leases vs NASDAQ 100",
        "description": "Compares bank credit growth with risk/growth assets."
    },

    "fed_securities_bank_credit_sp500": {
        "macro_asset": "FED_SECURITIES_BANK_CREDIT",
        "market_asset": "SP500",
        "label": "Securities in Bank Credit vs S&P 500",
        "description": "Compares securities in bank credit with the S&P 500."
    }
}


# =========================
# VALIDATION DO PAR
# =========================

def validar_par(config):
    macro_asset = config["macro_asset"]
    market_asset = config["market_asset"]

    if macro_asset not in MACRO_ASSETS:
        raise ValueError(
            f"Macro indicator is not active in MACRO_ASSETS: {macro_asset}"
        )

    if market_asset not in ASSETS:
        raise ValueError(
            f"Market asset not found em ASSETS: {market_asset}"
        )

    macro_cfg = MACRO_ASSETS[macro_asset]

    if macro_cfg.get("enabled", True) is not True:
        raise ValueError(
            f"Macro indicator is disabled: {macro_asset}"
        )

    if macro_cfg.get("needs_filter", False) is True:
        raise ValueError(
            f"Macro indicator requires filters and should not be used yet: {macro_asset}"
        )


# =========================
# ROLLING CORRELATION
# =========================

def calcular_rolling_correlations(df, macro_asset, market_asset):
    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    df[f"{macro_asset}_pct_change_90obs"] = df[macro_asset].pct_change(90)
    df[f"{market_asset}_return_90obs"] = df[market_asset].pct_change(90)

    macro_change_col = f"{macro_asset}_pct_change_90obs"
    market_return_col = f"{market_asset}_return_90obs"

    for window in ROLLING_CORR_WINDOWS:
        corr_col = f"rolling_corr_{window}obs"

        df[corr_col] = (
            df[macro_change_col]
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

def gerar_summary_liquidez(df, macro_asset, market_asset, label):
    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    macro_series = df[macro_asset].dropna()
    market_series = df[market_asset].dropna()

    if macro_series.empty or market_series.empty:
        raise ValueError("Macro series or market series has no valid data.")

    macro_start = macro_series.iloc[0]
    macro_end = macro_series.iloc[-1]

    market_start = market_series.iloc[0]
    market_end = market_series.iloc[-1]

    macro_total_change_pct = (
        ((macro_end / macro_start) - 1) * 100
        if macro_start != 0
        else None
    )

    market_total_return_pct = (
        ((market_end / market_start) - 1) * 100
        if market_start != 0
        else None
    )

    df_changes = calcular_variacoes(
        df[["snapped_at", macro_asset, market_asset]].copy(),
        windows=[90, 180, 252]
    )

    correlations = {}

    for window in [90, 180, 252]:
        macro_col = f"{macro_asset}_pct_change_{window}d"
        market_col = f"{market_asset}_pct_change_{window}d"

        if macro_col not in df_changes.columns or market_col not in df_changes.columns:
            correlations[f"corr_{window}obs_changes"] = None
            continue

        corr_df = df_changes[[macro_col, market_col]].dropna()

        if len(corr_df) >= 30:
            correlations[f"corr_{window}obs_changes"] = round(
                corr_df[macro_col].corr(corr_df[market_col]),
                4
            )
        else:
            correlations[f"corr_{window}obs_changes"] = None

    summary = {
        "label": label,
        "macro_asset": macro_asset,
        "macro_display_name": macro_cfg["display_name"],
        "macro_table": macro_cfg["table_name"],
        "macro_value_col": macro_cfg["value_col"],
        "market_asset": market_asset,
        "market_display_name": market_cfg["display_name"],
        "start_date": df["snapped_at"].min().date(),
        "end_date": df["snapped_at"].max().date(),
        "observations": len(df),
        "macro_start": round(macro_start, 4),
        "macro_end": round(macro_end, 4),
        "macro_total_change_pct": round(macro_total_change_pct, 2) if macro_total_change_pct is not None else None,
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
# BASE 100 CHART
# =========================

def gerar_grafico_base100(df, macro_asset, market_asset, label, description):
    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    norm_df = normalizar_base_100(
        df[["snapped_at", macro_asset, market_asset]].copy()
    )

    if macro_asset not in norm_df.columns or market_asset not in norm_df.columns:
        print("Warning: not foi possible gerar chart base 100.")
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=norm_df["snapped_at"],
            y=norm_df[macro_asset],
            mode="lines",
            name=f"{macro_cfg['display_name']} Base 100",
            hovertemplate=(
                f"<b>{macro_cfg['display_name']}</b><br>"
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
            text=f"Liquidity vs Market - {label}",
            x=0.5,
            xanchor="center",
            font=dict(size=20, color="white")
        ),
        template="plotly_dark",
        height=800,
        width=1500,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Base 100",
        margin=dict(l=80, r=240, t=115, b=70),
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
# ROLLING CORRELATION CHART
# =========================

def gerar_grafico_rolling_corr(df, macro_asset, market_asset, label):
    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    fig = go.Figure()

    corr_cols = [
        col for col in df.columns
        if col.startswith("rolling_corr_")
    ]

    if not corr_cols:
        print("Warning: sem columns de rolling correlation para mostrar.")
        return None

    for col in corr_cols:
        window_label = (
            col.replace("rolling_corr_", "")
            .replace("obs", "")
        )

        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df[col],
                mode="lines",
                name=f"{window_label} obs Rolling Corr",
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
            text=(
                "Rolling Correlation - "
                f"{macro_cfg['display_name']} 90 obs Change vs "
                f"{market_cfg['display_name']} 90 obs Return"
            ),
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

def export_resultados(df, summary_df, pair_key, macro_asset, market_asset):
    if not EXPORT_REPORT:
        return

    safe_name = f"{pair_key}_{macro_asset.lower()}_{market_asset.lower()}"

    data_output = f"macro_liquidity_market_{safe_name}.csv"
    summary_output = f"macro_liquidity_market_summary_{safe_name}.csv"

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

    macro_asset = config["macro_asset"]
    market_asset = config["market_asset"]
    label = config["label"]
    description = config["description"]

    print("\n" + "=" * 130)
    print(f"LIQUIDITY MARKET ANALYSIS - {label}")
    print("=" * 130)
    print(f"Par: {pair_key}")
    print(f"Macro: {macro_asset} | {MACRO_ASSETS[macro_asset]['display_name']}")
    print(f"Market: {market_asset} | {ASSETS[market_asset]['display_name']}")
    print(f"Period: {START_DATE} -> {END_DATE if END_DATE else 'end'}")
    print("=" * 130)

    df = alinhar_macro_com_market(
        macro_key=macro_asset,
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
        macro_asset=macro_asset,
        market_asset=market_asset
    )

    summary_df = gerar_summary_liquidez(
        df=df,
        macro_asset=macro_asset,
        market_asset=market_asset,
        label=label
    )

    if GENERATE_BASE100_CHART:
        gerar_grafico_base100(
            df=df,
            macro_asset=macro_asset,
            market_asset=market_asset,
            label=label,
            description=description
        )

    if GENERATE_ROLLING_CORR_CHART:
        gerar_grafico_rolling_corr(
            df=df,
            macro_asset=macro_asset,
            market_asset=market_asset,
            label=label
        )

    export_resultados(
        df=df,
        summary_df=summary_df,
        pair_key=pair_key,
        macro_asset=macro_asset,
        market_asset=market_asset
    )

    return summary_df


# =========================
# MAIN
# =========================

def main():
    print("\nA iniciar Macro Liquidity Market Analysis...")
    print(f"Run mode: {RUN_MODE}")
    print(f"Start date: {START_DATE}")
    print(f"End date: {END_DATE}")
    print(f"Pares configurados: {len(LIQUIDITY_MARKET_PAIRS)}")

    engine = get_engine()

    final_summaries = []

    if RUN_MODE == "single":
        if SELECTED_PAIR_KEY not in LIQUIDITY_MARKET_PAIRS:
            raise ValueError(
                f"SELECTED_PAIR_KEY does not exist: {SELECTED_PAIR_KEY}"
            )

        config = LIQUIDITY_MARKET_PAIRS[SELECTED_PAIR_KEY]

        summary_df = executar_par(
            pair_key=SELECTED_PAIR_KEY,
            config=config,
            engine=engine
        )

        final_summaries.append(summary_df)

    elif RUN_MODE == "all":
        for idx, (pair_key, config) in enumerate(LIQUIDITY_MARKET_PAIRS.items(), start=1):
            print("\n" + "#" * 130)
            print(f"[{idx}/{len(LIQUIDITY_MARKET_PAIRS)}] {pair_key}")
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
            "macro_liquidity_market_summary_all.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print("\nSummary final exportado:")
        print("macro_liquidity_market_summary_all.csv")

    print("\nMacro Liquidity Market Analysis completed.")


if __name__ == "__main__":
    main()

