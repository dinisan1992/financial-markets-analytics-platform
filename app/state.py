import streamlit as st


SESSION_DEFAULTS = {
    "asset_loaded": False,
    "asset_key": None,
    "asset_display_name": None,
    "asset_tech_df": None,
    "corr_loaded": False,
    "corr_price_df": None,
    "corr_returns_df": None,
    "corr_corr_df": None,
    "corr_pairs_df": None,
    "corr_selected_assets": None,
    "corr_window": 90,
    "corr_load_report": None,
    "event_load_report": None,
    "data_quality_results": None,
    "market_regime_df": None,
    "market_regime_load_report": None,
    "asset_events_df": None,
}


def initialize_session_state():
    for key, default_value in SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
