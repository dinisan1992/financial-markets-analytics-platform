import streamlit as st

from asset_config import ASSETS
from euro_series_config import EURO_MARKET_PAIRS, EURO_SERIES
from macro_config import MACRO_ASSETS


def render_overview():
    st.title("Macro-Financial Risk & Market Behaviour Analytics Platform")

    st.markdown(
        """
        Multi-asset analytics platform with technical indicators, macro-financial analysis,
        market regimes, rolling correlations and suspicious behaviour detection.
        """
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("FED indicators", len(MACRO_ASSETS))

    with c2:
        active_euro = sum(
            1 for _, cfg in EURO_SERIES.items()
            if cfg.get("enabled", True)
        )
        st.metric("EURO active series", active_euro)

    with c3:
        st.metric("EURO market pairs", len(EURO_MARKET_PAIRS))

    with c4:
        st.metric("Market assets", len(ASSETS))

    st.markdown("---")

    st.subheader("Current modules")

    st.success("FED macro layer validated.")
    st.success("EURO macro layer v1 validated.")
    st.success("Asset Explorer with an integrated technical dashboard, historical events and suspicious flags.")
    st.success("Correlations with heatmap, rolling correlation, scatter and Base 100 views.")
    st.info("EURO fraud layer is documented as a separate backlog.")

    st.markdown("---")

    st.subheader("Charts included in this version")

    st.markdown(
        """
        - KPI Cards
        - Candlestick
        - Line Chart
        - Bar Chart
        - Scatter Plot
        - Box Plot
        - Heatmap
        - Rolling Correlation
        - Multi-Asset Base 100
        - Volume Chart
        - Volume Z-Score
        - RSI
        - Stochastic RSI
        - MACD
        - Drawdown
        - Rolling Volatility
        - Suspicious events table
        """
    )
