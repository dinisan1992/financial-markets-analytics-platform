from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd
import streamlit as st

from asset_config import ASSETS
from dashboard.asset_charts import (
    make_asset_line_chart,
    make_drawdown_chart,
    make_price_chart,
    make_returns_boxplot,
    make_suspicious_events_bar_chart,
    make_volume_price_scatter,
    make_volume_zscore_chart,
    make_volatility_chart,
)
from dashboard.asset_indicators import (
    calculate_asset_kpis,
    get_suspicious_events,
    prepare_asset_technical_data,
)


@dataclass(frozen=True)
class AssetExplorerDeps:
    render_date_range_selector: Callable
    date_to_str: Callable
    load_asset_data: Callable
    load_asset_events: Callable
    filter_events_for_chart: Callable
    render_asset_kpi_cards: Callable
    render_technical_signal_summary: Callable
    render_event_impact_tab: Callable
    render_btc_halving_cycle_analysis: Callable
    filter_df_by_recent_window: Callable
    render_suspicion_score: Callable
    render_suspicious_events_table: Callable
    render_return_distribution_summary: Callable
    calculate_event_forward_returns: Callable
    calculate_btc_auto_detected_cycles: Callable
    calculate_btc_validated_swing_cycles: Callable
    calculate_btc_halving_impact_from_events: Callable
    dataframe_to_csv_bytes: Callable


def render_asset_explorer(deps: AssetExplorerDeps):
    st.title("Asset Explorer")

    st.markdown(
        """
        Individual asset analysis with an integrated technical dashboard,
        risk signals, statistical views and calculated data.
        """
    )

    selected_asset, start_date, end_date, load_asset_button = _render_top_controls(deps)
    chart_mode, chart_size, event_filter = _render_chart_controls()

    if load_asset_button:
        _load_selected_asset(
            deps=deps,
            selected_asset=selected_asset,
            start_date=start_date,
            end_date=end_date,
        )

    if st.session_state.asset_loaded and st.session_state.asset_tech_df is not None:
        _render_loaded_asset(
            deps=deps,
            chart_mode=chart_mode,
            chart_size=chart_size,
            event_filter=event_filter,
        )
    else:
        st.info("Select an asset and click Load Asset to start the analysis.")


def _render_top_controls(deps: AssetExplorerDeps):
    asset_keys = list(ASSETS.keys())
    top_col1, top_col2, top_col3 = st.columns([2, 2, 1])

    with top_col1:
        selected_asset = st.selectbox(
            "Asset",
            asset_keys,
            format_func=lambda key: f"{key} - {ASSETS[key]['display_name']}",
        )

    with top_col2:
        start_date, end_date = deps.render_date_range_selector(
            default_start=date(2020, 1, 1),
            default_end=date.today(),
        )

    with top_col3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        load_asset_button = st.button("Load Asset", width="stretch")

    return selected_asset, start_date, end_date, load_asset_button


def _render_chart_controls():
    c1, c2, c3 = st.columns([1, 1, 1])

    with c1:
        chart_mode = st.selectbox(
            "Main Chart Type",
            ["Candlestick", "Line Chart"],
        )

    with c2:
        chart_size = st.selectbox(
            "Main Chart Size",
            ["Compact", "Normal", "Large"],
            index=1,
        )

    with c3:
        event_filter = st.selectbox(
            "Events",
            [
                "All",
                "BTC Events",
                "World Events",
                "Hide Events",
            ],
        )

    return chart_mode, chart_size, event_filter


def _load_selected_asset(deps: AssetExplorerDeps, selected_asset, start_date, end_date):
    try:
        with st.spinner("Loading asset and calculating indicators..."):
            raw_df = deps.load_asset_data(
                asset_key=selected_asset,
                start_date=deps.date_to_str(start_date),
                end_date=deps.date_to_str(end_date),
            )

            asset_cfg = ASSETS[selected_asset]
            tech_df = prepare_asset_technical_data(
                raw_df,
                asset_cfg=asset_cfg,
            )

            events_df = deps.load_asset_events(
                start_date=deps.date_to_str(start_date),
                end_date=deps.date_to_str(end_date),
            )

        display_name = asset_cfg["display_name"]

        st.session_state.asset_loaded = True
        st.session_state.asset_key = selected_asset
        st.session_state.asset_display_name = display_name
        st.session_state.asset_tech_df = tech_df
        st.session_state.asset_events_df = events_df

        st.success("Asset loaded successfully.")

    except Exception as exc:
        st.session_state.asset_loaded = False
        st.session_state.asset_tech_df = None
        st.session_state.asset_events_df = None
        st.error(f"Error loading asset: {exc}")


def _render_loaded_asset(deps: AssetExplorerDeps, chart_mode, chart_size, event_filter):
    tech_df = st.session_state.asset_tech_df
    display_name = st.session_state.asset_display_name
    selected_asset_loaded = st.session_state.asset_key

    st.subheader(f"{selected_asset_loaded} - {display_name}")

    kpis = calculate_asset_kpis(tech_df)
    deps.render_asset_kpi_cards(kpis)

    st.markdown("---")

    events_for_chart = deps.filter_events_for_chart(
        events_df=st.session_state.asset_events_df,
        event_filter=event_filter,
    )

    if selected_asset_loaded == "BTC":
        tab_technical, tab_event_impact, tab_btc_cycle, tab_risk, tab_stats, tab_data = st.tabs(
            [
                "Technical Dashboard",
                "Event Impact",
                "BTC Cycle Analysis",
                "Risk Signals",
                "Statistics",
                "Data",
            ],
            on_change="rerun",
        )
    else:
        tab_technical, tab_event_impact, tab_risk, tab_stats, tab_data = st.tabs(
            [
                "Technical Dashboard",
                "Event Impact",
                "Risk Signals",
                "Statistics",
                "Data",
            ],
            on_change="rerun",
        )

    if tab_technical.open:
        with tab_technical:
            _render_technical_tab(
                deps=deps,
                tech_df=tech_df,
                display_name=display_name,
                chart_mode=chart_mode,
                chart_size=chart_size,
                events_for_chart=events_for_chart,
            )

    if tab_event_impact.open:
        with tab_event_impact:
            deps.render_event_impact_tab(
                events_for_chart=events_for_chart,
                tech_df=tech_df,
            )

    if selected_asset_loaded == "BTC" and tab_btc_cycle.open:
        with tab_btc_cycle:
            deps.render_btc_halving_cycle_analysis(
                price_df=tech_df,
                events_df=st.session_state.asset_events_df,
            )

    if tab_risk.open:
        with tab_risk:
            _render_risk_tab(deps, tech_df, display_name)

    if tab_stats.open:
        with tab_stats:
            _render_stats_tab(deps, tech_df, display_name)

    if tab_data.open:
        with tab_data:
            _render_data_tab(
                deps=deps,
                tech_df=tech_df,
                events_for_chart=events_for_chart,
                selected_asset_loaded=selected_asset_loaded,
            )


def _render_technical_tab(
    deps: AssetExplorerDeps,
    tech_df,
    display_name,
    chart_mode,
    chart_size,
    events_for_chart,
):
    chart_height_map = {
        "Compact": 650,
        "Normal": 850,
        "Large": 1050,
    }

    st.markdown("## Technical Dashboard")

    deps.render_technical_signal_summary(tech_df, asset_label=display_name)

    st.markdown("---")
    st.markdown("### Price Action")

    if chart_mode == "Candlestick":
        price_fig = make_price_chart(
            df=tech_df,
            display_name=display_name,
            show_emas=True,
            show_bollinger=True,
            show_flags=True,
            selected_emas=[9, 20, 50, 100, 200],
            chart_height=chart_height_map[chart_size],
            show_volume=True,
            show_rsi=True,
            show_stoch_rsi=True,
            show_macd=True,
            events=events_for_chart,
        )
    else:
        price_fig = make_asset_line_chart(
            df=tech_df,
            display_name=display_name,
        )

    if price_fig is not None:
        st.plotly_chart(price_fig, width="stretch")
    else:
        st.warning("Unable to generate the main chart.")


def _render_risk_tab(deps: AssetExplorerDeps, tech_df, display_name):
    st.markdown("## Risk & Suspicious Signals")

    risk_window = st.radio(
        "Recent Risk Window",
        [
            "Last 7D",
            "Last 30D",
            "Last 90D",
            "Full Period",
        ],
        index=1,
        horizontal=True,
    )

    risk_df = deps.filter_df_by_recent_window(
        df=tech_df,
        window_label=risk_window,
    )

    deps.render_suspicion_score(
        df=risk_df,
        window_label=risk_window,
    )

    st.markdown("---")

    total_suspicious = int(risk_df["suspicious_event"].sum()) if "suspicious_event" in risk_df.columns else 0
    volume_spikes = int(risk_df["volume_spike"].sum()) if "volume_spike" in risk_df.columns else 0
    pump_dump = int(risk_df["possible_pump_dump"].sum()) if "possible_pump_dump" in risk_df.columns else 0
    candle_rejection = int(risk_df["high_volume_candle_rejection"].sum()) if "high_volume_candle_rejection" in risk_df.columns else 0
    extreme_rsi = int(risk_df["extreme_rsi"].sum()) if "extreme_rsi" in risk_df.columns else 0

    r1, r2, r3, r4, r5 = st.columns(5)

    with r1:
        st.metric("Suspicious Events", total_suspicious)

    with r2:
        st.metric("Volume Spikes", volume_spikes)

    with r3:
        st.metric("Pump/Dump", pump_dump)

    with r4:
        st.metric("Candle Rejection", candle_rejection)

    with r5:
        st.metric("Extreme RSI", extreme_rsi)

    st.markdown("---")

    risk_view = st.radio(
        "Risk View",
        [
            "Event Counts",
            "Volume Z-Score",
            "Suspicious Table",
            "Top Suspicious Events",
        ],
        horizontal=True,
    )

    if risk_view == "Event Counts":
        event_fig = make_suspicious_events_bar_chart(
            df=risk_df,
            display_name=display_name,
        )
        st.plotly_chart(event_fig, width="stretch")

    elif risk_view == "Volume Z-Score":
        zscore_fig = make_volume_zscore_chart(
            df=risk_df,
            display_name=display_name,
        )

        if zscore_fig is not None:
            st.plotly_chart(zscore_fig, width="stretch")
        else:
            st.info("Volume Z-Score unavailable for this asset.")

    elif risk_view == "Suspicious Table":
        _render_suspicious_table_view(deps, risk_df)

    elif risk_view == "Top Suspicious Events":
        suspicious_df = get_suspicious_events(risk_df)

        if suspicious_df.empty:
            st.info("No suspicious events in the selected risk window.")
        else:
            sort_col = "volume_zscore" if "volume_zscore" in suspicious_df.columns else None

            if sort_col:
                suspicious_df = suspicious_df.sort_values(
                    sort_col,
                    ascending=False,
                )

            st.dataframe(
                suspicious_df.head(20),
                width="stretch",
            )


def _render_suspicious_table_view(deps: AssetExplorerDeps, risk_df):
    event_type_filter = st.selectbox(
        "Filter by Event Type",
        [
            "All",
            "Volume Spike",
            "Possible Pump/Dump",
            "High-Volume Candle Rejection",
            "Extreme RSI",
        ],
    )

    filtered_df = risk_df.copy()

    if event_type_filter == "Volume Spike" and "volume_spike" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["volume_spike"]]

    elif event_type_filter == "Possible Pump/Dump" and "possible_pump_dump" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["possible_pump_dump"]]

    elif event_type_filter == "High-Volume Candle Rejection" and "high_volume_candle_rejection" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["high_volume_candle_rejection"]]

    elif event_type_filter == "Extreme RSI" and "extreme_rsi" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["extreme_rsi"]]

    if event_type_filter == "All":
        deps.render_suspicious_events_table(risk_df)
    else:
        if filtered_df.empty:
            st.info("No events for the selected filter.")
        else:
            st.dataframe(
                filtered_df.tail(100),
                width="stretch",
            )


def _render_stats_tab(deps: AssetExplorerDeps, tech_df, display_name):
    st.markdown("## Statistical Views")

    deps.render_return_distribution_summary(tech_df)

    st.markdown("---")

    stat_view = st.radio(
        "Statistics View",
        [
            "Scatter",
            "Box Plot",
            "Drawdown",
            "Rolling Volatility",
        ],
        horizontal=True,
    )

    if stat_view == "Scatter":
        scatter_fig = make_volume_price_scatter(
            df=tech_df,
            display_name=display_name,
        )

        if scatter_fig is not None:
            st.plotly_chart(scatter_fig, width="stretch")
        else:
            st.warning("Not enough volume data to generate the scatter plot.")

    elif stat_view == "Box Plot":
        box_fig = make_returns_boxplot(
            df=tech_df,
            display_name=display_name,
        )

        if box_fig is not None:
            st.plotly_chart(box_fig, width="stretch")
        else:
            st.warning("Box Plot unavailable. Check whether the daily_return_pct column exists.")

    elif stat_view == "Drawdown":
        drawdown_fig = make_drawdown_chart(
            df=tech_df,
            display_name=display_name,
        )

        if drawdown_fig is not None:
            st.plotly_chart(drawdown_fig, width="stretch")
        else:
            st.warning("Drawdown unavailable. Check whether the drawdown_pct column exists.")

    elif stat_view == "Rolling Volatility":
        volatility_fig = make_volatility_chart(
            df=tech_df,
            display_name=display_name,
        )

        if volatility_fig is not None:
            st.plotly_chart(volatility_fig, width="stretch")
        else:
            st.warning("Rolling volatility unavailable. Check whether the rolling_volatility_30d column exists.")


def _render_data_tab(deps: AssetExplorerDeps, tech_df, events_for_chart, selected_asset_loaded):
    st.markdown("## Data")

    suspicious_df = get_suspicious_events(tech_df)
    event_returns_df = (
        deps.calculate_event_forward_returns(
            events_df=events_for_chart,
            price_df=tech_df,
        )
        if events_for_chart is not None and not events_for_chart.empty
        else pd.DataFrame()
    )

    data_options = [
        "Calculated Data",
        "Suspicious Events",
        "Event Impact Data",
    ]

    if selected_asset_loaded == "BTC":
        data_options.append("BTC Halving Cycle Data")

    data_view = st.radio(
        "Table",
        data_options,
        horizontal=True,
    )

    if data_view == "Calculated Data":
        st.dataframe(
            tech_df.tail(100),
            width="stretch",
        )

    elif data_view == "Suspicious Events":
        if suspicious_df.empty:
            st.info("No suspicious events in the selected period.")
        else:
            st.dataframe(
                suspicious_df,
                width="stretch",
            )

    elif data_view == "Event Impact Data":
        if event_returns_df.empty:
            st.info("No event impact data available for the selected period.")
        else:
            st.dataframe(
                event_returns_df,
                width="stretch",
            )

    elif data_view == "BTC Halving Cycle Data":
        _render_btc_cycle_data_view(
            deps=deps,
            tech_df=tech_df,
        )

    _render_downloads(
        deps=deps,
        tech_df=tech_df,
        suspicious_df=suspicious_df,
        event_returns_df=event_returns_df,
        selected_asset_loaded=selected_asset_loaded,
    )


def _render_btc_cycle_data_view(deps: AssetExplorerDeps, tech_df):
    btc_data_view = st.radio(
        "BTC Cycle Data View",
        [
            "Auto-Detected Cycles",
            "Historical Benchmark",
            "Halving Impact",
        ],
        horizontal=True,
    )

    if btc_data_view == "Auto-Detected Cycles":
        btc_cycle_df = deps.calculate_btc_auto_detected_cycles(
            price_df=tech_df,
            events_df=st.session_state.asset_events_df,
        )
    elif btc_data_view == "Historical Benchmark":
        btc_cycle_df = deps.calculate_btc_validated_swing_cycles(
            price_df=tech_df,
            events_df=st.session_state.asset_events_df,
        )
    else:
        btc_cycle_df = deps.calculate_btc_halving_impact_from_events(
            price_df=tech_df,
            events_df=st.session_state.asset_events_df,
        )

    if btc_cycle_df.empty:
        st.info("No BTC cycle data available.")
    else:
        st.dataframe(
            btc_cycle_df,
            width="stretch",
        )


def _render_downloads(
    deps: AssetExplorerDeps,
    tech_df,
    suspicious_df,
    event_returns_df,
    selected_asset_loaded,
):
    st.markdown("---")
    st.markdown("### Downloads")

    d1, d2, d3 = st.columns(3)

    with d1:
        calculated_csv = deps.dataframe_to_csv_bytes(tech_df)

        if calculated_csv is not None:
            st.download_button(
                label="Download calculated data CSV",
                data=calculated_csv,
                file_name=f"{selected_asset_loaded}_calculated_data.csv",
                mime="text/csv",
                width="stretch",
            )

    with d2:
        suspicious_csv = deps.dataframe_to_csv_bytes(suspicious_df)

        if suspicious_csv is not None:
            st.download_button(
                label="Download suspicious events CSV",
                data=suspicious_csv,
                file_name=f"{selected_asset_loaded}_suspicious_events.csv",
                mime="text/csv",
                width="stretch",
            )
        else:
            st.caption("No suspicious events to download.")

    with d3:
        event_impact_csv = deps.dataframe_to_csv_bytes(event_returns_df)

        if event_impact_csv is not None:
            st.download_button(
                label="Download event impact CSV",
                data=event_impact_csv,
                file_name=f"{selected_asset_loaded}_event_impact.csv",
                mime="text/csv",
                width="stretch",
            )
        else:
            st.caption("No event impact data to download.")
