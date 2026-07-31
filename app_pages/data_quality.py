from dataclasses import dataclass
from typing import Callable

import pandas as pd
import streamlit as st

from services.data_quality_service import build_audit_summary, build_audit_zip_bytes


@dataclass(frozen=True)
class DataQualityDeps:
    load_data_quality_audit: Callable


def render_data_quality(deps: DataQualityDeps):
    st.title("Data Quality")

    if st.button("Run read-only data audit", width="stretch"):
        try:
            with st.spinner("Auditing asset, correlation and event coverage..."):
                st.session_state.data_quality_results = deps.load_data_quality_audit()
        except Exception as exc:
            st.session_state.data_quality_results = None
            st.error(f"Data audit failed: {exc}")

    results = st.session_state.get("data_quality_results")
    if not results:
        st.info("Run the audit to inspect the current database coverage.")
        return

    summary = build_audit_summary(results)
    with st.container(horizontal=True):
        st.metric("Assets", summary["asset_count"], border=True)
        st.metric("Healthy", summary["assets_ok"], border=True)
        st.metric("Warnings", summary["assets_warning"], border=True)
        st.metric("Errors", summary["assets_error"], border=True)
        st.metric("Potentially Biased Pairs", summary["potentially_biased_pairs"], border=True)

    tab_assets, tab_pairs, tab_events, tab_export = st.tabs(
        ["Assets", "Correlation Coverage", "Event Coverage", "Export"],
        on_change="rerun",
    )

    if tab_assets.open:
        with tab_assets:
            asset_audit = results.get("asset_audit", pd.DataFrame())
            if asset_audit.empty:
                st.info("No asset audit rows are available.")
            else:
                status_options = asset_audit["status"].dropna().unique().tolist()
                selected_status = st.multiselect(
                    "Status",
                    status_options,
                    default=status_options,
                )
                filtered = asset_audit[asset_audit["status"].isin(selected_status)]
                st.dataframe(filtered, hide_index=True, width="stretch")

    if tab_pairs.open:
        with tab_pairs:
            pair_audit = results.get("correlation_coverage", pd.DataFrame())
            if pair_audit.empty:
                st.info("No pair coverage rows are available.")
            else:
                show_flagged_only = st.checkbox("Show potentially biased pairs only", value=True)
                if show_flagged_only:
                    pair_audit = pair_audit[pair_audit["potential_bias"]]
                st.dataframe(pair_audit, hide_index=True, width="stretch")

    if tab_events.open:
        with tab_events:
            event_audit = results.get("event_coverage", pd.DataFrame())
            if event_audit.empty:
                st.info("No event coverage rows are available.")
            else:
                st.dataframe(event_audit, hide_index=True, width="stretch")

    if tab_export.open:
        with tab_export:
            zip_bytes = build_audit_zip_bytes(results)
            st.download_button(
                "Download aggregated audit ZIP",
                data=zip_bytes,
                file_name="audit_outputs.zip",
                mime="application/zip",
                width="stretch",
            )
