import pandas as pd
import plotly.graph_objects as go


def make_correlation_heatmap(
    corr_df: pd.DataFrame,
    title: str = "Correlation Heatmap",
):
    """Create a heatmap from a correlation matrix."""

    if corr_df.empty:
        return None

    fig = go.Figure(
        data=go.Heatmap(
            z=corr_df.values,
            x=corr_df.columns,
            y=corr_df.index,
            zmin=-1,
            zmax=1,
            colorscale="RdBu",
            reversescale=True,
            colorbar=dict(title="Correlation"),
            text=corr_df.round(2).values,
            texttemplate="%{text}",
            hovertemplate=(
                "Asset X: %{x}<br>"
                "Asset Y: %{y}<br>"
                "Correlation: %{z:.3f}<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=750,
        xaxis_title="Asset",
        yaxis_title="Asset",
    )

    return fig


def make_rolling_correlation_chart(
    rolling_df: pd.DataFrame,
    asset_x: str,
    asset_y: str,
    window: int,
):
    """Create a line chart for rolling correlation."""

    if rolling_df.empty:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=rolling_df["snapped_at"],
            y=rolling_df["rolling_correlation"],
            mode="lines",
            name=f"{asset_x} vs {asset_y}",
        )
    )

    fig.add_hline(y=0, line_dash="dash", opacity=0.5)
    fig.add_hline(y=0.5, line_dash="dot", opacity=0.4)
    fig.add_hline(y=-0.5, line_dash="dot", opacity=0.4)

    fig.update_layout(
        title=f"Rolling Correlation {window}D - {asset_x} vs {asset_y}",
        template="plotly_dark",
        height=600,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Correlation",
        yaxis=dict(range=[-1, 1]),
    )

    return fig


def make_returns_scatter_chart(
    scatter_df: pd.DataFrame,
    asset_x: str,
    asset_y: str,
):
    """Create a scatter plot of returns between two assets."""

    if scatter_df.empty:
        return None

    x_col = f"{asset_x}_return_pct"
    y_col = f"{asset_y}_return_pct"

    if x_col not in scatter_df.columns or y_col not in scatter_df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=scatter_df[x_col],
            y=scatter_df[y_col],
            mode="markers",
            name=f"{asset_x} vs {asset_y}",
            text=scatter_df["snapped_at"].dt.strftime("%Y-%m-%d"),
            hovertemplate=(
                "Date: %{text}<br>"
                f"{asset_x} Return: " + "%{x:.2f}%<br>"
                f"{asset_y} Return: " + "%{y:.2f}%<extra></extra>"
            ),
        )
    )

    fig.add_hline(y=0, line_dash="dash", opacity=0.5)
    fig.add_vline(x=0, line_dash="dash", opacity=0.5)

    fig.update_layout(
        title=f"Daily Returns Scatter - {asset_x} vs {asset_y}",
        template="plotly_dark",
        height=650,
        xaxis_title=f"{asset_x} Daily Return %",
        yaxis_title=f"{asset_y} Daily Return %",
    )

    return fig


def make_base100_multi_asset_chart(
    norm_df: pd.DataFrame,
    selected_assets: list,
    title: str = "Multi-Asset Performance - Base 100",
):
    """Create a multi-asset Base 100 line chart."""

    if norm_df.empty:
        return None

    fig = go.Figure()

    for asset in selected_assets:
        if asset not in norm_df.columns:
            continue

        fig.add_trace(
            go.Scatter(
                x=norm_df["snapped_at"],
                y=norm_df[asset],
                mode="lines",
                name=asset,
            )
        )

    fig.add_hline(y=100, line_dash="dash", opacity=0.5)

    fig.update_layout(
        title=title,
        template="plotly_dark",
        height=650,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Base 100",
    )

    return fig
