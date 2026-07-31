from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd
import streamlit as st

from asset_config import ASSETS
from macro_config import MACRO_ASSETS, MACRO_MARKET_PAIRS
from services.macro_analytics_service import prepare_macro_market_features


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
    st.markdown("Compares active US/FED macro indicators with market assets.")

    selected_pair_key = st.selectbox(
        "FED/market pair",
        list(MACRO_MARKET_PAIRS),
        format_func=lambda key: MACRO_MARKET_PAIRS[key]["name"],
    )
    selected_cfg = MACRO_MARKET_PAIRS[selected_pair_key]
    macro_key = selected_cfg["macro_asset"]
    market_asset = selected_cfg["market_asset"]

    start_date, end_date = deps.render_date_range_selector(
        default_start=date(2000, 1, 1),
        default_end=date.today(),
    )

    st.caption(selected_cfg["description"])
    if st.button("Load FED analysis"):
        try:
            with st.spinner("Loading FED/market data..."):
                frame = deps.load_fed_macro_pair(
                    macro_key=macro_key,
                    market_asset=market_asset,
                    start_date=deps.date_to_str(start_date),
                    end_date=deps.date_to_str(end_date),
                )
            st.session_state["fed_macro_result"] = {
                "pair_key": selected_pair_key,
                "frame": frame,
            }
            st.success("Data loaded successfully.")
        except Exception as exc:
            st.session_state.pop("fed_macro_result", None)
            st.error(f"Error loading FED analysis: {exc}")

    state = st.session_state.get("fed_macro_result")
    if state and state.get("pair_key") == selected_pair_key:
        _render_fed_pair(
            deps,
            state["frame"],
            macro_key,
            market_asset,
            selected_cfg,
        )


def _render_fed_pair(deps, frame, macro_key, market_asset, selected_cfg):
    macro_cfg = MACRO_ASSETS[macro_key]
    market_cfg = ASSETS[market_asset]
    features = prepare_macro_market_features(frame, macro_key, market_asset)

    deps.make_summary_cards(frame, macro_key, market_asset)
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
            if macro_cfg.get("category") in {"rates", "consumer_stress"}:
                figure = deps.make_dual_axis_chart(
                    df=frame,
                    macro_col=macro_key,
                    market_col=market_asset,
                    macro_name=macro_cfg["display_name"],
                    market_name=market_cfg["display_name"],
                    macro_unit=macro_cfg.get("unit", ""),
                    title=selected_cfg["name"],
                )
            else:
                figure = deps.make_base100_chart(
                    df=frame,
                    left_col=macro_key,
                    right_col=market_asset,
                    left_name=macro_cfg["display_name"],
                    right_name=market_cfg["display_name"],
                    title=selected_cfg["name"],
                )
            if figure is not None:
                st.plotly_chart(figure, width="stretch")

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
