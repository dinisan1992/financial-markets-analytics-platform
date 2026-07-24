import numpy as np
import pandas as pd
import streamlit as st

from dashboard.btc_cycle_charts import (
    make_btc_halving_forward_returns_chart,
    make_btc_halving_window_extremes_chart,
    make_btc_validated_cycle_performance_chart,
    make_btc_validated_cycle_timing_chart,
)
from services.btc_cycle_service import (
    calculate_btc_auto_detected_cycles,
    calculate_btc_halving_impact_from_events,
    calculate_btc_validated_swing_cycles,
    extract_btc_halving_events,
)
from services.export_service import dataframe_to_csv_bytes


def render_btc_cycle_summary(cycle_df: pd.DataFrame, title: str):
    st.markdown(f"### {title}")

    if cycle_df is None or cycle_df.empty:
        st.info("No BTC cycle data available.")
        return

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Cycles Available", len(cycle_df))

    with c2:
        avg_upside = cycle_df["Upside from Halving %"].dropna().mean() if "Upside from Halving %" in cycle_df.columns else np.nan
        st.metric(
            "Average Upside from Halving",
            f"{avg_upside:,.2f}%" if pd.notna(avg_upside) else "-",
        )

    with c3:
        avg_drawdown = cycle_df["Drawdown from Halving %"].dropna().mean() if "Drawdown from Halving %" in cycle_df.columns else np.nan
        st.metric(
            "Average Drawdown from Halving",
            f"{avg_drawdown:,.2f}%" if pd.notna(avg_drawdown) else "-",
        )

    with c4:
        avg_days_to_top = cycle_df["Days to Top"].dropna().mean() if "Days to Top" in cycle_df.columns else np.nan
        st.metric(
            "Average Days to Top",
            f"{avg_days_to_top:,.0f}" if pd.notna(avg_days_to_top) else "-",
        )


def render_btc_auto_cycle_summary(cycle_df: pd.DataFrame, min_drawdown_pct: float):
    if cycle_df is None or cycle_df.empty:
        st.info("No auto-detected BTC cycle data available.")
        return

    st.markdown("### Auto-Detected BTC Cycle Summary")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Detected Cycles", len(cycle_df))

    with c2:
        avg_drawdown = cycle_df["Drawdown %"].dropna().mean() if "Drawdown %" in cycle_df.columns else np.nan
        st.metric(
            "Average Bear Drawdown",
            f"{avg_drawdown:,.2f}%" if pd.notna(avg_drawdown) else "-",
        )

    with c3:
        avg_upside = cycle_df["Upside %"].dropna().mean() if "Upside %" in cycle_df.columns else np.nan
        st.metric(
            "Average Bull Upside",
            f"{avg_upside:,.2f}%" if pd.notna(avg_upside) else "-",
        )

    with c4:
        avg_days_up = cycle_df["Days Up"].dropna().mean() if "Days Up" in cycle_df.columns else np.nan
        st.metric(
            "Average Days Up",
            f"{avg_days_up:,.0f}" if pd.notna(avg_days_up) else "-",
        )

    st.markdown("#### Detection Method")
    st.info(
        f"The detector identifies macro BTC cycles by tracking all-time highs and confirming a bear phase "
        f"when price falls at least {min_drawdown_pct:,.0f}% from the latest ATH. "
        f"The cycle bottom is the lowest price before recovery to the previous ATH. "
        f"The next bull top is the next detected ATH before another major bear phase, or the latest high for the current cycle."
    )


def render_btc_auto_detected_cycle_analysis(price_df: pd.DataFrame, events_df: pd.DataFrame):
    st.markdown("## BTC Auto-Detected Cycle Analysis")
    st.caption(
        "This view detects BTC macro cycles directly from the price chart. "
        "No cycle top/bottom dates are manually supplied."
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        min_drawdown_pct = st.slider(
            "Major Bear Drawdown Threshold",
            min_value=40,
            max_value=85,
            value=60,
            step=5,
            help="A bear phase is confirmed when BTC falls at least this much from a prior ATH.",
        )

    with c2:
        min_days_after_top = st.slider(
            "Minimum Days After ATH",
            min_value=7,
            max_value=180,
            value=30,
            step=7,
            help="Prevents very short crashes from being treated as macro cycles.",
        )

    with c3:
        recovery_ratio = st.selectbox(
            "Recovery Rule",
            options=[1.0, 0.95, 0.9],
            index=0,
            format_func=lambda value: "New ATH / Full Recovery" if value == 1.0 else f"{value:.0%} of previous ATH",
        )

    cycle_df = calculate_btc_auto_detected_cycles(
        price_df=price_df,
        events_df=events_df,
        min_drawdown_pct=float(min_drawdown_pct),
        recovery_ratio=float(recovery_ratio),
        min_days_after_top=int(min_days_after_top),
    )

    if cycle_df.empty:
        st.info("No BTC macro cycles detected with the selected settings.")
        return

    render_btc_auto_cycle_summary(
        cycle_df=cycle_df,
        min_drawdown_pct=float(min_drawdown_pct),
    )

    st.markdown("---")

    perf_fig = make_btc_validated_cycle_performance_chart(cycle_df)

    if perf_fig is not None:
        perf_fig.update_layout(title="BTC Auto-Detected Cycle Performance")
        st.plotly_chart(perf_fig, width="stretch")

    timing_fig = make_btc_validated_cycle_timing_chart(cycle_df)

    if timing_fig is not None:
        timing_fig.update_layout(title="BTC Auto-Detected Cycle Timing")
        st.plotly_chart(timing_fig, width="stretch")

    st.markdown("---")
    st.markdown("### Full Auto-Detected BTC Cycle Table")
    st.dataframe(cycle_df, width="stretch")

    csv_data = dataframe_to_csv_bytes(cycle_df)

    if csv_data is not None:
        st.download_button(
            label="Download auto-detected BTC cycle data CSV",
            data=csv_data,
            file_name="BTC_auto_detected_cycle_analysis.csv",
            mime="text/csv",
            width="stretch",
        )


def render_btc_validated_cycle_summary(cycle_df: pd.DataFrame):
    if cycle_df is None or cycle_df.empty:
        st.info("No validated BTC cycle data available.")
        return

    closed_df = cycle_df[cycle_df["Status"].isin(["Closed", "Tentative / Current"])].copy()

    st.markdown("### Historical Benchmark Summary")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Cycles", len(cycle_df))

    with c2:
        avg_drawdown = closed_df["Drawdown %"].dropna().mean() if "Drawdown %" in closed_df.columns else np.nan
        st.metric(
            "Average Bear Drawdown",
            f"{avg_drawdown:,.2f}%" if pd.notna(avg_drawdown) else "-",
        )

    with c3:
        avg_upside = closed_df["Upside %"].dropna().mean() if "Upside %" in closed_df.columns else np.nan
        st.metric(
            "Average Bull Upside",
            f"{avg_upside:,.2f}%" if pd.notna(avg_upside) else "-",
        )

    with c4:
        avg_days_up = closed_df["Days Up"].dropna().mean() if "Days Up" in closed_df.columns else np.nan
        st.metric(
            "Average Days Up",
            f"{avg_days_up:,.0f}" if pd.notna(avg_days_up) else "-",
        )

    st.markdown("#### Cycle Interpretation")

    st.info(
        "This benchmark uses historically validated BTC swing anchors: cycle top -> bear-market bottom -> next cycle top. "
        "It is kept as a reference layer to validate the automatic detector. "
        "The current 2025 cycle is marked as open/unconfirmed until a clear bear-market bottom is established."
    )


def render_btc_validated_swing_cycle_analysis(price_df: pd.DataFrame, events_df: pd.DataFrame):
    st.markdown("## BTC Historical Benchmark")
    st.caption(
        "Reference-only view using historically validated BTC cycle tops/bottoms. Use this to compare against Auto-Detected Cycles."
    )

    cycle_df = calculate_btc_validated_swing_cycles(
        price_df=price_df,
        events_df=events_df,
    )

    if cycle_df.empty:
        st.info("No validated BTC cycle data available.")
        return

    render_btc_validated_cycle_summary(cycle_df)

    st.markdown("---")

    perf_fig = make_btc_validated_cycle_performance_chart(cycle_df)

    if perf_fig is not None:
        st.plotly_chart(perf_fig, width="stretch")

    timing_fig = make_btc_validated_cycle_timing_chart(cycle_df)

    if timing_fig is not None:
        st.plotly_chart(timing_fig, width="stretch")

    st.markdown("---")
    st.markdown("### Full Historical Benchmark Table")
    st.dataframe(cycle_df, width="stretch")

    csv_data = dataframe_to_csv_bytes(cycle_df)

    if csv_data is not None:
        st.download_button(
            label="Download validated BTC cycle data CSV",
            data=csv_data,
            file_name="BTC_validated_swing_cycle_analysis.csv",
            mime="text/csv",
            width="stretch",
        )


def render_btc_halving_impact_analysis(price_df: pd.DataFrame, events_df: pd.DataFrame):
    st.markdown("## BTC Halving Impact")
    st.caption(
        "This view measures fixed forward performance after each halving. "
        "It is not a macro cycle detector."
    )

    impact_df = calculate_btc_halving_impact_from_events(
        price_df=price_df,
        events_df=events_df,
    )

    if impact_df.empty:
        st.info("No BTC halving impact data available.")
        return

    st.markdown("### Halving Impact Summary")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Halvings Analysed", len(impact_df))

    with c2:
        avg_365 = impact_df["Return +365D %"].dropna().mean() if "Return +365D %" in impact_df.columns else np.nan
        st.metric(
            "Average +365D Return",
            f"{avg_365:,.2f}%" if pd.notna(avg_365) else "-",
        )

    with c3:
        avg_730 = impact_df["Return +730D %"].dropna().mean() if "Return +730D %" in impact_df.columns else np.nan
        st.metric(
            "Average +730D Return",
            f"{avg_730:,.2f}%" if pd.notna(avg_730) else "-",
        )

    with c4:
        avg_1095 = impact_df["Return +1095D %"].dropna().mean() if "Return +1095D %" in impact_df.columns else np.nan
        st.metric(
            "Average +1095D Return",
            f"{avg_1095:,.2f}%" if pd.notna(avg_1095) else "-",
        )

    st.info(
        "Forward Window Days is fixed at 1095 days by default so each halving can be compared consistently. "
        "For recent halvings, Available Coverage Days may be lower because future data does not exist yet."
    )

    st.markdown("---")

    returns_fig = make_btc_halving_forward_returns_chart(impact_df)

    if returns_fig is not None:
        st.plotly_chart(returns_fig, width="stretch")

    extremes_fig = make_btc_halving_window_extremes_chart(impact_df)

    if extremes_fig is not None:
        st.plotly_chart(extremes_fig, width="stretch")

    st.markdown("---")
    st.markdown("### Full Halving Impact Table")
    st.dataframe(impact_df, width="stretch")

    csv_data = dataframe_to_csv_bytes(impact_df)

    if csv_data is not None:
        st.download_button(
            label="Download BTC halving impact data CSV",
            data=csv_data,
            file_name="BTC_halving_impact_analysis.csv",
            mime="text/csv",
            width="stretch",
        )


def render_btc_halving_cycle_analysis(price_df: pd.DataFrame, events_df: pd.DataFrame):
    st.markdown("## BTC Cycle Analysis")
    st.caption(
        "Auto-Detected Cycles is the primary BTC cycle model. Historical Benchmark is kept only for validation/reference. "
        "Halving dates are extracted from the BTC events table."
    )

    view = st.radio(
        "BTC Cycle View",
        [
            "Auto-Detected Cycles",
            "Historical Benchmark",
            "Halving Impact",
        ],
        horizontal=True,
    )

    if view == "Auto-Detected Cycles":
        render_btc_auto_detected_cycle_analysis(
            price_df=price_df,
            events_df=events_df,
        )
        return

    if view == "Historical Benchmark":
        render_btc_validated_swing_cycle_analysis(
            price_df=price_df,
            events_df=events_df,
        )
        return

    halvings_df = extract_btc_halving_events(events_df)

    if halvings_df.empty:
        st.info("No BTC halving events found in the loaded BTC event table.")
        return

    render_btc_halving_impact_analysis(
        price_df=price_df,
        events_df=events_df,
    )
