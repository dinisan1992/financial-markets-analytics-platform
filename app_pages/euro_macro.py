from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd
import streamlit as st

from asset_config import ASSETS
from euro_series_config import EURO_MARKET_PAIRS, EURO_SERIES
from services.macro_analytics_service import prepare_macro_market_features


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
    st.markdown("Compares configured European macro series with market assets.")

    selected_pair_key = st.selectbox(
        "EURO/market pair",
        list(EURO_MARKET_PAIRS),
        format_func=lambda key: EURO_MARKET_PAIRS[key]["label"],
    )
    selected_cfg = EURO_MARKET_PAIRS[selected_pair_key]
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

    st.caption(selected_cfg["description"])
    if st.button("Load EURO analysis"):
        try:
            with st.spinner("Loading EURO/market data..."):
                frame = deps.load_euro_macro_pair(
                    euro_series_key=euro_series_key,
                    market_asset=market_asset,
                    start_date=deps.date_to_str(start_date),
                    end_date=deps.date_to_str(end_date),
                )
            st.session_state["euro_macro_result"] = {
                "pair_key": selected_pair_key,
                "frame": frame,
            }
            st.success("Data loaded successfully.")
        except Exception as exc:
            st.session_state.pop("euro_macro_result", None)
            st.error(f"Error loading EURO analysis: {exc}")

    state = st.session_state.get("euro_macro_result")
    if state and state.get("pair_key") == selected_pair_key:
        _render_euro_pair(
            deps,
            state["frame"],
            euro_series_key,
            market_asset,
            euro_cfg,
            selected_cfg,
            show_base100,
        )


def _render_euro_pair(
    deps,
    frame,
    euro_series_key,
    market_asset,
    euro_cfg,
    selected_cfg,
    show_base100,
):
    market_cfg = ASSETS[market_asset]
    features = prepare_macro_market_features(frame, euro_series_key, market_asset)
    deps.make_summary_cards(frame, euro_series_key, market_asset)
    st.caption(
        "Calendar policy: real market observations. Macro values are carried backward-to-forward "
        "only after their observation date; macro_age_days reports their age."
    )

    tab_chart, tab_features, tab_data = st.tabs(
        ["Comparison", "Macro Features", "Data"],
        on_change="rerun",
    )

    if tab_chart.open:
        with tab_chart:
            figure = deps.make_dual_axis_chart(
                df=frame,
                macro_col=euro_series_key,
                market_col=market_asset,
                macro_name=euro_cfg["display_name"],
                market_name=market_cfg["display_name"],
                macro_unit=euro_cfg.get("unit", ""),
                title=selected_cfg["label"],
            )
            if figure is not None:
                st.plotly_chart(figure, width="stretch")

            if show_base100:
                base_figure = deps.make_base100_chart(
                    df=frame,
                    left_col=euro_series_key,
                    right_col=market_asset,
                    left_name=euro_cfg["display_name"],
                    right_name=market_cfg["display_name"],
                    title=f"Base 100 - {selected_cfg['label']}",
                )
                if base_figure is not None:
                    st.plotly_chart(base_figure, width="stretch")

    if tab_features.open:
        with tab_features:
            latest = features.iloc[-1]
            c1, c2, c3 = st.columns(3)
            c1.metric("Macro Observation Age", f"{int(latest['macro_age_days'])} days")
            c2.metric("30-Observation Correlation", _format_number(latest.get("rolling_correlation_30obs")))
            c3.metric("90-Observation Correlation", _format_number(latest.get("rolling_correlation_90obs")))
            feature_columns = [
                column for column in features.columns
                if column == "snapped_at" or "change_" in column or "return_" in column
                or "zscore_" in column or "correlation_" in column
            ]
            st.dataframe(features[feature_columns].tail(250), hide_index=True, width="stretch")

    if tab_data.open:
        with tab_data:
            st.dataframe(frame.tail(500), hide_index=True, width="stretch")


def _format_number(value):
    return f"{value:.3f}" if pd.notna(value) else "-"
