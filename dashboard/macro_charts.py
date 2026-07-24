import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def make_base100_chart(df, left_col, right_col, left_name, right_name, title):
    norm_df = df[["snapped_at", left_col, right_col]].copy()
    norm_df = norm_df.sort_values("snapped_at").reset_index(drop=True)

    for col in [left_col, right_col]:
        series = norm_df[col].dropna()

        if series.empty:
            continue

        base_value = series.iloc[0]

        if base_value == 0:
            continue

        norm_df[col] = (norm_df[col] / base_value) * 100

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=norm_df["snapped_at"],
            y=norm_df[left_col],
            mode="lines",
            name=f"{left_name} Base 100",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=norm_df["snapped_at"],
            y=norm_df[right_col],
            mode="lines",
            name=f"{right_name} Base 100",
        )
    )

    fig.add_hline(y=100, line_dash="dash", opacity=0.5)

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=600,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Base 100",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    return fig


def make_dual_axis_chart(df, macro_col, market_col, macro_name, market_name, macro_unit, title):
    plot_df = df[["snapped_at", macro_col, market_col]].copy()
    plot_df = plot_df.sort_values("snapped_at").reset_index(drop=True)

    market_series = plot_df[market_col].dropna()

    if market_series.empty:
        return None

    market_base = market_series.iloc[0]

    if market_base == 0:
        return None

    plot_df[f"{market_col}_base100"] = (plot_df[market_col] / market_base) * 100

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df[f"{market_col}_base100"],
            mode="lines",
            name=f"{market_name} Base 100",
            yaxis="y1",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df[macro_col],
            mode="lines",
            name=f"{macro_name} ({macro_unit})",
            yaxis="y2",
            line=dict(dash="dot"),
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=600,
        hovermode="x unified",
        xaxis=dict(title="Date"),
        yaxis=dict(
            title=f"{market_name} Base 100",
            side="left",
        ),
        yaxis2=dict(
            title=f"{macro_name} ({macro_unit})",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    return fig


def make_summary_cards(df, macro_col, market_col):
    col1, col2, col3, col4 = st.columns(4)

    start_date = df["snapped_at"].min()
    end_date = df["snapped_at"].max()

    market_series = df[market_col].dropna()
    market_latest = market_series.iloc[-1] if not market_series.empty else None

    with col1:
        st.metric("Observacoes", f"{len(df):,}")

    with col2:
        st.metric("Start date", str(start_date.date()) if pd.notna(start_date) else "-")

    with col3:
        st.metric("End date", str(end_date.date()) if pd.notna(end_date) else "-")

    with col4:
        st.metric("Latest market value", f"{market_latest:,.2f}" if market_latest is not None else "-")
