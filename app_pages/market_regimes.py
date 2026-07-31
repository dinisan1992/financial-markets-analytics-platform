from dataclasses import dataclass
from datetime import date
from typing import Callable

import streamlit as st

from dashboard.market_regime_charts import (
    make_market_regime_timeline,
    make_regime_distribution_chart,
)
from services.market_regime_service import (
    REGIME_ASSETS,
    classify_market_regimes,
    prepare_market_regime_features,
    summarize_regime_performance,
)


@dataclass(frozen=True)
class MarketRegimeDeps:
    render_date_range_selector: Callable
    date_to_str: Callable
    load_regime_prices: Callable


def render_market_regimes(deps: MarketRegimeDeps):
    st.title("Market Regimes")

    start_date, end_date = deps.render_date_range_selector(
        default_start=date(2020, 1, 1),
        default_end=date.today(),
    )
    rolling_window = st.slider(
        "Regime Window (market observations)",
        min_value=20,
        max_value=120,
        value=30,
        step=5,
    )

    if st.button("Load market regimes", width="stretch"):
        try:
            with st.spinner("Loading regime assets and calculating classifications..."):
                prices, load_report = deps.load_regime_prices(
                    tuple(REGIME_ASSETS),
                    deps.date_to_str(start_date),
                    deps.date_to_str(end_date),
                )
                features = prepare_market_regime_features(prices, rolling_window=rolling_window)
                regimes = classify_market_regimes(features, rolling_window=rolling_window)

            st.session_state.market_regime_df = regimes
            st.session_state.market_regime_load_report = load_report
        except Exception as exc:
            st.session_state.market_regime_df = None
            st.error(f"Unable to calculate market regimes: {exc}")

    regime_df = st.session_state.get("market_regime_df")
    if regime_df is None or regime_df.empty:
        st.info("Load the regime analysis to view the current classification.")
        return

    load_report = st.session_state.get("market_regime_load_report")
    if load_report is not None and not load_report.empty:
        failures = load_report[load_report["status"] != "loaded"]
        if not failures.empty:
            st.dataframe(failures, hide_index=True, width="stretch")

    latest = regime_df.iloc[-1]
    with st.container(horizontal=True):
        st.metric("Current Regime", latest["market_regime"], border=True)
        st.metric("Regime Score", int(latest["regime_score"]), border=True)
        st.metric("Observation Date", str(latest["snapped_at"].date()), border=True)
        st.metric("Current VIX", f"{latest['VIX']:.2f}", border=True)

    summary = summarize_regime_performance(regime_df)
    tab_timeline, tab_summary, tab_data = st.tabs(
        ["Timeline", "Regime Statistics", "Data"],
        on_change="rerun",
    )

    if tab_timeline.open:
        with tab_timeline:
            figure = make_market_regime_timeline(regime_df)
            if figure is not None:
                st.plotly_chart(figure, width="stretch")

    if tab_summary.open:
        with tab_summary:
            figure = make_regime_distribution_chart(summary)
            if figure is not None:
                st.plotly_chart(figure, width="stretch")
            st.dataframe(summary, hide_index=True, width="stretch")

    if tab_data.open:
        with tab_data:
            st.dataframe(regime_df.tail(500), hide_index=True, width="stretch")
