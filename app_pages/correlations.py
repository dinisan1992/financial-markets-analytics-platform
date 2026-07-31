from dataclasses import dataclass
from datetime import date
from typing import Callable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from asset_config import ASSETS
from dashboard.correlation_charts import (
    make_base100_multi_asset_chart,
    make_correlation_heatmap,
    make_returns_scatter_chart,
    make_rolling_correlation_chart,
)
from dashboard.correlation_data import (
    build_multi_asset_price_frame,
    build_scatter_returns_frame,
    calculate_correlation_matrix,
    calculate_returns,
    calculate_rolling_correlation,
    normalize_base_100,
)
from services.correlation_quality_service import build_pair_correlation_statistics


@dataclass(frozen=True)
class CorrelationsDeps:
    get_engine: Callable
    render_date_range_selector: Callable
    date_to_str: Callable


def render_correlations(deps: CorrelationsDeps):
    st.title("Correlations")

    st.markdown(
        """
        Multi-asset analysis with correlation matrix, rolling correlation,
        returns scatter, correlation rankings and normalized performance.
        """
    )

    selected_assets, start_date, end_date = _render_asset_date_controls(deps)
    return_method, correlation_window, load_corr_button = _render_correlation_controls()

    if len(selected_assets) < 2:
        st.warning("Select at least two assets.")
        return

    if load_corr_button:
        _load_correlation_data(
            deps=deps,
            selected_assets=selected_assets,
            start_date=start_date,
            end_date=end_date,
            return_method=return_method,
            correlation_window=correlation_window,
        )

    if not st.session_state.get("corr_loaded", False):
        st.info("Choose at least two assets and click Load correlations.")
        return

    _render_loaded_correlations(
        deps=deps,
        selected_assets=selected_assets,
        start_date=start_date,
        end_date=end_date,
        correlation_window=correlation_window,
    )


def _render_asset_date_controls(deps: CorrelationsDeps):
    default_assets = [
        asset for asset in [
            "BTC",
            "SP500",
            "NASDAQ100",
            "GOLD",
            "DXY",
            "VIX",
            "US10Y",
            "WTI_OIL",
            "BRENT_OIL",
        ]
        if asset in ASSETS
    ]

    c1, c2 = st.columns([2, 2])

    with c1:
        selected_assets = st.multiselect(
            "Assets",
            options=list(ASSETS.keys()),
            default=default_assets,
            format_func=lambda key: f"{key} - {ASSETS[key]['display_name']}",
        )

    with c2:
        start_date, end_date = deps.render_date_range_selector(
            default_start=date(2020, 1, 1),
            default_end=date.today(),
        )

    return selected_assets, start_date, end_date


def _render_correlation_controls():
    c3, c4, c5 = st.columns(3)

    with c3:
        return_method = st.selectbox(
            "Return Type",
            ["pct", "log"],
            format_func=lambda value: "Simple Percentage" if value == "pct" else "Logarithmic",
        )

    with c4:
        correlation_window = st.slider(
            "Rolling Correlation Window (observations)",
            min_value=30,
            max_value=365,
            value=90,
            step=15,
        )

    with c5:
        st.markdown("###")
        load_corr_button = st.button(
            "Load correlations",
            width="stretch",
        )

    return return_method, correlation_window, load_corr_button


def _load_correlation_data(
    deps: CorrelationsDeps,
    selected_assets,
    start_date,
    end_date,
    return_method,
    correlation_window,
):
    try:
        with st.spinner("Loading multi-asset prices..."):
            price_df, load_report = build_multi_asset_price_frame(
                engine=deps.get_engine(),
                selected_assets=selected_assets,
                assets_config=ASSETS,
                start_date=deps.date_to_str(start_date),
                end_date=deps.date_to_str(end_date),
                forward_fill=False,
                return_load_report=True,
            )

        if price_df.empty:
            st.warning("Unable to load data for the selected assets.")
            st.session_state.corr_loaded = False
            st.session_state.corr_load_report = load_report
            return

        loaded_assets = [
            column for column in price_df.columns
            if column != "snapped_at"
        ]

        if len(loaded_assets) < 2:
            st.warning("Fewer than two requested assets produced valid prices.")
            st.session_state.corr_loaded = False
            st.session_state.corr_load_report = load_report
            return

        returns_df = calculate_returns(
            price_df=price_df,
            method=return_method,
        )

        corr_df = calculate_correlation_matrix(
            returns_df=returns_df,
            min_periods=30,
        )

        corr_pairs_df = build_pair_correlation_statistics(returns_df)

        st.session_state.corr_loaded = True
        st.session_state.corr_price_df = price_df
        st.session_state.corr_returns_df = returns_df
        st.session_state.corr_corr_df = corr_df
        st.session_state.corr_pairs_df = corr_pairs_df
        st.session_state.corr_selected_assets = loaded_assets
        st.session_state.corr_window = correlation_window
        st.session_state.corr_load_report = load_report

        st.success("Correlation data loaded successfully.")

    except Exception as exc:
        st.session_state.corr_loaded = False
        st.error(f"Error loading correlation analysis: {exc}")


def _render_loaded_correlations(
    deps: CorrelationsDeps,
    selected_assets,
    start_date,
    end_date,
    correlation_window,
):
    price_df = st.session_state.corr_price_df
    returns_df = st.session_state.corr_returns_df
    corr_df = st.session_state.corr_corr_df
    corr_pairs_df = st.session_state.corr_pairs_df
    loaded_assets = st.session_state.corr_selected_assets or selected_assets
    load_report = st.session_state.get("corr_load_report")

    if price_df is None or returns_df is None or corr_df is None:
        st.warning("Correlation data is not available. Please reload.")
        return

    _render_load_report(load_report)

    _render_correlation_summary(
        deps=deps,
        returns_df=returns_df,
        corr_pairs_df=corr_pairs_df,
        loaded_assets=loaded_assets,
        start_date=start_date,
        end_date=end_date,
    )

    st.markdown("---")

    tab_heatmap, tab_rankings, tab_pair, tab_base100, tab_data = st.tabs(
        [
            "Heatmap",
            "Top Correlations",
            "Pair Analysis",
            "Base 100",
            "Data",
        ],
        on_change="rerun",
    )

    if tab_heatmap.open:
        with tab_heatmap:
            _render_heatmap_tab(corr_df)

    if tab_rankings.open:
        with tab_rankings:
            _render_rankings_tab(corr_pairs_df, loaded_assets)

    if tab_pair.open:
        with tab_pair:
            _render_pair_tab(
                returns_df,
                corr_pairs_df,
                loaded_assets,
                correlation_window,
            )

    if tab_base100.open:
        with tab_base100:
            _render_base100_tab(price_df, loaded_assets)

    if tab_data.open:
        with tab_data:
            _render_data_tab(price_df, returns_df, corr_df, corr_pairs_df)


def _render_correlation_summary(
    deps: CorrelationsDeps,
    returns_df,
    corr_pairs_df,
    loaded_assets,
    start_date,
    end_date,
):
    period_start = deps.date_to_str(start_date)
    period_end = deps.date_to_str(end_date)
    valid_pairs = (
        corr_pairs_df.dropna(subset=["correlation"])
        if corr_pairs_df is not None and not corr_pairs_df.empty
        else pd.DataFrame()
    )
    avg_corr = valid_pairs["correlation"].mean() if not valid_pairs.empty else None

    top_positive = None
    top_negative = None

    if not valid_pairs.empty:
        top_positive = valid_pairs.sort_values(
            "correlation",
            ascending=False,
        ).iloc[0]

        top_negative = valid_pairs.sort_values(
            "correlation",
            ascending=True,
        ).iloc[0]

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("Assets", len(loaded_assets))

    with k2:
        st.metric("Return Dates", f"{len(returns_df):,}")

    with k3:
        st.metric("Average Correlation", f"{avg_corr:.2f}" if avg_corr is not None else "-")

    with k4:
        st.metric("Period", f"{period_start[:4]} to {period_end[:4]}")

    st.caption(f"Loaded date range: {period_start} to {period_end}.")

    if top_positive is not None and top_negative is not None:
        p1, p2 = st.columns(2)

        with p1:
            st.info(
                f"Highest positive correlation: "
                f"{top_positive['asset_a']} / {top_positive['asset_b']} "
                f"= {top_positive['correlation']:.2f}"
            )

        with p2:
            st.info(
                f"Lowest correlation: "
                f"{top_negative['asset_a']} / {top_negative['asset_b']} "
                f"= {top_negative['correlation']:.2f}"
            )


def _render_load_report(load_report):
    if load_report is None or load_report.empty:
        return

    requested = len(load_report)
    loaded = int(load_report["status"].eq("loaded").sum())
    failed = requested - loaded

    with st.container(horizontal=True):
        st.metric("Assets Requested", requested, border=True)
        st.metric("Assets Loaded", loaded, border=True)
        st.metric("Assets Not Loaded", failed, border=True)

    if failed:
        st.dataframe(
            load_report[load_report["status"] != "loaded"],
            hide_index=True,
            width="stretch",
        )


def _render_heatmap_tab(corr_df):
    st.markdown("## Correlation Heatmap")

    fig = make_correlation_heatmap(
        corr_df=corr_df,
        title="Correlation Heatmap - Daily Returns",
    )

    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("Unable to generate heatmap.")


def _render_rankings_tab(corr_pairs_df, loaded_assets):
    st.markdown("## Top Correlations")

    if corr_pairs_df is None or corr_pairs_df.empty:
        st.warning("Not enough correlation pairs.")
        return

    corr_pairs_df = corr_pairs_df.dropna(subset=["correlation"]).copy()
    if corr_pairs_df.empty:
        st.warning("No pair has enough valid observations for a correlation.")
        return

    positive_df = corr_pairs_df.sort_values(
        "correlation",
        ascending=False,
    ).head(15)

    negative_df = corr_pairs_df.sort_values(
        "correlation",
        ascending=True,
    ).head(15)

    cpos, cneg = st.columns(2)

    with cpos:
        st.markdown("### Top Positive")
        st.dataframe(
            positive_df.round(4),
            width="stretch",
        )

    with cneg:
        st.markdown("### Top Negative")
        st.dataframe(
            negative_df.round(4),
            width="stretch",
        )

    focus_asset = st.selectbox(
        "Ranking against asset",
        loaded_assets,
    )

    focus_rows = corr_pairs_df[
        (corr_pairs_df["asset_a"] == focus_asset)
        | (corr_pairs_df["asset_b"] == focus_asset)
    ].copy()

    if not focus_rows.empty:
        focus_rows["other_asset"] = np.where(
            focus_rows["asset_a"] == focus_asset,
            focus_rows["asset_b"],
            focus_rows["asset_a"],
        )

        focus_rows = focus_rows[
            [
                "other_asset",
                "correlation",
                "common_observations",
                "coverage_pct",
                "confidence",
            ]
        ].sort_values(
            "correlation",
            ascending=False,
        )

        st.markdown(f"### Correlations against {focus_asset}")
        st.dataframe(
            focus_rows.round(4),
            width="stretch",
        )


def _render_pair_tab(returns_df, corr_pairs_df, loaded_assets, correlation_window):
    st.markdown("## Pair Analysis")

    available_assets = [
        asset for asset in loaded_assets
        if asset in returns_df.columns
    ]

    if len(available_assets) < 2:
        st.warning("Not enough assets with valid returns for pair analysis.")
        return

    pc1, pc2 = st.columns(2)

    with pc1:
        asset_x = st.selectbox(
            "Asset X",
            available_assets,
            index=0,
        )

    with pc2:
        default_y_index = 1 if len(available_assets) > 1 else 0
        asset_y = st.selectbox(
            "Asset Y",
            available_assets,
            index=default_y_index,
        )

    pair_view = st.radio(
        "Pair View",
        [
            "Rolling Correlation",
            "Returns Scatter",
        ],
        horizontal=True,
    )

    if asset_x == asset_y:
        st.warning("Choose two different assets.")
        return

    _render_pair_quality(corr_pairs_df, asset_x, asset_y)

    if pair_view == "Rolling Correlation":
        _render_rolling_correlation(returns_df, asset_x, asset_y, correlation_window)

    elif pair_view == "Returns Scatter":
        _render_returns_scatter(returns_df, asset_x, asset_y)


def _render_pair_quality(corr_pairs_df, asset_x, asset_y):
    if corr_pairs_df is None or corr_pairs_df.empty:
        return

    pair = corr_pairs_df[
        ((corr_pairs_df["asset_a"] == asset_x) & (corr_pairs_df["asset_b"] == asset_y))
        | ((corr_pairs_df["asset_a"] == asset_y) & (corr_pairs_df["asset_b"] == asset_x))
    ]
    if pair.empty:
        return

    stats = pair.iloc[0]
    common_start = stats["common_start_date"]
    common_end = stats["common_end_date"]
    with st.container(horizontal=True):
        st.metric("Common Observations", f"{int(stats['common_observations']):,}", border=True)
        st.metric("Coverage", f"{stats['coverage_pct']:.2f}%", border=True)
        st.metric("Confidence", stats["confidence"].title(), border=True)
        st.metric(
            "Common Period",
            f"{str(common_start)[:4]} to {str(common_end)[:4]}",
            border=True,
        )

    st.caption(f"Aligned return dates: {common_start} to {common_end}.")

    if stats["potential_bias"]:
        st.warning(
            "This pair has limited aligned observations or coverage. "
            "Treat the reported correlation as low-confidence."
        )
    elif pd.notna(stats["correlation_ci95_low"]):
        st.caption(
            f"Full-period correlation {stats['correlation']:.4f}; "
            f"95% CI [{stats['correlation_ci95_low']:.4f}, "
            f"{stats['correlation_ci95_high']:.4f}]."
        )


def _render_rolling_correlation(returns_df, asset_x, asset_y, correlation_window):
    rolling_df = calculate_rolling_correlation(
        returns_df=returns_df,
        asset_x=asset_x,
        asset_y=asset_y,
        window=correlation_window,
    )

    fig = make_rolling_correlation_chart(
        rolling_df=rolling_df,
        asset_x=asset_x,
        asset_y=asset_y,
        window=correlation_window,
    )

    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("Unable to generate rolling correlation.")


def _render_returns_scatter(returns_df, asset_x, asset_y):
    scatter_df = build_scatter_returns_frame(
        returns_df=returns_df,
        asset_x=asset_x,
        asset_y=asset_y,
    )

    fig = make_returns_scatter_chart(
        scatter_df=scatter_df,
        asset_x=asset_x,
        asset_y=asset_y,
    )

    if fig is None and scatter_df is not None and not scatter_df.empty:
        fig = _make_returns_scatter_fallback(scatter_df, asset_x, asset_y)

    if fig is not None:
        st.plotly_chart(fig, width="stretch")

        st.markdown("### Scatter Data Preview")
        st.dataframe(
            scatter_df.tail(50),
            width="stretch",
        )
    else:
        st.warning("Unable to generate returns scatter plot.")


def _make_returns_scatter_fallback(scatter_df, asset_x, asset_y):
    x_col = f"{asset_x}_return_pct"
    y_col = f"{asset_y}_return_pct"

    if x_col not in scatter_df.columns or y_col not in scatter_df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=scatter_df[x_col],
            y=scatter_df[y_col],
            mode="markers",
            name=f"{asset_x} vs {asset_y}",
            text=scatter_df["snapped_at"].dt.strftime("%Y-%m-%d")
            if "snapped_at" in scatter_df.columns
            else None,
            marker=dict(
                size=6,
                opacity=0.55,
            ),
            hovertemplate=(
                "Date: %{text}<br>"
                f"{asset_x}: " + "%{x:.2f}%<br>"
                f"{asset_y}: " + "%{y:.2f}%<extra></extra>"
            ),
        )
    )

    fig.add_hline(y=0, line_dash="dot", opacity=0.45)
    fig.add_vline(x=0, line_dash="dot", opacity=0.45)

    fig.update_layout(
        title=f"Returns Scatter - {asset_x} vs {asset_y}",
        template="plotly_dark",
        height=620,
        xaxis_title=f"{asset_x} Daily Return %",
        yaxis_title=f"{asset_y} Daily Return %",
        hovermode="closest",
    )

    return fig


def _render_base100_tab(price_df, loaded_assets):
    st.markdown("## Multi-Asset Performance - Base 100")

    norm_df = normalize_base_100(price_df)

    fig = make_base100_multi_asset_chart(
        norm_df=norm_df,
        selected_assets=loaded_assets,
        title="Multi-Asset Performance - Base 100",
    )

    if fig is not None:
        st.plotly_chart(fig, width="stretch")
    else:
        st.warning("Unable to generate Base 100 chart.")


def _render_data_tab(price_df, returns_df, corr_df, corr_pairs_df):
    st.markdown("## Data")

    data_view = st.radio(
        "Table",
        [
            "Prices",
            "Returns",
            "Correlation Matrix",
            "Pair Coverage",
        ],
        horizontal=True,
    )

    if data_view == "Prices":
        st.dataframe(
            price_df.tail(100),
            width="stretch",
        )

    elif data_view == "Returns":
        st.dataframe(
            returns_df.tail(100),
            width="stretch",
        )

    elif data_view == "Correlation Matrix":
        st.dataframe(
            corr_df.round(4),
            width="stretch",
        )

    elif data_view == "Pair Coverage":
        st.dataframe(
            corr_pairs_df,
            hide_index=True,
            width="stretch",
            column_config={
                "coverage_ratio": st.column_config.ProgressColumn(
                    "Coverage Ratio",
                    min_value=0.0,
                    max_value=1.0,
                    format="percent",
                ),
                "correlation": st.column_config.NumberColumn(format="%.4f"),
                "correlation_ci95_low": st.column_config.NumberColumn(format="%.4f"),
                "correlation_ci95_high": st.column_config.NumberColumn(format="%.4f"),
            },
        )
