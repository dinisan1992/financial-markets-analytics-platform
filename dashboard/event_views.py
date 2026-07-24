import numpy as np
import pandas as pd
import streamlit as st

from dashboard.event_charts import make_event_source_impact_chart
from services.event_analysis_service import (
    build_best_worst_event_tables,
    build_event_impact_interpretation,
    build_event_source_comparison_table,
    calculate_event_forward_returns,
    calculate_event_impact_summary,
)


def render_event_impact_summary(event_returns_df: pd.DataFrame):
    summary = calculate_event_impact_summary(event_returns_df)

    if not summary:
        st.info("No event impact data available.")
        return

    st.markdown("### Event Impact Summary")

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Events in Period", summary.get("events_count", 0))

    with c2:
        avg_7d = summary.get("avg_7d", np.nan)
        st.metric("Average Return +7D", f"{avg_7d:,.2f}%" if pd.notna(avg_7d) else "-")

    with c3:
        avg_30d = summary.get("avg_30d", np.nan)
        st.metric("Average Return +30D", f"{avg_30d:,.2f}%" if pd.notna(avg_30d) else "-")

    with c4:
        avg_90d = summary.get("avg_90d", np.nan)
        st.metric("Average Return +90D", f"{avg_90d:,.2f}%" if pd.notna(avg_90d) else "-")

    c5, c6, c7 = st.columns(3)

    with c5:
        best_return = summary.get("best_return", np.nan)
        best_event = summary.get("best_event") or "-"
        st.metric("Best +30D Reaction", f"{best_return:,.2f}%" if pd.notna(best_return) else "-")
        st.caption(str(best_event)[:80])

    with c6:
        worst_return = summary.get("worst_return", np.nan)
        worst_event = summary.get("worst_event") or "-"
        st.metric("Worst +30D Reaction", f"{worst_return:,.2f}%" if pd.notna(worst_return) else "-")
        st.caption(str(worst_event)[:80])

    with c7:
        st.metric("Most Impacted Source", summary.get("most_impacted_source", "-"))


def render_event_impact_tab(events_for_chart: pd.DataFrame, tech_df: pd.DataFrame):
    st.markdown("## Event Impact")

    if events_for_chart is None or events_for_chart.empty:
        st.info("No events available for the selected filter and date range.")
        return

    event_returns_df = calculate_event_forward_returns(
        events_df=events_for_chart,
        price_df=tech_df,
    )

    if event_returns_df.empty:
        st.info("No event return data available for the selected period.")
        return

    render_event_impact_summary(event_returns_df)

    st.markdown("#### Event Impact Interpretation")
    st.info(build_event_impact_interpretation(event_returns_df))

    st.markdown("---")

    st.markdown("### BTC Events vs World Events")

    comparison_df = build_event_source_comparison_table(event_returns_df)

    if comparison_df.empty:
        st.info("Not enough data to compare event sources.")
    else:
        st.dataframe(comparison_df, width="stretch")

    source_fig = make_event_source_impact_chart(event_returns_df)

    if source_fig is not None:
        st.plotly_chart(source_fig, width="stretch")
    else:
        st.info("Not enough data to calculate event source impact.")

    st.markdown("---")

    st.markdown("### Best and Worst Event Reactions")

    available_ranking_cols = [
        col for col in [
            "Return +7D %",
            "Return +30D %",
            "Return +90D %",
            "Return +180D %",
            "Return +365D %",
        ]
        if col in event_returns_df.columns
    ]

    if not available_ranking_cols:
        st.info("No forward return columns available for ranking.")
    else:
        ranking_col = st.selectbox(
            "Ranking Horizon",
            available_ranking_cols,
            index=1 if "Return +30D %" in available_ranking_cols else 0,
        )

        best_df, worst_df = build_best_worst_event_tables(
            event_returns_df=event_returns_df,
            ranking_col=ranking_col,
            n=10,
        )

        best_col, worst_col = st.columns(2)

        with best_col:
            st.markdown(f"#### Best Reactions by {ranking_col}")
            if best_df.empty:
                st.info("No positive/valid event reactions available.")
            else:
                st.dataframe(best_df, width="stretch")

        with worst_col:
            st.markdown(f"#### Worst Reactions by {ranking_col}")
            if worst_df.empty:
                st.info("No negative/valid event reactions available.")
            else:
                st.dataframe(worst_df, width="stretch")

    st.markdown("---")

    st.markdown("### Full Event Forward Returns Table")
    st.dataframe(event_returns_df, width="stretch")
