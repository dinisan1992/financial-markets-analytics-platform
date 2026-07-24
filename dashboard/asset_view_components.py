import pandas as pd
import streamlit as st

from dashboard.asset_indicators import get_suspicious_events
from services.risk_statistics_service import (
    calculate_return_distribution_summary,
    calculate_suspicion_score,
)
from services.technical_signal_service import (
    build_current_technical_interpretation,
    calculate_technical_signal_summary,
)


def render_technical_signal_summary(df: pd.DataFrame, asset_label: str = "The asset"):
    summary = calculate_technical_signal_summary(df)

    if not summary:
        st.info("Technical Signal Summary unavailable.")
        return

    st.markdown("### Current Technical Signal Summary")

    signal_date = summary.get("signal_date")

    if pd.notna(signal_date):
        st.caption(f"Signal date: {pd.to_datetime(signal_date).date()}")

    s1, s2, s3, s4 = st.columns(4)

    with s1:
        st.metric("Trend", summary.get("trend", "-"))

    with s2:
        st.metric("Price vs EMA200", summary.get("price_vs_ema200", "-"))

    with s3:
        st.metric("RSI State", summary.get("rsi_state", "-"))

    with s4:
        st.metric("MACD State", summary.get("macd_state", "-"))

    s5, s6, s7, s8 = st.columns(4)

    with s5:
        st.metric("Volume State", summary.get("volume_state", "-"))

    with s6:
        st.metric("Volatility State", summary.get("volatility_state", "-"))

    with s7:
        st.metric("Suspicious Activity", summary.get("suspicious_state", "-"))

    with s8:
        st.metric("Suspicious Events Last 30D", summary.get("recent_suspicious_count", 0))

    st.markdown("#### Current Interpretation")
    st.info(build_current_technical_interpretation(summary, asset_label=asset_label))


def render_asset_kpi_cards(kpis):
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        value = kpis.get("latest_price")
        st.metric("Latest Price", f"{value:,.2f}" if value is not None else "-")

    with c2:
        value = kpis.get("total_return")
        st.metric("Period Return", f"{value:,.2f}%" if value is not None else "-")

    with c3:
        value = kpis.get("latest_rsi")
        st.metric("Current RSI", f"{value:,.2f}" if value is not None else "-")

    with c4:
        value = kpis.get("latest_macd")
        st.metric("Current MACD", f"{value:,.2f}" if value is not None else "-")

    c5, c6, c7, c8 = st.columns(4)

    with c5:
        value = kpis.get("latest_volatility")
        st.metric("30D Volatility", f"{value:,.2f}%" if value is not None else "-")

    with c6:
        value = kpis.get("latest_drawdown")
        st.metric("Current Drawdown", f"{value:,.2f}%" if value is not None else "-")

    with c7:
        st.metric("Suspicious Events", kpis.get("suspicious_count", 0))

    with c8:
        pump = kpis.get("pump_dump_count", 0)
        spoof = kpis.get("spoofing_count", 0)
        st.metric("Pump/Dump | Spoofing", f"{pump} | {spoof}")


def render_suspicious_events_table(df):
    suspicious_df = get_suspicious_events(df)

    if suspicious_df.empty:
        st.info("No suspicious events found in the selected period.")
        return

    st.dataframe(
        suspicious_df,
        width="stretch",
    )


def render_suspicion_score(df: pd.DataFrame, window_label: str):
    score_data = calculate_suspicion_score(df)

    st.markdown("### Suspicion Score")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            "Suspicion Score",
            f"{score_data.get('score', 0)}/100",
        )

    with c2:
        st.metric(
            "Risk Level",
            score_data.get("risk_level", "-"),
        )

    with c3:
        st.metric(
            "Risk Window",
            window_label,
        )

    with c4:
        st.metric(
            "Suspicious Events",
            score_data.get("suspicious_events", 0),
        )

    d1, d2, d3, d4 = st.columns(4)

    with d1:
        st.metric(
            "Volume Spikes",
            score_data.get("volume_spikes", 0),
        )

    with d2:
        st.metric(
            "Pump/Dump Flags",
            score_data.get("pump_dump", 0),
        )

    with d3:
        st.metric(
            "Spoofing Flags",
            score_data.get("spoofing", 0),
        )

    with d4:
        st.metric(
            "Extreme RSI",
            score_data.get("extreme_rsi", 0),
        )

    days_count = score_data.get("days_count", 0)
    suspicious_rate = score_data.get("suspicious_rate", 0)

    st.caption(
        f"The score is based on signal density and severity within the selected risk window. "
        f"Window observations: {days_count}. "
        f"Suspicious signal density: {suspicious_rate * 100:.2f}%."
    )


def render_return_distribution_summary(df: pd.DataFrame):
    summary = calculate_return_distribution_summary(df)

    if not summary:
        st.info("Return distribution summary unavailable. No valid daily return column was found.")
        return

    st.markdown("### Return Distribution Summary")
    st.caption(f"Based on column: {summary.get('return_col')}")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Average Daily Return", f"{summary['average_return']:,.2f}%")

    with c2:
        st.metric("Median Daily Return", f"{summary['median_return']:,.2f}%")

    with c3:
        st.metric("Best Day", f"{summary['best_day']:,.2f}%")

    with c4:
        st.metric("Worst Day", f"{summary['worst_day']:,.2f}%")

    c5, c6, c7 = st.columns(3)

    with c5:
        st.metric("Positive Days", f"{summary['positive_days_pct']:,.2f}%")

    with c6:
        st.metric("Negative Days", f"{summary['negative_days_pct']:,.2f}%")

    with c7:
        st.metric("Return Observations", f"{summary['observations']:,}")
