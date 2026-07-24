import pandas as pd
import plotly.graph_objects as go



def make_btc_cycle_performance_chart(cycle_df: pd.DataFrame, title: str):
    if cycle_df is None or cycle_df.empty:
        return None

    required_cols = [
        "Halving Event",
        "Drawdown from Halving %",
        "Upside from Halving %"
    ]

    if any(col not in cycle_df.columns for col in required_cols):
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=cycle_df["Halving Event"],
            y=cycle_df["Drawdown from Halving %"],
            name="Drawdown from Halving %"
        )
    )

    fig.add_trace(
        go.Bar(
            x=cycle_df["Halving Event"],
            y=cycle_df["Upside from Halving %"],
            name="Upside from Halving %"
        )
    )

    if "Drawdown Top to Bottom %" in cycle_df.columns:
        fig.add_trace(
            go.Bar(
                x=cycle_df["Halving Event"],
                y=cycle_df["Drawdown Top to Bottom %"],
                name="Drawdown Top to Bottom %"
            )
        )

    if "Upside Bottom to Top %" in cycle_df.columns:
        fig.add_trace(
            go.Bar(
                x=cycle_df["Halving Event"],
                y=cycle_df["Upside Bottom to Top %"],
                name="Upside Bottom to Top %"
            )
        )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=520,
        barmode="group",
        xaxis_title="Halving Event",
        yaxis_title="Return (%)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=80, b=90)
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(220,220,220,0.55)"
    )

    return fig



def make_btc_cycle_timing_chart(cycle_df: pd.DataFrame, title: str):
    if cycle_df is None or cycle_df.empty:
        return None

    required_cols = [
        "Halving Event",
        "Days to Bottom",
        "Days to Top",
        "Cycle Duration"
    ]

    if any(col not in cycle_df.columns for col in required_cols):
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=cycle_df["Halving Event"],
            y=cycle_df["Days to Bottom"],
            name="Days to Bottom"
        )
    )

    fig.add_trace(
        go.Bar(
            x=cycle_df["Halving Event"],
            y=cycle_df["Days to Top"],
            name="Days to Top"
        )
    )

    if "Days Down" in cycle_df.columns:
        fig.add_trace(
            go.Bar(
                x=cycle_df["Halving Event"],
                y=cycle_df["Days Down"],
                name="Days Down"
            )
        )

    if "Days Up" in cycle_df.columns:
        fig.add_trace(
            go.Bar(
                x=cycle_df["Halving Event"],
                y=cycle_df["Days Up"],
                name="Days Up"
            )
        )

    fig.add_trace(
        go.Bar(
            x=cycle_df["Halving Event"],
            y=cycle_df["Cycle Duration"],
            name="Cycle Duration"
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=520,
        barmode="group",
        xaxis_title="Halving Event",
        yaxis_title="Days",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=80, b=90)
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(220,220,220,0.55)"
    )

    return fig



def make_btc_validated_cycle_performance_chart(cycle_df: pd.DataFrame):
    if cycle_df is None or cycle_df.empty:
        return None

    plot_df = cycle_df.copy()

    fig = go.Figure()

    if "Drawdown %" in plot_df.columns:
        fig.add_trace(
            go.Bar(
                x=plot_df["Cycle"],
                y=plot_df["Drawdown %"],
                name="Drawdown %"
            )
        )

    if "Upside %" in plot_df.columns:
        fig.add_trace(
            go.Bar(
                x=plot_df["Cycle"],
                y=plot_df["Upside %"],
                name="Upside %"
            )
        )

    fig.update_layout(
        title="BTC Historical Benchmark Performance",
        template="plotly_dark",
        height=520,
        barmode="group",
        xaxis_title="Cycle",
        yaxis_title="Return (%)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=80, b=100)
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(220,220,220,0.55)"
    )

    return fig



def make_btc_validated_cycle_timing_chart(cycle_df: pd.DataFrame):
    if cycle_df is None or cycle_df.empty:
        return None

    plot_df = cycle_df.copy()

    fig = go.Figure()

    if "Days Down" in plot_df.columns:
        fig.add_trace(
            go.Bar(
                x=plot_df["Cycle"],
                y=plot_df["Days Down"],
                name="Days Down"
            )
        )

    if "Days Up" in plot_df.columns:
        fig.add_trace(
            go.Bar(
                x=plot_df["Cycle"],
                y=plot_df["Days Up"],
                name="Days Up"
            )
        )

    if "Days Bottom to Halving" in plot_df.columns:
        fig.add_trace(
            go.Bar(
                x=plot_df["Cycle"],
                y=plot_df["Days Bottom to Halving"],
                name="Days Bottom to Halving"
            )
        )

    if "Days Halving to Top" in plot_df.columns:
        fig.add_trace(
            go.Bar(
                x=plot_df["Cycle"],
                y=plot_df["Days Halving to Top"],
                name="Days Halving to Top"
            )
        )

    fig.update_layout(
        title="BTC Historical Benchmark Timing",
        template="plotly_dark",
        height=520,
        barmode="group",
        xaxis_title="Cycle",
        yaxis_title="Days",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=80, b=100)
    )

    return fig



def make_btc_halving_forward_returns_chart(halving_df: pd.DataFrame):
    if halving_df is None or halving_df.empty:
        return None

    if "Halving Event" not in halving_df.columns:
        return None

    return_cols = [
        col for col in [
            "Return +30D %",
            "Return +90D %",
            "Return +180D %",
            "Return +365D %",
            "Return +730D %",
            "Return +1095D %",
        ]
        if col in halving_df.columns
    ]

    if not return_cols:
        return None

    plot_df = halving_df.copy()

    for col in return_cols:
        plot_df[col] = pd.to_numeric(plot_df[col], errors="coerce")

    fig = go.Figure()

    for col in return_cols:
        fig.add_trace(
            go.Bar(
                x=plot_df["Halving Event"],
                y=plot_df[col],
                name=col.replace("Return ", "")
            )
        )

    fig.update_layout(
        title="BTC Halving Forward Returns",
        template="plotly_dark",
        height=520,
        barmode="group",
        xaxis_title="Halving Event",
        yaxis_title="Forward Return (%)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=80, b=100)
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(220,220,220,0.55)"
    )

    return fig



def make_btc_halving_window_extremes_chart(halving_df: pd.DataFrame):
    if halving_df is None or halving_df.empty:
        return None

    required_cols = [
        "Halving Event",
        "Max Drawdown from Halving %",
        "Max Upside from Halving %"
    ]

    if any(col not in halving_df.columns for col in required_cols):
        return None

    plot_df = halving_df.copy()
    plot_df["Max Drawdown from Halving %"] = pd.to_numeric(
        plot_df["Max Drawdown from Halving %"],
        errors="coerce"
    )
    plot_df["Max Upside from Halving %"] = pd.to_numeric(
        plot_df["Max Upside from Halving %"],
        errors="coerce"
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=plot_df["Halving Event"],
            y=plot_df["Max Drawdown from Halving %"],
            name="Max Drawdown from Halving %"
        )
    )

    fig.add_trace(
        go.Bar(
            x=plot_df["Halving Event"],
            y=plot_df["Max Upside from Halving %"],
            name="Max Upside from Halving %"
        )
    )

    fig.update_layout(
        title="BTC Halving Window Extremes",
        template="plotly_dark",
        height=520,
        barmode="group",
        xaxis_title="Halving Event",
        yaxis_title="Return (%)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        ),
        margin=dict(l=20, r=20, t=80, b=100)
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(220,220,220,0.55)"
    )

    return fig
