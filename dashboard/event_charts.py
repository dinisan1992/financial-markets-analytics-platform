import pandas as pd
import plotly.graph_objects as go



def make_event_source_impact_chart(event_returns_df: pd.DataFrame):
    if event_returns_df is None or event_returns_df.empty:
        return None

    if "Source" not in event_returns_df.columns:
        return None

    return_cols = [
        col for col in [
            "Return +7D %",
            "Return +30D %",
            "Return +90D %",
            "Return +180D %",
            "Return +365D %",
        ]
        if col in event_returns_df.columns
    ]

    if not return_cols:
        return None

    plot_df = event_returns_df.copy()

    for col in return_cols:
        plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")

    grouped = (
        plot_df.groupby("Source")[return_cols]
        .mean()
        .reset_index()
    )

    if grouped.empty:
        return None

    fig = go.Figure()

    for col in return_cols:
        fig.add_trace(
            go.Bar(
                x=grouped["Source"],
                y=grouped[col],
                name=col.replace("Return ", "")
            )
        )

    fig.update_layout(
        title="Average Forward Returns by Event Source",
        template="plotly_dark",
        height=500,
        barmode="group",
        xaxis_title="Event Source",
        yaxis_title="Average Forward Return (%)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=70, b=60)
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(220,220,220,0.55)"
    )

    return fig



def make_event_impact_heatmap(matrix_df: pd.DataFrame, title: str):
    if matrix_df is None or matrix_df.empty:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix_df.values,
            x=matrix_df.columns.tolist(),
            y=matrix_df.index.tolist(),
            colorscale="RdYlGn",
            zmid=0,
            colorbar=dict(title="Return %"),
            hovertemplate=(
                "Event: %{y}<br>"
                "Asset: %{x}<br>"
                "Return: %{z:.2f}%"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=max(520, min(1100, 70 + 34 * len(matrix_df.index))),
        xaxis_title="Asset",
        yaxis_title="Event",
        margin=dict(l=260, r=40, t=70, b=40)
    )

    return fig



def make_event_category_heatmap(summary_df: pd.DataFrame):
    if summary_df is None or summary_df.empty:
        return None

    matrix = summary_df.pivot_table(
        index="Category",
        columns="Asset",
        values="Average_Return",
        aggfunc="mean"
    )

    if matrix.empty:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            x=matrix.columns.tolist(),
            y=matrix.index.tolist(),
            colorscale="RdYlGn",
            zmid=0,
            colorbar=dict(title="Avg Return %"),
            hovertemplate=(
                "Category: %{y}<br>"
                "Asset: %{x}<br>"
                "Avg Return: %{z:.2f}%"
                "<extra></extra>"
            )
        )
    )

    fig.update_layout(
        title="Average Event Return by Category and Asset",
        template="plotly_dark",
        height=max(420, min(900, 100 + 42 * len(matrix.index))),
        xaxis_title="Asset",
        yaxis_title="Event Category",
        margin=dict(l=180, r=40, t=70, b=40)
    )

    return fig
