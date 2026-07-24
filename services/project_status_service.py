from pathlib import Path

import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@st.cache_data(show_spinner=False)
def load_project_status():
    status_file = PROJECT_ROOT / "PROJECT_STATUS.md"

    if not status_file.exists():
        return "PROJECT_STATUS.md not found."

    try:
        return status_file.read_text(encoding="utf-8")
    except Exception as exc:
        return f"Error reading PROJECT_STATUS.md: {exc}"
