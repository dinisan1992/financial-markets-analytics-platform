import streamlit as st

from services.project_status_service import load_project_status


def render_project_status():
    st.markdown(load_project_status())
