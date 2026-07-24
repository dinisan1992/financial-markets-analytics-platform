from dataclasses import dataclass
from datetime import date
from typing import Callable

import streamlit as st

from asset_config import ASSETS
from macro_config import MACRO_ASSETS


@dataclass(frozen=True)
class FedMacroDeps:
    render_date_range_selector: Callable
    date_to_str: Callable
    load_fed_macro_pair: Callable
    make_summary_cards: Callable
    make_dual_axis_chart: Callable
    make_base100_chart: Callable


def render_fed_macro(deps: FedMacroDeps):
    st.title("FED Macro vs Market")

    st.markdown(
        """
        Compares US/FED macro indicators with market assets.
        """
    )

    fed_options = {
        "US M2 Money Supply vs BTC": ("FED_M2", "BTC", date(2020, 1, 1), "base100"),
        "Fed Funds Rate vs NASDAQ 100": ("FED_FUNDS_RATE", "NASDAQ100", date(2020, 1, 1), "dual"),
        "Fed Total Assets vs S&P 500": ("FED_TOTAL_ASSETS", "SP500", date(2020, 1, 1), "base100"),
        "Credit Card Delinquency vs VIX": ("FED_CREDIT_CARD_DELINQUENCY", "VIX", date(2020, 1, 1), "dual"),
        "Bank Credit vs S&P 500": ("FED_BANK_CREDIT", "SP500", date(2020, 1, 1), "base100"),
    }

    selected_label = st.selectbox(
        "Choose a FED/market pair",
        list(fed_options.keys()),
    )

    macro_key, market_asset, default_start, chart_type = fed_options[selected_label]

    start_date, end_date = deps.render_date_range_selector(
        default_start=default_start,
        default_end=date.today(),
    )

    if st.button("Load FED analysis"):
        _load_and_render_fed_pair(
            deps=deps,
            macro_key=macro_key,
            market_asset=market_asset,
            start_date=start_date,
            end_date=end_date,
            chart_type=chart_type,
            selected_label=selected_label,
        )


def _load_and_render_fed_pair(
    deps: FedMacroDeps,
    macro_key,
    market_asset,
    start_date,
    end_date,
    chart_type,
    selected_label,
):
    try:
        with st.spinner("Loading FED/market data..."):
            df = deps.load_fed_macro_pair(
                macro_key=macro_key,
                market_asset=market_asset,
                start_date=deps.date_to_str(start_date),
                end_date=deps.date_to_str(end_date),
            )

        macro_cfg = MACRO_ASSETS[macro_key]
        market_cfg = ASSETS[market_asset]

        st.success("Data loaded successfully.")

        deps.make_summary_cards(
            df=df,
            macro_col=macro_key,
            market_col=market_asset,
        )

        st.dataframe(df.tail(20), width="stretch")

        if chart_type == "dual":
            fig = deps.make_dual_axis_chart(
                df=df,
                macro_col=macro_key,
                market_col=market_asset,
                macro_name=macro_cfg["display_name"],
                market_name=market_cfg["display_name"],
                macro_unit=macro_cfg.get("unit", ""),
                title=selected_label,
            )
        else:
            fig = deps.make_base100_chart(
                df=df,
                left_col=macro_key,
                right_col=market_asset,
                left_name=macro_cfg["display_name"],
                right_name=market_cfg["display_name"],
                title=selected_label,
            )

        if fig is not None:
            st.plotly_chart(fig, width="stretch")
        else:
            st.warning("Unable to generate the chart.")

    except Exception as exc:
        st.error(f"Error loading FED analysis: {exc}")
