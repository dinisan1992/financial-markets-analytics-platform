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

SELECTED_PAIR_KEY = "fed_delinquency_vix"

GENERATE_DUAL_AXIS_CHART = True
GENERATE_BASE100_CHART = True
GENERATE_STRESS_REGIME_CHART = True
GENERATE_ROLLING_CORR_CHART = True

ROLLING_CORR_WINDOWS = [90, 180, 252]

pio.renderers.default = "browser"


# =========================
# CREDIT / STRESS / MARKET PAIRS
# =========================
# Note:
# For now, only FED indicators are used because EURO indicators are disabled
# until dedicated filters are created for multidimensional tables.

CREDIT_STRESS_MARKET_PAIRS = {
    "fed_delinquency_vix": {
        "macro_asset": "FED_CREDIT_CARD_DELINQUENCY",
        "market_asset": "VIX",
        "label": "Credit Card Delinquency vs VIX",
        "description": "Compares US consumer stress with equity volatility."
    },

    "fed_charge_off_vix": {
        "macro_asset": "FED_CHARGE_OFF_RATE_CREDIT_CARDS",
        "market_asset": "VIX",
        "label": "Credit Card Charge-Off Rate vs VIX",
        "description": "Compares credit card losses with equity volatility."
    },

    "fed_charge_off_sp500": {
        "macro_asset": "FED_CHARGE_OFF_RATE_CREDIT_CARDS",
        "market_asset": "SP500",
        "label": "Credit Card Charge-Off Rate vs S&P 500",
        "description": "Analisa se perdas no credit ao consumo acompanham fraqueza em equities."
    },

    "fed_consumer_loans_nasdaq": {
        "macro_asset": "FED_CONSUMER_LOANS_CREDIT_CARDS",
        "market_asset": "NASDAQ100",
        "label": "Consumer Credit Card Loans vs NASDAQ 100",
        "description": "Compares revolving credit expansion with risk/growth assets."
    },

    "fed_bank_credit_sp500": {
        "macro_asset": "FED_BANK_CREDIT",
        "market_asset": "SP500",
        "label": "Bank Credit vs S&P 500",
        "description": "Compares aggregate bank credit with the US equity market."
    },

    "fed_bank_credit_financial_conditions": {
        "macro_asset": "FED_BANK_CREDIT",
        "market_asset": "FINANCIAL_CONDITIONS",
        "label": "Bank Credit vs Financial Conditions",
        "description": "Compares bank credit with financial conditions."
    },

    "fed_loans_leases_sp500": {
        "macro_asset": "FED_LOANS_LEASES",
        "market_asset": "SP500",
        "label": "Loans and Leases vs S&P 500",
        "description": "Compares loans and leases with US equities."
    },

    "fed_deposits_financial_conditions": {
        "macro_asset": "FED_DEPOSITS",
        "market_asset": "FINANCIAL_CONDITIONS",
        "label": "Commercial Bank Deposits vs Financial Conditions",
        "description": "Compares bank deposits with stress/financial conditions."
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

    df[f"{macro_asset}_abs_change_90obs"] = (
        df[macro_asset] - df[macro_asset].shift(90)
    )

    df[f"{macro_asset}_pct_change_90obs"] = (
        df[macro_asset].pct_change(90)
    )

    df[f"{market_asset}_return_90obs"] = (
        df[market_asset].pct_change(90)
    )

    macro_abs_col = f"{macro_asset}_abs_change_90obs"
    macro_pct_col = f"{macro_asset}_pct_change_90obs"
    market_return_col = f"{market_asset}_return_90obs"

    for window in ROLLING_CORR_WINDOWS:
        abs_corr_col = f"rolling_corr_abs_{window}obs"
        pct_corr_col = f"rolling_corr_pct_{window}obs"

        df[abs_corr_col] = (
            df[macro_abs_col]
            .rolling(
                window=window,
                min_periods=max(20, int(window * 0.6))
            )
            .corr(df[market_return_col])
        )

        df[pct_corr_col] = (
            df[macro_pct_col]
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

def gerar_summary_credit_stress(df, macro_asset, market_asset, label):
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

    macro_absolute_change = macro_end - macro_start

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
        macro_pct_col = f"{macro_asset}_pct_change_{window}d"
        macro_abs_col = f"{macro_asset}_abs_change_{window}d"
        market_col = f"{market_asset}_pct_change_{window}d"

        if macro_pct_col in df_changes.columns and market_col in df_changes.columns:
            corr_pct_df = df_changes[[macro_pct_col, market_col]].dropna()

            if len(corr_pct_df) >= 30:
                correlations[f"corr_{window}obs_macro_pct_vs_market_return"] = round(
                    corr_pct_df[macro_pct_col].corr(corr_pct_df[market_col]),
                    4
                )
            else:
                correlations[f"corr_{window}obs_macro_pct_vs_market_return"] = None
        else:
            correlations[f"corr_{window}obs_macro_pct_vs_market_return"] = None

        if macro_abs_col in df_changes.columns and market_col in df_changes.columns:
            corr_abs_df = df_changes[[macro_abs_col, market_col]].dropna()

            if len(corr_abs_df) >= 30:
                correlations[f"corr_{window}obs_macro_abs_vs_market_return"] = round(
                    corr_abs_df[macro_abs_col].corr(corr_abs_df[market_col]),
                    4
                )
            else:
                correlations[f"corr_{window}obs_macro_abs_vs_market_return"] = None
        else:
            correlations[f"corr_{window}obs_macro_abs_vs_market_return"] = None

    latest_rows = df.tail(252).copy()

    recent_macro_change = None
    recent_market_return = None

    if len(latest_rows) > 30:
        recent_macro_change = (
            latest_rows[macro_asset].iloc[-1]
            - latest_rows[macro_asset].iloc[0]
        )

        if latest_rows[market_asset].iloc[0] != 0:
            recent_market_return = (
                (latest_rows[market_asset].iloc[-1] / latest_rows[market_asset].iloc[0]) - 1
            ) * 100

    summary = {
        "label": label,
        "macro_asset": macro_asset,
        "macro_display_name": macro_cfg["display_name"],
        "macro_table": macro_cfg["table_name"],
        "macro_value_col": macro_cfg["value_col"],
        "macro_category": macro_cfg["category"],
        "market_asset": market_asset,
        "market_display_name": market_cfg["display_name"],
        "start_date": df["snapped_at"].min().date(),
        "end_date": df["snapped_at"].max().date(),
        "observations": len(df),
        "macro_start": round(macro_start, 4),
        "macro_end": round(macro_end, 4),
        "macro_absolute_change": round(macro_absolute_change, 4),
        "macro_total_change_pct": round(macro_total_change_pct, 2) if macro_total_change_pct is not None else None,
        "market_start": round(market_start, 4),
        "market_end": round(market_end, 4),
        "market_total_return_pct": round(market_total_return_pct, 2) if market_total_return_pct is not None else None,
        "recent_252obs_macro_abs_change": round(recent_macro_change, 4) if recent_macro_change is not None else None,
        "recent_252obs_market_return_pct": round(recent_market_return, 2) if recent_market_return is not None else None,
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
# SIMPLE STRESS CLASSIFICATION
# =========================

def classificar_stress_macro(df, macro_asset):
    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    rolling_mean = df[macro_asset].rolling(252, min_periods=60).mean()
    rolling_std = df[macro_asset].rolling(252, min_periods=60).std()

    zscore_col = f"{macro_asset}_zscore_252obs"

    df[zscore_col] = (
        (df[macro_asset] - rolling_mean) / rolling_std
    )

    def regime_from_zscore(z):
        if pd.isna(z):
            return "insufficient_data"

        if z >= 2:
            return "extreme_stress"

        if z >= 1:
            return "high_stress"

        if z <= -1:
            return "low_stress"

        return "normal"

    df["macro_stress_regime"] = df[zscore_col].apply(
        regime_from_zscore
    )

    return df


# =========================
# DUAL-AXIS CHART
# =========================

def gerar_grafico_dual_axis(df, macro_asset, market_asset, label, description):
    macro_cfg = MACRO_ASSETS[macro_asset]
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
            y=plot_df[macro_asset],
            mode="lines",
            name=f"{macro_cfg['display_name']} ({macro_cfg['unit']})",
            yaxis="y2",
            line=dict(
                dash="dot",
                width=2
            ),
            hovertemplate=(
                f"<b>{macro_cfg['display_name']}</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Value: %{y:.4f}<br>"
                f"Unit: {macro_cfg['unit']}"
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
            text=f"Credit / Stress vs Market - {label}",
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
            title=f"{macro_cfg['display_name']} ({macro_cfg['unit']})",
            overlaying="y",
            side="right",
            showgrid=False
        ),
        margin=dict(l=80, r=260, t=115, b=70),
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

def gerar_grafico_base100(df, macro_asset, market_asset, label):
    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    norm_df = normalizar_base_100(
        df[["snapped_at", macro_asset, market_asset]].copy()
    )

    if macro_asset not in norm_df.columns or market_asset not in norm_df.columns:
        print("Warning: not foi possible gerar base 100 para este par.")
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
# CHART STRESS REGIME
# =========================

def gerar_grafico_stress_regime(df, macro_asset, market_asset, label):
    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    zscore_col = f"{macro_asset}_zscore_252obs"

    if zscore_col not in df.columns:
        print("Warning: z-score not encontrado para chart de stress.")
        return None

    market_base = df[market_asset].dropna().iloc[0]

    if market_base == 0:
        print("Warning: market base value is zero. Not foi possible gerar chart stress regime.")
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
            y=plot_df[zscore_col],
            mode="lines",
            name=f"{macro_cfg['display_name']} Z-Score 252 obs",
            yaxis="y2",
            line=dict(
                dash="dot",
                width=2
            ),
            hovertemplate=(
                f"<b>{macro_cfg['display_name']} Z-Score</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Z-Score: %{y:.2f}"
                "<extra></extra>"
            )
        )
    )

    fig.add_hline(
        y=2,
        line_dash="dash",
        opacity=0.4,
        annotation_text="Extreme stress",
        annotation_position="top right",
        yref="y2"
    )

    fig.add_hline(
        y=1,
        line_dash="dot",
        opacity=0.4,
        annotation_text="High stress",
        annotation_position="top right",
        yref="y2"
    )

    fig.add_hline(
        y=0,
        line_dash="dash",
        opacity=0.3,
        annotation_text="Normal",
        annotation_position="bottom right",
        yref="y2"
    )

    fig.update_layout(
        title=dict(
            text=f"Macro Stress Regime - {label}",
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
            title=f"{macro_cfg['display_name']} Z-Score",
            overlaying="y",
            side="right",
            showgrid=False
        ),
        margin=dict(l=80, r=260, t=110, b=70),
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

def gerar_grafico_rolling_corr(df, macro_asset, market_asset, label):
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
            text=f"Rolling Correlation - Credit/Stress Change vs Market Return | {label}",
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

    data_output = f"macro_credit_stress_{safe_name}.csv"
    summary_output = f"macro_credit_stress_summary_{safe_name}.csv"

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
    print(f"CREDIT / STRESS MARKET ANALYSIS - {label}")
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

    df = classificar_stress_macro(
        df=df,
        macro_asset=macro_asset
    )

    summary_df = gerar_summary_credit_stress(
        df=df,
        macro_asset=macro_asset,
        market_asset=market_asset,
        label=label
    )

    if GENERATE_DUAL_AXIS_CHART:
        gerar_grafico_dual_axis(
            df=df,
            macro_asset=macro_asset,
            market_asset=market_asset,
            label=label,
            description=description
        )

    if GENERATE_BASE100_CHART:
        gerar_grafico_base100(
            df=df,
            macro_asset=macro_asset,
            market_asset=market_asset,
            label=label
        )

    if GENERATE_STRESS_REGIME_CHART:
        gerar_grafico_stress_regime(
            df=df,
            macro_asset=macro_asset,
            market_asset=market_asset,
            label=label
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
    print("\nA iniciar Macro Credit & Stress Analysis...")
    print(f"Run mode: {RUN_MODE}")
    print(f"Start date: {START_DATE}")
    print(f"End date: {END_DATE}")
    print(f"Pares configurados: {len(CREDIT_STRESS_MARKET_PAIRS)}")

    engine = get_engine()

    final_summaries = []

    if RUN_MODE == "single":
        if SELECTED_PAIR_KEY not in CREDIT_STRESS_MARKET_PAIRS:
            raise ValueError(
                f"SELECTED_PAIR_KEY does not exist: {SELECTED_PAIR_KEY}"
            )

        config = CREDIT_STRESS_MARKET_PAIRS[SELECTED_PAIR_KEY]

        summary_df = executar_par(
            pair_key=SELECTED_PAIR_KEY,
            config=config,
            engine=engine
        )

        final_summaries.append(summary_df)

    elif RUN_MODE == "all":
        for idx, (pair_key, config) in enumerate(CREDIT_STRESS_MARKET_PAIRS.items(), start=1):
            print("\n" + "#" * 130)
            print(f"[{idx}/{len(CREDIT_STRESS_MARKET_PAIRS)}] {pair_key}")
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
            "macro_credit_stress_summary_all.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print("\nSummary final exportado:")
        print("macro_credit_stress_summary_all.csv")

    print("\nMacro Credit & Stress Analysis completed.")


if __name__ == "__main__":
    main()

