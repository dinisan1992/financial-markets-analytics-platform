import streamlit as st

from datetime import date

from macro_data_loader import (
    get_engine as get_macro_engine,
    alinhar_macro_com_market
)

from euro_data_loader import (
    alinhar_euro_com_market
)

from asset_config import ASSETS

from app.layout import setup_page
from app.navigation import render_sidebar
from app.state import initialize_session_state
from app_pages.asset_explorer import AssetExplorerDeps, render_asset_explorer
from app_pages.correlations import CorrelationsDeps, render_correlations
from app_pages.euro_macro import EuroMacroDeps, render_euro_macro
from app_pages.fed_macro import FedMacroDeps, render_fed_macro
from app_pages.market_event_analysis import (
    MarketEventAnalysisDeps,
    render_market_event_analysis,
)
from app_pages.overview import render_overview
from app_pages.project_status import render_project_status
from dashboard.asset_view_components import (
    render_asset_kpi_cards,
    render_return_distribution_summary,
    render_suspicion_score,
    render_suspicious_events_table,
    render_technical_signal_summary,
)
from dashboard.btc_cycle_views import render_btc_halving_cycle_analysis
from dashboard.event_charts import (
    make_event_category_heatmap,
    make_event_impact_heatmap,
)
from dashboard.event_views import render_event_impact_tab
from dashboard.macro_charts import (
    make_base100_chart,
    make_dual_axis_chart,
    make_summary_cards,
)
from services.btc_cycle_service import (
    calculate_btc_auto_detected_cycles,
    calculate_btc_halving_impact_from_events,
    calculate_btc_validated_swing_cycles,
)
from services import data_access_service
from services.event_analysis_service import (
    build_event_impact_matrix,
    calculate_cross_asset_event_impact,
    calculate_event_category_asset_summary,
    calculate_event_forward_returns,
    calculate_risk_on_off_snapshot,
    filter_events_for_chart,
)
from services.export_service import dataframe_to_csv_bytes
from services.risk_statistics_service import filter_df_by_recent_window


# =========================
# STREAMLIT CONFIG
# =========================

setup_page()


# =========================
# SESSION STATE INIT
# =========================

initialize_session_state()

# =========================
# ENGINE / CACHE
# =========================

@st.cache_resource
def get_engine():
    return get_macro_engine()


# =========================
# DATE HELPERS
# =========================

def render_date_range_selector(default_start=date(2020, 1, 1), default_end=None):
    if default_end is None:
        default_end = date.today()

    selected_range = st.date_input(
        "Date Range",
        value=(default_start, default_end),
        format="YYYY-MM-DD"
    )

    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        st.warning("Select a start date and an end date.")
        start_date, end_date = default_start, default_end

    return start_date, end_date


def date_to_str(value):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    return value.strftime("%Y-%m-%d")


# =========================
# ASSET DATA LOADERS
# =========================

@st.cache_data(show_spinner=True)
def get_table_columns(table_name):
    return data_access_service.get_table_columns(
        engine=get_engine(),
        table_name=table_name,
    )


# =========================
# EVENT LOADERS
# =========================

def detect_column(columns, candidates):
    return data_access_service.detect_column(
        columns=columns,
        candidates=candidates,
    )


@st.cache_data(show_spinner=True)
def table_exists(table_name):
    return data_access_service.table_exists(
        engine=get_engine(),
        table_name=table_name,
    )


@st.cache_data(show_spinner=True)
def load_events_from_table(table_name, start_date=None, end_date=None):
    return data_access_service.load_events_from_table(
        engine=get_engine(),
        table_name=table_name,
        start_date=start_date,
        end_date=end_date,
        table_exists_func=table_exists,
        get_table_columns_func=get_table_columns,
    )


@st.cache_data(show_spinner=True)
def load_asset_events(start_date=None, end_date=None):
    return data_access_service.load_asset_events(
        load_events_from_table_func=load_events_from_table,
        start_date=start_date,
        end_date=end_date,
    )


# =========================
# ASSET DATA LOADER
# =========================

@st.cache_data(show_spinner=True)
def load_asset_data(asset_key, start_date=None, end_date=None):
    return data_access_service.load_asset_data(
        engine=get_engine(),
        assets_config=ASSETS,
        asset_key=asset_key,
        start_date=start_date,
        end_date=end_date,
        get_table_columns_func=get_table_columns,
    )


# =========================
# FED / EURO LOADERS
# =========================

@st.cache_data(show_spinner=True)
def load_fed_macro_pair(macro_key, market_asset, start_date, end_date):
    return data_access_service.load_fed_macro_pair(
        engine=get_engine(),
        align_macro_func=alinhar_macro_com_market,
        macro_key=macro_key,
        market_asset=market_asset,
        start_date=start_date,
        end_date=end_date,
    )


@st.cache_data(show_spinner=True)
def load_euro_macro_pair(euro_series_key, market_asset, start_date, end_date):
    return data_access_service.load_euro_macro_pair(
        engine=get_engine(),
        align_euro_func=alinhar_euro_com_market,
        euro_series_key=euro_series_key,
        market_asset=market_asset,
        start_date=start_date,
        end_date=end_date,
    )


# =========================
# SIDEBAR
# =========================

page = render_sidebar()


# =========================
# PAGE - OVERVIEW
# =========================

if page == "Overview":
    render_overview()

# =========================
# PAGE - ASSET EXPLORER
# =========================

elif page == "Asset Explorer":
    render_asset_explorer(
        AssetExplorerDeps(
            render_date_range_selector=render_date_range_selector,
            date_to_str=date_to_str,
            load_asset_data=load_asset_data,
            load_asset_events=load_asset_events,
            filter_events_for_chart=filter_events_for_chart,
            render_asset_kpi_cards=render_asset_kpi_cards,
            render_technical_signal_summary=render_technical_signal_summary,
            render_event_impact_tab=render_event_impact_tab,
            render_btc_halving_cycle_analysis=render_btc_halving_cycle_analysis,
            filter_df_by_recent_window=filter_df_by_recent_window,
            render_suspicion_score=render_suspicion_score,
            render_suspicious_events_table=render_suspicious_events_table,
            render_return_distribution_summary=render_return_distribution_summary,
            calculate_event_forward_returns=calculate_event_forward_returns,
            calculate_btc_auto_detected_cycles=calculate_btc_auto_detected_cycles,
            calculate_btc_validated_swing_cycles=calculate_btc_validated_swing_cycles,
            calculate_btc_halving_impact_from_events=calculate_btc_halving_impact_from_events,
            dataframe_to_csv_bytes=dataframe_to_csv_bytes,
        )
    )

# =========================
# PAGE - MARKET EVENT ANALYSIS
# =========================
elif page == "Market Event Analysis":
    render_market_event_analysis(
        MarketEventAnalysisDeps(
            render_date_range_selector=render_date_range_selector,
            assets_config=ASSETS,
            load_asset_events=load_asset_events,
            load_asset_data=load_asset_data,
            calculate_cross_asset_event_impact=calculate_cross_asset_event_impact,
            build_event_impact_matrix=build_event_impact_matrix,
            make_event_impact_heatmap=make_event_impact_heatmap,
            calculate_event_category_asset_summary=calculate_event_category_asset_summary,
            make_event_category_heatmap=make_event_category_heatmap,
            calculate_risk_on_off_snapshot=calculate_risk_on_off_snapshot,
            dataframe_to_csv_bytes=dataframe_to_csv_bytes,
        )
    )

# =========================
# PAGE - CORRELATIONS
# =========================
elif page == "Correlations":
    render_correlations(
        CorrelationsDeps(
            get_engine=get_engine,
            render_date_range_selector=render_date_range_selector,
            date_to_str=date_to_str,
        )
    )

# =========================
# PAGE - FED MACRO
# =========================
elif page == "FED Macro":
    render_fed_macro(
        FedMacroDeps(
            render_date_range_selector=render_date_range_selector,
            date_to_str=date_to_str,
            load_fed_macro_pair=load_fed_macro_pair,
            make_summary_cards=make_summary_cards,
            make_dual_axis_chart=make_dual_axis_chart,
            make_base100_chart=make_base100_chart,
        )
    )

# =========================
# PAGE - EURO MACRO
# =========================

elif page == "EURO Macro":
    render_euro_macro(
        EuroMacroDeps(
            render_date_range_selector=render_date_range_selector,
            date_to_str=date_to_str,
            load_euro_macro_pair=load_euro_macro_pair,
            make_summary_cards=make_summary_cards,
            make_dual_axis_chart=make_dual_axis_chart,
            make_base100_chart=make_base100_chart,
        )
    )

# =========================
# PAGE - PROJECT STATUS
# =========================
elif page == "Project Status":
    render_project_status()
