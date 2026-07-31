import streamlit as st


PAGES = [
    "Overview",
    "Asset Explorer",
    "Market Event Analysis",
    "Correlations",
    "Market Regimes",
    "FED Macro",
    "EURO Macro",
    "Data Quality",
    "Project Status",
]


def render_sidebar():
    st.sidebar.title("Analytics Platform")
    page = st.sidebar.radio("Page", PAGES)
    st.sidebar.markdown("---")
    st.sidebar.caption("Macro-Financial Risk & Market Behaviour Analytics Platform")
    return page
