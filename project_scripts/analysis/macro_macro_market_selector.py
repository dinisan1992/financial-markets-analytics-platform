from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from asset_config import ASSETS
from macro_config import (
    MACRO_ASSETS,
    MACRO_GROUPS,
    MACRO_MARKET_PAIRS
)
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

EXPORT_REPORT = True

ROLLING_CORR_WINDOWS = [90, 180, 252]

pio.renderers.default = "browser"


# =========================
# MENU PRINCIPAL
# =========================

def mostrar_menu_principal():
    print("\n" + "=" * 100)
    print("SELETOR MACRO / MARKET ANALYSIS")
    print("=" * 100)
    print("1 - Usar par macro/market predefinido")
    print("2 - Chooser indicador macro e asset manualmente")
    print("3 - View available macro groups")
    print("0 - Exit")
    print("=" * 100)


# =========================
# MENU DE PARES PREDEFINIDOS
# =========================

def chooser_par_predefinido():
    pair_items = list(MACRO_MARKET_PAIRS.items())

    print("\n" + "=" * 120)
    print("PARES MACRO / MERCADO PREDEFINIDOS")
    print("=" * 120)

    for i, (pair_key, pair_data) in enumerate(pair_items, start=1):
        print(
            f"{i:02d} - "
            f"{pair_data['name']} | "
            f"{pair_data['description']}"
        )

    print("=" * 120)
    print("0 - Voltar")
    print("=" * 120)

    while True:
        choice = input("\nChoose o par: ").strip()

        if choice == "0":
            return None

        if not choice.isdigit():
            print("Invalid choice.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(pair_items):
            print("Number outside the list.")
            continue

        pair_key, pair_data = pair_items[choice_num - 1]

        return {
            "pair_key": pair_key,
            "macro_asset": pair_data["macro_asset"],
            "market_asset": pair_data["market_asset"],
            "label": pair_data["name"],
            "description": pair_data["description"]
        }


# =========================
# MENU DE INDICADORES MACRO
# =========================

def mostrar_macro_groups():
    print("\n" + "=" * 120)
    print("AVAILABLE MACRO GROUPS")
    print("=" * 120)

    for group_key, group_data in MACRO_GROUPS.items():
        print(f"\n{group_key} - {group_data['name']}")
        print(f"Description: {group_data['description']}")
        print("Indicadores:")

        for macro_key in group_data["assets"]:
            if macro_key in MACRO_ASSETS:
                cfg = MACRO_ASSETS[macro_key]
                print(
                    f"  - {macro_key:40s} | "
                    f"{cfg['display_name']} | "
                    f"{cfg['category']} | "
                    f"{cfg['region']}"
                )

    print("=" * 120)


def chooser_macro_por_grupo():
    group_items = list(MACRO_GROUPS.items())

    print("\n" + "=" * 120)
    print("ESCOLHER GROUP MACRO")
    print("=" * 120)

    for i, (group_key, group_data) in enumerate(group_items, start=1):
        print(
            f"{i:02d} - "
            f"{group_data['name']} | "
            f"{group_data['description']}"
        )

    print("=" * 120)
    print("98 - Ver todos os indicadores macro")
    print("0  - Voltar")
    print("=" * 120)

    while True:
        choice = input("\nChoose the group macro: ").strip()

        if choice == "0":
            return None

        if choice == "98":
            return chooser_macro_todos()

        if not choice.isdigit():
            print("Invalid choice.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(group_items):
            print("Number outside the list.")
            continue

        group_key, group_data = group_items[choice_num - 1]

        macro_keys = [
            macro_key for macro_key in group_data["assets"]
            if macro_key in MACRO_ASSETS
        ]

        return chooser_macro_de_lista(
            macro_keys=macro_keys,
            title=f"INDICADORES - {group_data['name']}"
        )


def chooser_macro_todos():
    macro_keys = list(MACRO_ASSETS.keys())

    return chooser_macro_de_lista(
        macro_keys=macro_keys,
        title="TODOS OS INDICADORES MACRO"
    )


def chooser_macro_de_lista(macro_keys, title):
    print("\n" + "=" * 130)
    print(title)
    print("=" * 130)

    for i, macro_key in enumerate(macro_keys, start=1):
        cfg = MACRO_ASSETS[macro_key]

        print(
            f"{i:02d} - "
            f"{macro_key:40s} | "
            f"{cfg['display_name']} | "
            f"{cfg['category']} | "
            f"{cfg['region']} | "
            f"{cfg['unit']}"
        )

    print("=" * 130)
    print("0 - Voltar")
    print("=" * 130)

    while True:
        choice = input("\nChoose o indicador macro: ").strip()

        if choice == "0":
            return None

        if not choice.isdigit():
            print("Invalid choice.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(macro_keys):
            print("Number outside the list.")
            continue

        return macro_keys[choice_num - 1]


# =========================
# MARKET ASSET MENU
# =========================

def chooser_asset_market():
    asset_keys = list(ASSETS.keys())

    print("\n" + "=" * 130)
    print("AVAILABLE MARKET ASSETS")
    print("=" * 130)

    for i, asset_key in enumerate(asset_keys, start=1):
        asset = ASSETS[asset_key]

        print(
            f"{i:02d} - "
            f"{asset_key:25s} | "
            f"{asset['display_name']} | "
            f"{asset['market_type']}"
        )

    print("=" * 130)
    print("0 - Voltar")
    print("=" * 130)

    while True:
        choice = input("\nChoose the asset de market: ").strip()

        if choice == "0":
            return None

        if not choice.isdigit():
            print("Invalid choice.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(asset_keys):
            print("Number outside the list.")
            continue

        return asset_keys[choice_num - 1]


def chooser_par_manual():
    macro_asset = chooser_macro_por_grupo()

    if macro_asset is None:
        return None

    market_asset = chooser_asset_market()

    if market_asset is None:
        return None

    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    return {
        "pair_key": f"custom_{macro_asset.lower()}_{market_asset.lower()}",
        "macro_asset": macro_asset,
        "market_asset": market_asset,
        "label": f"{macro_cfg['display_name']} vs {market_cfg['display_name']}",
        "description": "Par personalizado escolhido manualmente."
    }


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
            print("Invalid start date.")

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
    print("2 - Desde 2010")
    print("3 - Last 1 year")
    print("4 - Last 3 years")
    print("5 - Last 5 years")
    print("6 - Last 10 years")
    print("7 - Full available history")
    print("8 - Custom date")
    print("=" * 80)

    while True:
        choice = input("\nChoose the period: ").strip()

        if choice == "1":
            return "2020-01-01", None, "Since 2020"

        if choice == "2":
            return "2010-01-01", None, "Desde 2010"

        if choice == "3":
            return calcular_data_inicio_anos(1), None, "Last 1 year"

        if choice == "4":
            return calcular_data_inicio_anos(3), None, "Last 3 years"

        if choice == "5":
            return calcular_data_inicio_anos(5), None, "Last 5 years"

        if choice == "6":
            return calcular_data_inicio_anos(10), None, "Last 10 years"

        if choice == "7":
            return None, None, "Full history"

        if choice == "8":
            return chooser_periodo_personalizado()

        print("Invalid choice.")


# =========================
# MENU DE TIPO DE ANALYSIS
# =========================

def chooser_tipo_analise():
    print("\n" + "=" * 90)
    print("COMPARISON TYPE")
    print("=" * 90)
    print("1 - Chart dual axis")
    print("2 - Chart base 100")
    print("3 - Rolling correlation")
    print("4 - Statistical summary")
    print("5 - Tudo")
    print("=" * 90)

    while True:
        choice = input("\nChoose o tipo de analysis: ").strip()

        if choice == "1":
            return "dual_axis"

        if choice == "2":
            return "base100"

        if choice == "3":
            return "rolling_corr"

        if choice == "4":
            return "summary"

        if choice == "5":
            return "all"

        print("Invalid choice.")


# =========================
# CALCULATIONS
# =========================

def preparar_features(df, macro_asset, market_asset):
    df = df.copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    df[f"{macro_asset}_abs_change_30d"] = df[macro_asset] - df[macro_asset].shift(30)
    df[f"{macro_asset}_abs_change_90d"] = df[macro_asset] - df[macro_asset].shift(90)
    df[f"{macro_asset}_abs_change_180d"] = df[macro_asset] - df[macro_asset].shift(180)
    df[f"{macro_asset}_abs_change_252d"] = df[macro_asset] - df[macro_asset].shift(252)

    df[f"{macro_asset}_pct_change_30d"] = df[macro_asset].pct_change(30)
    df[f"{macro_asset}_pct_change_90d"] = df[macro_asset].pct_change(90)
    df[f"{macro_asset}_pct_change_180d"] = df[macro_asset].pct_change(180)
    df[f"{macro_asset}_pct_change_252d"] = df[macro_asset].pct_change(252)

    df[f"{market_asset}_return_30d"] = df[market_asset].pct_change(30)
    df[f"{market_asset}_return_90d"] = df[market_asset].pct_change(90)
    df[f"{market_asset}_return_180d"] = df[market_asset].pct_change(180)
    df[f"{market_asset}_return_252d"] = df[market_asset].pct_change(252)

    macro_mean = df[macro_asset].rolling(252, min_periods=60).mean()
    macro_std = df[macro_asset].rolling(252, min_periods=60).std()

    df[f"{macro_asset}_zscore_252d"] = (
        (df[macro_asset] - macro_mean) / macro_std
    )

    return df


def calcular_rolling_corr(df, macro_asset, market_asset):
    df = df.copy()

    macro_abs_col = f"{macro_asset}_abs_change_90d"
    macro_pct_col = f"{macro_asset}_pct_change_90d"
    market_return_col = f"{market_asset}_return_90d"

    for window in ROLLING_CORR_WINDOWS:
        df[f"rolling_corr_abs_{window}d"] = (
            df[macro_abs_col]
            .rolling(window=window, min_periods=max(20, int(window * 0.6)))
            .corr(df[market_return_col])
        )

        df[f"rolling_corr_pct_{window}d"] = (
            df[macro_pct_col]
            .rolling(window=window, min_periods=max(20, int(window * 0.6)))
            .corr(df[market_return_col])
        )

    return df


# =========================
# SUMMARY
# =========================

def gerar_summary(df, macro_asset, market_asset, label):
    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    macro_series = df[macro_asset].dropna()
    market_series = df[market_asset].dropna()

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

    correlations = {}

    for window in [30, 90, 180, 252]:
        macro_abs_col = f"{macro_asset}_abs_change_{window}d"
        macro_pct_col = f"{macro_asset}_pct_change_{window}d"
        market_col = f"{market_asset}_return_{window}d"

        if macro_abs_col in df.columns and market_col in df.columns:
            corr_df = df[[macro_abs_col, market_col]].dropna()

            correlations[f"corr_{window}d_macro_abs_vs_market_return"] = (
                round(corr_df[macro_abs_col].corr(corr_df[market_col]), 4)
                if len(corr_df) >= 30
                else None
            )

        if macro_pct_col in df.columns and market_col in df.columns:
            corr_df = df[[macro_pct_col, market_col]].dropna()

            correlations[f"corr_{window}d_macro_pct_vs_market_return"] = (
                round(corr_df[macro_pct_col].corr(corr_df[market_col]), 4)
                if len(corr_df) >= 30
                else None
            )

    zscore_col = f"{macro_asset}_zscore_252d"

    latest_zscore = None

    if zscore_col in df.columns:
        zscore_series = df[zscore_col].dropna()

        if not zscore_series.empty:
            latest_zscore = zscore_series.iloc[-1]

    summary = {
        "label": label,
        "macro_asset": macro_asset,
        "macro_display_name": macro_cfg["display_name"],
        "macro_category": macro_cfg["category"],
        "macro_region": macro_cfg["region"],
        "macro_unit": macro_cfg["unit"],
        "market_asset": market_asset,
        "market_display_name": market_cfg["display_name"],
        "market_type": market_cfg["market_type"],
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
        "latest_macro_zscore_252d": round(latest_zscore, 4) if latest_zscore is not None else None,
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
# CHARTS
# =========================

def gerar_grafico_dual_axis(df, macro_asset, market_asset, label, description, period_label):
    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    market_base = df[market_asset].dropna().iloc[0]

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
            text=f"Macro / Market Dual Axis - {label} | {period_label}",
            x=0.5,
            xanchor="center",
            font=dict(size=20, color="white")
        ),
        template="plotly_dark",
        height=820,
        width=1550,
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
        margin=dict(l=80, r=270, t=120, b=70),
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


def gerar_grafico_base100(df, macro_asset, market_asset, label, period_label):
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
            text=f"Macro / Market Base 100 - {label} | {period_label}",
            x=0.5,
            xanchor="center",
            font=dict(size=20, color="white")
        ),
        template="plotly_dark",
        height=780,
        width=1550,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Base 100",
        margin=dict(l=80, r=250, t=110, b=70),
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


def gerar_grafico_rolling_corr(df, macro_asset, market_asset, label, period_label):
    fig = go.Figure()

    corr_cols = [
        col for col in df.columns
        if col.startswith("rolling_corr_abs_")
    ]

    for col in corr_cols:
        window_label = col.replace("rolling_corr_abs_", "").replace("d", "")

        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df[col],
                mode="lines",
                name=f"{window_label}D Corr Abs Change",
                hovertemplate=(
                    f"<b>{label}</b><br>"
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
            text=f"Macro / Market Rolling Correlation - {label} | {period_label}",
            x=0.5,
            xanchor="center",
            font=dict(size=19, color="white")
        ),
        template="plotly_dark",
        height=760,
        width=1550,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Rolling Correlation",
        yaxis=dict(range=[-1, 1]),
        margin=dict(l=80, r=230, t=110, b=70),
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

def export_resultados(df, summary_df, pair_key):
    if not EXPORT_REPORT:
        return

    safe_key = (
        pair_key
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .lower()
    )

    data_output = f"macro_market_selector_{safe_key}.csv"
    summary_output = f"macro_market_selector_summary_{safe_key}.csv"

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
# EXECUTAR ANALYSIS
# =========================

def executar_analise(pair_config):
    start_date, end_date, period_label = chooser_periodo()
    analysis_type = chooser_tipo_analise()

    pair_key = pair_config["pair_key"]
    macro_asset = pair_config["macro_asset"]
    market_asset = pair_config["market_asset"]
    label = pair_config["label"]
    description = pair_config["description"]

    macro_cfg = MACRO_ASSETS[macro_asset]
    market_cfg = ASSETS[market_asset]

    print("\n" + "=" * 130)
    print("MACRO / MARKET ANALYSIS")
    print("=" * 130)
    print(f"Par: {label}")
    print(f"Description: {description}")
    print(f"Macro: {macro_asset} | {macro_cfg['display_name']} | {macro_cfg['category']} | {macro_cfg['region']}")
    print(f"Market: {market_asset} | {market_cfg['display_name']} | {market_cfg['market_type']}")
    print(f"Period: {period_label}")
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print(f"Tipo de analysis: {analysis_type}")
    print("=" * 130)

    engine = get_engine()

    df = alinhar_macro_com_market(
        macro_key=macro_asset,
        market_asset=market_asset,
        engine=engine,
        start_date=start_date,
        end_date=end_date,
        how="outer",
        forward_fill=True
    )

    summary_dataset(df)

    df = preparar_features(
        df=df,
        macro_asset=macro_asset,
        market_asset=market_asset
    )

    df = calcular_rolling_corr(
        df=df,
        macro_asset=macro_asset,
        market_asset=market_asset
    )

    summary_df = gerar_summary(
        df=df,
        macro_asset=macro_asset,
        market_asset=market_asset,
        label=label
    )

    if analysis_type in ["dual_axis", "all"]:
        gerar_grafico_dual_axis(
            df=df,
            macro_asset=macro_asset,
            market_asset=market_asset,
            label=label,
            description=description,
            period_label=period_label
        )

    if analysis_type in ["base100", "all"]:
        gerar_grafico_base100(
            df=df,
            macro_asset=macro_asset,
            market_asset=market_asset,
            label=label,
            period_label=period_label
        )

    if analysis_type in ["rolling_corr", "all"]:
        gerar_grafico_rolling_corr(
            df=df,
            macro_asset=macro_asset,
            market_asset=market_asset,
            label=label,
            period_label=period_label
        )

    export_resultados(
        df=df,
        summary_df=summary_df,
        pair_key=pair_key
    )

    print("\nAnalysis macro/market completed.")


# =========================
# MAIN
# =========================

def main():
    while True:
        mostrar_menu_principal()

        choice = input("\nChoose an option: ").strip()

        if choice == "0":
            print("\nExiting the Macro / Market Analysis selector.")
            break

        elif choice == "1":
            pair_config = chooser_par_predefinido()

            if pair_config is None:
                continue

            try:
                executar_analise(pair_config)

            except Exception as e:
                print("\nERROR while running analysis:")
                print(e)

            input("\nPressiona ENTER para voltar ao menu...")

        elif choice == "2":
            pair_config = chooser_par_manual()

            if pair_config is None:
                continue

            try:
                executar_analise(pair_config)

            except Exception as e:
                print("\nERROR while running analysis:")
                print(e)

            input("\nPressiona ENTER para voltar ao menu...")

        elif choice == "3":
            mostrar_macro_groups()
            input("\nPressiona ENTER para voltar ao menu...")

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
