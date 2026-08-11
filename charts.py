import inspect
from pathlib import Path

import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.io as pio


# =========================
# DETETAR NOME DO ATIVO PELO FICHEIRO
# =========================
def detectar_nome_asset():
    asset_names = {
        "main.py": "BTC",
        "sp500.py": "SP500",
        "stoxx600.py": "STOXX600",
        "ftse100.py": "FTSE100",
        "gold.py": "GOLD",
        "dollaramericano.py": "DXY / USD INDEX",
        "dxy.py": "DXY / USD INDEX",
        "euro.py": "EURO",
        "yuan.py": "YUAN",
        "libra.py": "LIBRA / GBP",
        "ssecomposite.py": "SSE COMPOSITE",
    }

    try:
        stack = inspect.stack()

        for frame in stack:
            filename = Path(frame.filename).name

            if filename in asset_names:
                return asset_names[filename]

    except Exception:
        pass

    return "ASSET"


# =========================
# GERAR DASHBOARD / MINI TRADINGVIEW
# =========================
def gerar_dashboard(df, asset_name=None):
    if asset_name is None:
        asset_name = detectar_nome_asset()

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        row_heights=[0.4, 0.25, 0.2, 0.15],
        subplot_titles=[
            asset_name,
            "Volume",
            "RSI / Stoch RSI",
            "MACD"
        ]
    )

    # =========================
    # CANDLESTICK
    # =========================
    fig.add_trace(
        go.Candlestick(
            x=df["snapped_at"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Candlestick",
            hovertext=[
                f"Open: {o:.2f}<br>"
                f"High: {h:.2f}<br>"
                f"Low: {low:.2f}<br>"
                f"Close: {c:.2f}"
                for o, h, low, c in zip(
                    df["open"],
                    df["high"],
                    df["low"],
                    df["close"]
                )
            ],
            hoverinfo="x+text"
        ),
        row=1,
        col=1
    )

    # =========================
    # EMAS
    # =========================
    for span in [9, 26, 50]:
        col = f"ema_{span}"

        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["snapped_at"],
                    y=df[col],
                    mode="lines",
                    name=f"EMA {span}"
                ),
                row=1,
                col=1
            )

    # =========================
    # BOLLINGER BANDS
    # =========================
    if "bb_upper" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df["bb_upper"],
                line=dict(color="rgba(255,0,0,0.3)"),
                name="BB Upper"
            ),
            row=1,
            col=1
        )

    if "bb_lower" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df["bb_lower"],
                fill="tonexty",
                fillcolor="rgba(255,0,0,0.1)",
                line=dict(color="rgba(0,255,0,0.3)"),
                name="BB Lower"
            ),
            row=1,
            col=1
        )

    # =========================
    # VOLUME
    # =========================
    volume_colors = [
        "green" if c >= o else "red"
        for c, o in zip(
            df["close"],
            df["open"]
        )
    ]

    fig.add_trace(
        go.Bar(
            x=df["snapped_at"],
            y=df["volume"],
            marker=dict(
                color=volume_colors,
                line=dict(width=0)
            ),
            opacity=1,
            name="Volume"
        ),
        row=2,
        col=1
    )

    # =========================
    # RSI
    # =========================
    if "rsi" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df["rsi"],
                mode="lines",
                line=dict(color="#1E90FF"),
                name="RSI"
            ),
            row=3,
            col=1
        )

    # =========================
    # STOCH RSI K / D
    # =========================
    if "stoch_rsi_k" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df["stoch_rsi_k"],
                line=dict(color="green"),
                name="%K"
            ),
            row=3,
            col=1
        )

    if "stoch_rsi_d" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df["stoch_rsi_d"],
                line=dict(color="orange"),
                name="%D"
            ),
            row=3,
            col=1
        )

    # =========================
    # LINHAS RSI 80 / 20
    # =========================
    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=[80] * len(df),
            mode="lines",
            line=dict(color="red", dash="dash"),
            showlegend=False
        ),
        row=3,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=[20] * len(df),
            mode="lines",
            line=dict(color="blue", dash="dash"),
            showlegend=False
        ),
        row=3,
        col=1
    )

    # =========================
    # LINHAS RSI 70 / 30
    # =========================
    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=[70] * len(df),
            mode="lines",
            line=dict(color="red", dash="dash"),
            name="Overbought"
        ),
        row=3,
        col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=[30] * len(df),
            mode="lines",
            line=dict(color="green", dash="dash"),
            name="Oversold"
        ),
        row=3,
        col=1
    )

    # =========================
    # MACD
    # =========================
    if "macd" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df["macd"],
                mode="lines",
                name="MACD",
                line=dict(color="blue")
            ),
            row=4,
            col=1
        )

    if "macd_signal" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df["macd_signal"],
                mode="lines",
                name="MACD Signal",
                line=dict(color="red")
            ),
            row=4,
            col=1
        )

    if "macd_percent" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df["macd_percent"],
                mode="lines",
                name="MACD %",
                line=dict(color="purple", dash="dash")
            ),
            row=4,
            col=1
        )

    # =========================
    # MANIPULATION FLAGS
    # =========================
    if "manipulation" in df.columns:
        flags_df = df[df["manipulation"].notnull()]

        if not flags_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=flags_df["snapped_at"],
                    y=flags_df["close"] * 1.02,
                    mode="markers",
                    marker=dict(
                        size=10,
                        color="orange",
                        symbol="triangle-up"
                    ),
                    text=flags_df["manipulation"],
                    textposition="top center",
                    name="Sinal Manipulation"
                ),
                row=1,
                col=1
            )

    # =========================
    # EIXOS
    # =========================
    fig.update_yaxes(
        title_text="Price",
        row=1,
        col=1
    )

    fig.update_yaxes(
        title_text="Volume",
        row=2,
        col=1
    )

    fig.update_yaxes(
        title_text="RSI",
        row=3,
        col=1,
        range=[0, 100]
    )

    fig.update_yaxes(
        title_text="MACD",
        row=4,
        col=1
    )

    fig.update_xaxes(
        rangeslider_visible=False
    )

    # =========================
    # SUBPLOT TITLE STYLE
    # =========================
    fig.update_annotations(
        font=dict(
            size=15,
            color="white"
        )
    )

    # =========================
    # FINAL CONFIGURATION
    # =========================
    fig.update_layout(
        dragmode="pan",
        hovermode="x unified",
        template="plotly_dark",
        height=1600,
        width=1400,
        margin=dict(
            t=90,
            r=40,
            b=50,
            l=70
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=10)
        )
    )

    pio.show(
        fig,
        config={
            "scrollZoom": True,
            "displayModeBar": True
        }
    )

    return fig
