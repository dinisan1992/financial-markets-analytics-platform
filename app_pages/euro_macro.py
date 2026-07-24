from dataclasses import dataclass
from datetime import date
from typing import Callable

import streamlit as st

from asset_config import ASSETS
from euro_series_config import EURO_MARKET_PAIRS, EURO_SERIES


@dataclass(frozen=True)
class EuroMacroDeps:
    render_date_range_selector: Callable
    date_to_str: Callable
    load_euro_macro_pair: Callable
    make_summary_cards: Callable
    make_dual_axis_chart: Callable
    make_base100_chart: Callable


def render_euro_macro(deps: EuroMacroDeps):
    st.title("EURO Macro vs Market")

    st.markdown(
        """
        Compares filtered European macro series with market assets.
        """
    )

    euro_options = {
        pair_key: cfg
        for pair_key, cfg in EURO_MARKET_PAIRS.items()
    }

    selected_pair_key = st.selectbox(
        "Choose a EURO/market pair",
        list(euro_options.keys()),
        format_func=lambda key: euro_options[key]["label"],
    )

    selected_cfg = euro_options[selected_pair_key]

    euro_series_key = selected_cfg["euro_series"]
    market_asset = selected_cfg["market_asset"]
    euro_cfg = EURO_SERIES[euro_series_key]

    start_date, end_date = deps.render_date_range_selector(
        default_start=date(2000, 1, 1),
        default_end=date.today(),
    )

    show_base100 = st.checkbox(
        "Show Base 100 chart",
        value=euro_cfg.get("base100_recommended", False),
    )

    if st.button("Load EURO analysis"):
        _load_and_render_euro_pair(
            deps=deps,
            euro_series_key=euro_series_key,
            market_asset=market_asset,
            start_date=start_date,
            end_date=end_date,
            euro_cfg=euro_cfg,
            selected_cfg=selected_cfg,
            show_base100=show_base100,
        )


def _load_and_render_euro_pair(
    deps: EuroMacroDeps,
    euro_series_key,
    market_asset,
    start_date,
    end_date,
    euro_cfg,
    selected_cfg,
    show_base100,
):
    try:
        with st.spinner("Loading EURO/market data..."):
            df = deps.load_euro_macro_pair(
                euro_series_key=euro_series_key,
                market_asset=market_asset,
                start_date=deps.date_to_str(start_date),
                end_date=deps.date_to_str(end_date),
            )

        market_cfg = ASSETS[market_asset]

        st.success("Data loaded successfully.")

        deps.make_summary_cards(
            df=df,
            macro_col=euro_series_key,
            market_col=market_asset,
        )

        st.dataframe(df.tail(20), width="stretch")

        fig_dual = deps.make_dual_axis_chart(
            df=df,
            macro_col=euro_series_key,
            market_col=market_asset,
            macro_name=euro_cfg["display_name"],
            market_name=market_cfg["display_name"],
            macro_unit=euro_cfg.get("unit", ""),
            title=selected_cfg["label"],
        )

        if fig_dual is not None:
            st.plotly_chart(fig_dual, width="stretch")
        else:
            st.warning("Unable to generate the dual-axis chart.")

        if show_base100:
            fig_base = deps.make_base100_chart(
                df=df,
                left_col=euro_series_key,
                right_col=market_asset,
                left_name=euro_cfg["display_name"],
                right_name=market_cfg["display_name"],
                title=f"Base 100 - {selected_cfg['label']}",
            )

            st.plotly_chart(fig_base, width="stretch")

    except Exception as exc:
        st.error(f"Error loading EURO analysis: {exc}")
