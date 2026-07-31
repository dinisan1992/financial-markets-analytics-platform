import pandas as pd
import plotly.graph_objects as go


REGIME_COLORS = {
    "Risk-On": "#2E8B57",
    "Risk-Off": "#C44536",
    "High Volatility": "#D97706",
    "Dollar Strength": "#3973B8",
    "Yield Pressure": "#8A5A44",
    "Commodity Shock": "#A05A2C",
    "Financial Stress": "#B02A37",
    "Neutral": "#7A7A7A",
}


def make_market_regime_timeline(regime_df: pd.DataFrame):
    if regime_df is None or regime_df.empty:
        return None

    frame = regime_df.copy()
    first_price = frame["SP500"].dropna().iloc[0]
    frame["SP500_base100"] = frame["SP500"] / first_price * 100

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=frame["snapped_at"],
            y=frame["SP500_base100"],
            mode="lines",
            name="S&P 500 Base 100",
            line={"color": "#D7DCE2", "width": 2},
        )
    )

    for regime in frame["market_regime"].dropna().unique():
        part = frame[frame["market_regime"] == regime]
        color = REGIME_COLORS.get(regime, "#8B8B8B")
        figure.add_trace(
            go.Scatter(
                x=part["snapped_at"],
                y=part["SP500_base100"],
                mode="markers",
                name=regime,
                marker={"size": 5, "color": color},
                hovertemplate=f"{regime}<br>%{{x|%Y-%m-%d}}<br>%{{y:.2f}}<extra></extra>",
            )
        )

    figure.update_layout(
        title="Market Regime Timeline",
        template="plotly_dark",
        height=650,
        hovermode="closest",
        xaxis_title="Date",
        yaxis_title="S&P 500 Base 100",
    )
    return figure


def make_regime_distribution_chart(summary_df: pd.DataFrame):
    if summary_df is None or summary_df.empty:
        return None

    colors = [REGIME_COLORS.get(value, "#8B8B8B") for value in summary_df["market_regime"]]
    figure = go.Figure(
        go.Bar(
            x=summary_df["market_regime"],
            y=summary_df["Observations"],
            marker_color=colors,
            hovertemplate="%{x}: %{y} observations<extra></extra>",
        )
    )
    figure.update_layout(
        title="Regime Distribution",
        template="plotly_dark",
        height=480,
        xaxis_title="Regime",
        yaxis_title="Observations",
    )
    return figure
