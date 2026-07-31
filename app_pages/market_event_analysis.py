from dataclasses import dataclass
from datetime import date
from typing import Callable

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


CROSS_ASSET_RETURN_COLUMNS = [
    "Return +1D %",
    "Return +7D %",
    "Return +30D %",
    "Return +90D %",
    "Return +180D %",
    "Return +365D %",
]


@dataclass(frozen=True)
class MarketEventAnalysisDeps:
    render_date_range_selector: Callable
    assets_config: dict
    load_asset_events: Callable
    load_asset_data: Callable
    calculate_cross_asset_event_impact: Callable
    build_event_impact_matrix: Callable
    make_event_impact_heatmap: Callable
    calculate_event_category_asset_summary: Callable
    make_event_category_heatmap: Callable
    calculate_risk_on_off_snapshot: Callable
    calculate_event_recovery_analysis: Callable
    dataframe_to_csv_bytes: Callable


def render_market_event_analysis(deps: MarketEventAnalysisDeps):
    st.title("Market Event Analysis")

    st.markdown(
        """
        Cross-asset event study that measures how different markets reacted after historical events.
        This module compares risk assets, defensive assets and macro-sensitive instruments.
        """
    )

    selected_assets, start_date, end_date = _render_asset_date_controls(deps)
    (
        event_source,
        horizon_mode,
        selected_horizon,
        custom_horizon_days,
        max_events,
        include_approximate,
    ) = _render_event_controls()

    st.markdown("---")

    if not selected_assets:
        st.warning("Select at least one asset.")
        return

    try:
        events_df = _load_filtered_events(
            deps=deps,
            event_source=event_source,
            start_date=start_date,
            end_date=end_date,
            max_events=max_events,
            include_approximate=include_approximate,
        )
    except Exception as exc:
        st.error(f"Event data is unavailable: {exc}")
        st.caption("Check that MySQL/XAMPP is running and that the configured event tables exist.")
        return

    if events_df.empty:
        st.info("No events available for the selected filters.")
        return

    if horizon_mode == "Preset":
        analysis_horizons = (1, 7, 30, 90, 180, 365)
    else:
        analysis_horizons = tuple(
            sorted(
                set([1, 7, 30, 90, 180, 365, int(custom_horizon_days)])
            )
        )

    cross_asset_df, load_report = deps.calculate_cross_asset_event_impact(
        events_df=events_df,
        asset_keys=selected_assets,
        start_date=start_date,
        end_date=end_date,
        horizons=analysis_horizons,
        assets_config=deps.assets_config,
        load_asset_data_func=deps.load_asset_data,
        include_approximate=include_approximate,
        return_load_report=True,
    )

    if cross_asset_df.empty:
        st.info("No cross-asset event impact data available.")
        return

    _render_load_report(load_report)
    _render_summary(cross_asset_df, selected_horizon)
    _render_tabs(
        deps,
        cross_asset_df,
        selected_horizon,
        selected_assets,
    )


def _render_asset_date_controls(deps: MarketEventAnalysisDeps):
    default_assets = [
        asset for asset in [
            "SP500",
            "NASDAQ100",
            "DOWJONES",
            "STOXX600",
            "FTSE100",
            "GOLD",
            "DXY",
            "VIX",
            "US10Y",
            "WTI_OIL",
            "BRENT_OIL",
            "BTC",
        ]
        if asset in deps.assets_config
    ]

    c1, c2 = st.columns([2, 2])

    with c1:
        selected_assets = st.multiselect(
            "Assets",
            options=list(deps.assets_config.keys()),
            default=default_assets,
            format_func=lambda key: f"{key} - {deps.assets_config[key].get('display_name', key)}",
        )

    with c2:
        start_date, end_date = deps.render_date_range_selector(
            default_start=date(2020, 1, 1),
            default_end=date.today(),
        )

    return selected_assets, start_date, end_date


def _render_event_controls():
    c3, c4, c5 = st.columns([2, 2, 2])

    with c3:
        event_source = st.selectbox(
            "Event Source",
            [
                "All Events",
                "BTC Events",
                "World Events",
            ],
            index=0,
        )

    with c4:
        horizon_mode = st.selectbox(
            "Return Horizon",
            [
                "Preset",
                "Custom",
            ],
            index=0,
        )

        if horizon_mode == "Preset":
            selected_horizon = st.selectbox(
                "Preset Horizon",
                CROSS_ASSET_RETURN_COLUMNS,
                index=2,
            )

            custom_horizon_days = None
        else:
            custom_horizon_days = st.number_input(
                "Custom Horizon Days",
                min_value=1,
                max_value=3650,
                value=45,
                step=1,
            )

            selected_horizon = f"Return +{int(custom_horizon_days)}D %"

    with c5:
        max_events = st.slider(
            "Max Events",
            min_value=5,
            max_value=80,
            value=30,
            step=5,
        )

        include_approximate = st.checkbox(
            "Include approximate year-only events",
            value=False,
        )

    return (
        event_source,
        horizon_mode,
        selected_horizon,
        custom_horizon_days,
        max_events,
        include_approximate,
    )


def _load_filtered_events(
    deps: MarketEventAnalysisDeps,
    event_source,
    start_date,
    end_date,
    max_events,
    include_approximate,
):
    events_df = deps.load_asset_events(
        start_date=start_date,
        end_date=end_date,
    )

    if event_source == "World Events":
        events_df = events_df[
            events_df["event_source_table"] == "world_historical_events"
        ].copy()
    elif event_source == "BTC Events":
        events_df = events_df[
            events_df["event_source_table"] == "bitcoin_historical_events"
        ].copy()

    if not include_approximate and "date_precision" in events_df.columns:
        events_df = events_df[events_df["date_precision"].eq("exact")].copy()

    return events_df.sort_values("event_date").tail(max_events).reset_index(drop=True)


def _render_summary(cross_asset_df, selected_horizon):
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.metric("Events", cross_asset_df["Event"].nunique())

    with k2:
        st.metric("Assets", cross_asset_df["Asset"].nunique())

    with k3:
        if selected_horizon in cross_asset_df.columns:
            avg_return = pd.to_numeric(cross_asset_df[selected_horizon], errors="coerce").mean()
        else:
            avg_return = np.nan

        st.metric(
            f"Average {selected_horizon}",
            f"{avg_return:,.2f}%" if pd.notna(avg_return) else "-",
        )

    with k4:
        if selected_horizon in cross_asset_df.columns:
            observations = pd.to_numeric(cross_asset_df[selected_horizon], errors="coerce").notna().sum()
        else:
            observations = 0

        st.metric("Valid Observations", int(observations))

    st.caption(
        "Returns are calculated from the first available market date on or after each event date. "
        "Custom horizons allow manual event-window testing. "
        "The analysis is event-driven and does not predict future returns."
    )


def _render_tabs(
    deps: MarketEventAnalysisDeps,
    cross_asset_df,
    selected_horizon,
    selected_assets,
):
    tab_matrix, tab_category, tab_risk, tab_detail, tab_data = st.tabs(
        [
            "Event Impact Matrix",
            "Category Summary",
            "Risk-On / Risk-Off",
            "Event Detail & Recovery",
            "Data",
        ],
        on_change="rerun",
    )

    if tab_matrix.open:
        with tab_matrix:
            _render_matrix_tab(deps, cross_asset_df, selected_horizon)

    if tab_category.open:
        with tab_category:
            _render_category_tab(deps, cross_asset_df, selected_horizon)

    if tab_risk.open:
        with tab_risk:
            _render_risk_tab(deps, cross_asset_df, selected_horizon)

    if tab_detail.open:
        with tab_detail:
            _render_event_detail_tab(
                deps,
                cross_asset_df,
                selected_horizon,
                selected_assets,
            )

    if tab_data.open:
        with tab_data:
            _render_data_tab(deps, cross_asset_df)


def _render_load_report(load_report):
    if load_report is None or load_report.empty:
        return

    with st.container(horizontal=True):
        st.metric("Assets Requested", len(load_report), border=True)
        st.metric("Assets Loaded", int(load_report["status"].eq("loaded").sum()), border=True)
        st.metric("Assets Not Loaded", int(load_report["status"].ne("loaded").sum()), border=True)

    failures = load_report[load_report["status"] != "loaded"]
    if not failures.empty:
        st.dataframe(failures, hide_index=True, width="stretch")


def _render_matrix_tab(deps: MarketEventAnalysisDeps, cross_asset_df, selected_horizon):
    matrix_df = deps.build_event_impact_matrix(
        cross_asset_df=cross_asset_df,
        return_col=selected_horizon,
    )

    heatmap_fig = deps.make_event_impact_heatmap(
        matrix_df=matrix_df,
        title=f"Cross-Asset Event Impact Matrix - {selected_horizon}",
    )

    if heatmap_fig is not None:
        st.plotly_chart(heatmap_fig, width="stretch")

    st.markdown("### Matrix Data")
    st.dataframe(matrix_df, width="stretch")


def _render_category_tab(deps: MarketEventAnalysisDeps, cross_asset_df, selected_horizon):
    category_summary_df = deps.calculate_event_category_asset_summary(
        cross_asset_df=cross_asset_df,
        return_col=selected_horizon,
    )

    category_fig = deps.make_event_category_heatmap(category_summary_df)

    if category_fig is not None:
        st.plotly_chart(category_fig, width="stretch")

    st.markdown("### Category / Asset Summary")
    st.dataframe(category_summary_df, width="stretch")


def _render_risk_tab(deps: MarketEventAnalysisDeps, cross_asset_df, selected_horizon):
    risk_df = deps.calculate_risk_on_off_snapshot(
        cross_asset_df=cross_asset_df,
        return_col=selected_horizon,
    )

    st.markdown("### Risk-On / Risk-Off Event Read")
    st.caption(
        "Risk assets include equity indices and BTC when selected. "
        "Defensive/macro assets include GOLD, DXY, US10Y and VIX when selected."
    )

    st.dataframe(risk_df, width="stretch")


def _render_event_detail_tab(
    deps: MarketEventAnalysisDeps,
    cross_asset_df,
    selected_horizon,
    selected_assets,
):
    labels = cross_asset_df["Event Label"].dropna().drop_duplicates().tolist()
    if not labels:
        st.info("No event detail is available.")
        return

    selected_label = st.selectbox("Event", labels, key="event_detail_label")
    event_rows = cross_asset_df[cross_asset_df["Event Label"] == selected_label].copy()
    if event_rows.empty:
        return

    event_info = event_rows.iloc[0]
    precision = event_info.get("Date Precision", "exact")
    precision_label = "Exact event date" if precision == "exact" else "Approximate year-only date"

    with st.container(horizontal=True):
        st.metric("Date", str(event_info.get("Event Date")), border=True)
        st.metric("Date Precision", precision_label, border=True)
        st.metric("Assets with Results", int(event_rows[selected_horizon].notna().sum()), border=True)

    description = str(event_info.get("Description", "")).strip()
    if description:
        st.caption(description)

    values = pd.to_numeric(event_rows[selected_horizon], errors="coerce")
    chart_data = event_rows.assign(_event_return=values).dropna(subset=["_event_return"])

    if not chart_data.empty:
        best = chart_data.sort_values("_event_return", ascending=False).iloc[0]
        worst = chart_data.sort_values("_event_return", ascending=True).iloc[0]

        with st.container(horizontal=True):
            st.metric("Best Asset", best["Asset"], f"{best['_event_return']:.2f}%", border=True)
            st.metric("Worst Asset", worst["Asset"], f"{worst['_event_return']:.2f}%", border=True)

        figure = go.Figure(
            go.Bar(
                x=chart_data["Asset"],
                y=chart_data["_event_return"],
                marker_color=np.where(chart_data["_event_return"] >= 0, "#2E8B57", "#C44536"),
                hovertemplate="%{x}: %{y:.2f}%<extra></extra>",
            )
        )
        figure.add_hline(y=0, line_dash="dot", opacity=0.5)
        figure.update_layout(
            title=f"Asset Reaction - {selected_horizon}",
            template="plotly_dark",
            height=480,
            xaxis_title="Asset",
            yaxis_title="Return (%)",
        )
        st.plotly_chart(figure, width="stretch")

    st.dataframe(event_rows, hide_index=True, width="stretch")

    if precision != "exact":
        st.warning("Recovery analysis is disabled because this event has only year-level date precision.")
        return

    recovery_window = st.slider(
        "Recovery Window (calendar days)",
        min_value=30,
        max_value=1095,
        value=365,
        step=30,
    )
    event_payload = {
        "event_date": event_info.get("Event Date"),
        "date_precision": precision,
    }
    recovery_df, recovery_report = deps.calculate_event_recovery_analysis(
        event=event_payload,
        asset_keys=selected_assets,
        assets_config=deps.assets_config,
        load_asset_data_func=deps.load_asset_data,
        horizon_days=recovery_window,
    )

    st.markdown("### Recovery Analysis")
    if recovery_df.empty:
        st.info("No recovery observations are available for this event.")
    else:
        st.dataframe(recovery_df, hide_index=True, width="stretch")

    if recovery_report is not None and not recovery_report.empty:
        failures = recovery_report[recovery_report["status"] != "loaded"]
        if not failures.empty:
            st.dataframe(failures, hide_index=True, width="stretch")


def _render_data_tab(deps: MarketEventAnalysisDeps, cross_asset_df):
    st.markdown("### Full Cross-Asset Event Impact Table")
    st.dataframe(cross_asset_df, width="stretch")

    csv_data = deps.dataframe_to_csv_bytes(cross_asset_df)

    if csv_data is not None:
        st.download_button(
            label="Download cross-asset event impact CSV",
            data=csv_data,
            file_name="cross_asset_event_impact_analysis.csv",
            mime="text/csv",
            width="stretch",
        )
