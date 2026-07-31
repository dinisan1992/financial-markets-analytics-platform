from dataclasses import dataclass
from typing import Callable

import pandas as pd
import streamlit as st

from services.data_quality_service import (
    build_audit_summary,
    build_audit_zip_bytes,
    build_freshness_report,
    build_remediation_report,
)


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

    asset_audit = results.get("asset_audit", pd.DataFrame())
    freshness = results.get("freshness_report")
    remediation = results.get("remediation_report")
    if freshness is None:
        freshness = build_freshness_report(asset_audit)
    if remediation is None:
        remediation = build_remediation_report(asset_audit)

    summary = build_audit_summary(results)
    with st.container(horizontal=True):
        st.metric("Assets", summary["asset_count"], border=True)
        st.metric("Healthy", summary["assets_ok"], border=True)
        st.metric("Stale", summary["stale_assets"], border=True)
        st.metric("Duplicate Assets", summary["assets_with_duplicates"], border=True)
        st.metric("Price Review", summary["assets_requiring_price_review"], border=True)
        st.metric("Biased Pairs", summary["potentially_biased_pairs"], border=True)

    tabs = st.tabs(
        [
            "Assets",
            "Freshness",
            "Remediation",
            "Correlation Coverage",
            "Event Coverage",
            "Export",
        ],
        on_change="rerun",
    )

    if tabs[0].open:
        with tabs[0]:
            _render_asset_audit(asset_audit)

    if tabs[1].open:
        with tabs[1]:
            _render_freshness(freshness)

    if tabs[2].open:
        with tabs[2]:
            _render_remediation(remediation)

    if tabs[3].open:
        with tabs[3]:
            _render_pair_coverage(results.get("correlation_coverage", pd.DataFrame()))

    if tabs[4].open:
        with tabs[4]:
            _render_event_coverage(results.get("event_coverage", pd.DataFrame()))

    if tabs[5].open:
        with tabs[5]:
            _render_export(results)


def _render_asset_audit(asset_audit: pd.DataFrame):
    if asset_audit.empty:
        st.info("No asset audit rows are available.")
        return

    status_options = asset_audit["status"].dropna().unique().tolist()
    selected_status = st.multiselect("Status", status_options, default=status_options)
    filtered = asset_audit[asset_audit["status"].isin(selected_status)]
    st.dataframe(
        filtered,
        hide_index=True,
        width="stretch",
        column_config={
            "asset": st.column_config.TextColumn("Asset", pinned=True),
            "calendar_coverage_pct": st.column_config.ProgressColumn(
                "Calendar Coverage",
                min_value=0,
                max_value=100,
                format="%.2f%%",
            ),
            "zero_return_pct": st.column_config.NumberColumn("Zero Returns", format="%.2f%%"),
            "native_ohlc_pct": st.column_config.NumberColumn("Native OHLC", format="%.2f%%"),
        },
    )


def _render_freshness(freshness: pd.DataFrame):
    if freshness.empty:
        st.info("No freshness rows are available.")
        return

    stale_only = st.checkbox("Show stale assets only", value=True)
    filtered = freshness
    if stale_only:
        filtered = filtered[filtered["freshness_status"] == "STALE"]

    st.dataframe(
        filtered,
        hide_index=True,
        width="stretch",
        column_config={
            "asset": st.column_config.TextColumn("Asset", pinned=True),
            "last_date": st.column_config.DateColumn("Last Observation"),
            "stale_days": st.column_config.NumberColumn("Age (days)", format="%d"),
            "stale_limit_days": st.column_config.NumberColumn("Limit (days)", format="%d"),
            "days_overdue": st.column_config.NumberColumn("Overdue (days)", format="%d"),
        },
    )


def _render_remediation(remediation: pd.DataFrame):
    if remediation.empty:
        st.success("No remediation tasks were identified.")
        return

    priorities = remediation["priority"].dropna().unique().tolist()
    selected = st.multiselect("Priority", priorities, default=priorities)
    filtered = remediation[remediation["priority"].isin(selected)]
    st.dataframe(
        filtered,
        hide_index=True,
        width="stretch",
        column_config={
            "priority": st.column_config.TextColumn("Priority", pinned=True),
            "asset": st.column_config.TextColumn("Asset", pinned=True),
        },
    )


def _render_pair_coverage(pair_audit: pd.DataFrame):
    if pair_audit.empty:
        st.info("No pair coverage rows are available.")
        return

    confidence_options = pair_audit["correlation_confidence"].dropna().unique().tolist()
    c1, c2 = st.columns(2)
    with c1:
        selected_confidence = st.multiselect(
            "Confidence",
            confidence_options,
            default=confidence_options,
        )
    with c2:
        flagged_only = st.checkbox("Show potentially biased pairs only", value=True)

    filtered = pair_audit[
        pair_audit["correlation_confidence"].isin(selected_confidence)
    ]
    if flagged_only:
        filtered = filtered[filtered["potential_bias"]]

    st.dataframe(
        filtered,
        hide_index=True,
        width="stretch",
        column_config={
            "coverage_ratio": st.column_config.ProgressColumn(
                "Coverage Ratio",
                min_value=0.0,
                max_value=1.0,
                format="percent",
            ),
            "full_period_correlation": st.column_config.NumberColumn(
                "Correlation",
                format="%.4f",
            ),
            "correlation_ci95_low": st.column_config.NumberColumn("95% CI Low", format="%.4f"),
            "correlation_ci95_high": st.column_config.NumberColumn("95% CI High", format="%.4f"),
        },
    )


def _render_event_coverage(event_audit: pd.DataFrame):
    if event_audit.empty:
        st.info("No event coverage rows are available.")
        return
    st.dataframe(event_audit, hide_index=True, width="stretch")


def _render_export(results: dict[str, pd.DataFrame]):
    zip_bytes = build_audit_zip_bytes(results)
    st.download_button(
        "Download aggregated audit ZIP",
        data=zip_bytes,
        file_name="audit_outputs.zip",
        mime="application/zip",
        width="stretch",
    )
