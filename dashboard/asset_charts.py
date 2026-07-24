import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================
# EVENT HELPERS
# =========================

def _find_first_existing_column(df: pd.DataFrame, candidates: list[str]):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _get_volume_column(df: pd.DataFrame):
    """
    Finds the best available volume column across different asset tables.
    BTC usually uses total_volume, while some market assets may use volume.
    """
    for col in [
        "total_volume",
        "volume",
        "Volume",
        "vol",
        "trading_volume"
    ]:
        if col in df.columns and pd.to_numeric(df[col], errors="coerce").notna().sum() > 0:
            return col

    return None


def _standardize_event_overlay_df(events_df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes events loaded from the source tables:
    - bitcoin_historical_events
    - world_historical_events

    Returns standard columns:
    - event_date
    - event_title
    - event_description
    - event_source
    """
    if events_df is None or events_df.empty:
        return pd.DataFrame(columns=[
            "event_date", "event_title", "event_description", "event_source"
        ])

    df = events_df.copy()

    date_col = _find_first_existing_column(df, [
        "event_date", "date", "snapped_at", "event_datetime", "datetime"
    ])
    title_col = _find_first_existing_column(df, [
        "title", "event_title", "event", "headline", "name"
    ])
    desc_col = _find_first_existing_column(df, [
        "description", "details", "summary", "event_description"
    ])
    source_col = _find_first_existing_column(df, [
        "source", "category", "event_type", "table_source"
    ])

    if date_col is None:
        return pd.DataFrame(columns=[
            "event_date", "event_title", "event_description", "event_source"
        ])

    out = pd.DataFrame()
    out["event_date"] = pd.to_datetime(df[date_col], errors="coerce")
    out["event_title"] = df[title_col].astype(str) if title_col else "Event"
    out["event_description"] = df[desc_col].astype(str) if desc_col else ""
    out["event_source"] = df[source_col].astype(str) if source_col else ""

    out = out.dropna(subset=["event_date"]).copy()
    out["event_date"] = out["event_date"].dt.normalize()

    # Aggregate same-day events to avoid excessive labels
    out = (
        out.groupby("event_date", as_index=False)
        .agg({
            "event_title": lambda x: " | ".join(pd.Series(x).dropna().astype(str).unique()[:3]),
            "event_description": lambda x: " | ".join(pd.Series(x).dropna().astype(str).unique()[:2]),
            "event_source": lambda x: " | ".join(pd.Series(x).dropna().astype(str).unique()[:2]),
        })
        .sort_values("event_date")
        .reset_index(drop=True)
    )

    return out


def _shorten_text(text: str, max_len: int = 32) -> str:
    text = str(text) if text is not None else ""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + "..."


def _add_event_overlay(
    fig,
    price_df: pd.DataFrame,
    events_df: pd.DataFrame,
    row: int = 1,
    col: int = 1,
    max_visible_labels: int = 10
):
    """
    Adds events to the main chart while reducing overlap:
    - all events keep marker + hover
    - only selected events keep visible labels
    - labels are staggered across multiple levels
    """
    if events_df is None or events_df.empty or price_df.empty:
        return fig

    ev = _standardize_event_overlay_df(events_df)
    if ev.empty:
        return fig

    price_base_col = "high" if "high" in price_df.columns else "close"
    y_max = float(price_df[price_base_col].max())
    marker_y = y_max * 1.01

    ev["marker_y"] = marker_y

    # Mostrar label apenas em parte dos eventos
    ev["show_label"] = False
    if len(ev) <= max_visible_labels:
        ev["show_label"] = True
    else:
        idx = np.linspace(0, len(ev) - 1, max_visible_labels, dtype=int)
        ev.loc[idx, "show_label"] = True

    # Alternating vertical levels to reduce overlap
    label_levels = [1.08, 1.14, 1.20, 1.26]
    ev["label_y"] = [
        y_max * label_levels[i % len(label_levels)]
        for i in range(len(ev))
    ]

    ev["short_title"] = ev["event_title"].apply(lambda x: _shorten_text(x, 28))

    # markers de todos os eventos
    fig.add_trace(
        go.Scatter(
            x=ev["event_date"],
            y=ev["marker_y"],
            mode="markers",
            name="Timeline Events",
            marker=dict(
                symbol="diamond",
                size=7,
                color="yellow",
                line=dict(width=1, color="black")
            ),
            customdata=np.stack([
                ev["event_title"],
                ev["event_description"],
                ev["event_source"]
            ], axis=-1),
            hovertemplate=(
                "<b>Event</b><br>"
                "Date: %{x|%Y-%m-%d}<br>"
                "Title: %{customdata[0]}<br>"
                "Description: %{customdata[1]}<br>"
                "Source: %{customdata[2]}"
                "<extra></extra>"
            ),
            showlegend=True
        ),
        row=row,
        col=col
    )

    # rows verticais + labels apenas para alguns eventos
    visible_labels = ev[ev["show_label"]].copy()

    for _, event in visible_labels.iterrows():
        fig.add_vline(
            x=event["event_date"],
            line_width=1,
            line_dash="dot",
            line_color="rgba(255, 215, 0, 0.35)",
            row=row,
            col=col
        )

        fig.add_annotation(
            x=event["event_date"],
            y=event["label_y"],
            text=event["short_title"],
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor="rgba(255,215,0,0.7)",
            ax=0,
            ay=-18,
            bgcolor="rgba(25,25,25,0.88)",
            bordercolor="rgba(255,215,0,0.65)",
            borderwidth=1,
            font=dict(size=9, color="white"),
            row=row,
            col=col
        )

    return fig
# =========================
# PRICE / TECHNICAL DASHBOARD
# =========================

def make_price_chart(
    df: pd.DataFrame,
    display_name: str,
    show_emas: bool = True,
    show_bollinger: bool = True,
    show_flags: bool = True,
    selected_emas=None,
    chart_height: int = 900,
    show_volume: bool = True,
    show_rsi: bool = True,
    show_stoch_rsi: bool = True,
    show_macd: bool = True,
    events=None
):
    """
    Main TradingView-style technical chart:
    - Candlestick
    - EMAs
    - Bollinger Bands
    - Flags suspeitas
    - Volume
    - RSI
    - Stochastic RSI
    - MACD
    - Eventos vindos da base de data
    """

    plot_df = df.copy()

    if selected_emas is None:
        selected_emas = [9, 20, 50, 100, 200]

    if "snapped_at" not in plot_df.columns:
        return None

    plot_df["snapped_at"] = pd.to_datetime(plot_df["snapped_at"], errors="coerce")
    plot_df = plot_df.dropna(subset=["snapped_at"]).copy()

    if plot_df.empty:
        return None

    volume_col = _get_volume_column(plot_df)

    has_volume = (
        show_volume
        and volume_col is not None
        and pd.to_numeric(plot_df[volume_col], errors="coerce").notna().sum() > 0
    )

    has_rsi = (
        show_rsi
        and "rsi" in plot_df.columns
        and plot_df["rsi"].notna().sum() > 0
    )

    has_stoch = (
        show_stoch_rsi
        and "stoch_rsi_k" in plot_df.columns
        and "stoch_rsi_d" in plot_df.columns
        and plot_df["stoch_rsi_k"].notna().sum() > 0
        and plot_df["stoch_rsi_d"].notna().sum() > 0
    )

    has_macd = (
        show_macd
        and "macd" in plot_df.columns
        and "macd_signal" in plot_df.columns
        and plot_df["macd"].notna().sum() > 0
        and plot_df["macd_signal"].notna().sum() > 0
    )

    subplot_specs = [[{"secondary_y": False}]]
    row_heights = [0.52]

    if has_volume:
        subplot_specs.append([{"secondary_y": False}])
        row_heights.append(0.12)

    if has_rsi:
        subplot_specs.append([{"secondary_y": False}])
        row_heights.append(0.12)

    if has_stoch:
        subplot_specs.append([{"secondary_y": False}])
        row_heights.append(0.12)

    if has_macd:
        subplot_specs.append([{"secondary_y": False}])
        row_heights.append(0.12)

    fig = make_subplots(
        rows=len(subplot_specs),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.025,
        row_heights=row_heights,
        specs=subplot_specs
    )

    current_row = 1

    fig.add_trace(
        go.Candlestick(
            x=plot_df["snapped_at"],
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            name="OHLC"
        ),
        row=current_row,
        col=1
    )

    if show_emas:
        for ema in selected_emas:
            col = f"ema_{ema}"

            if col in plot_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=plot_df["snapped_at"],
                        y=plot_df[col],
                        mode="lines",
                        name=f"EMA {ema}",
                        line=dict(width=1.2)
                    ),
                    row=current_row,
                    col=1
                )

    if show_bollinger:
        if "bb_upper" in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df["snapped_at"],
                    y=plot_df["bb_upper"],
                    mode="lines",
                    name="BB Upper",
                    line=dict(width=1, dash="dot")
                ),
                row=current_row,
                col=1
            )

        if "bb_lower" in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df["snapped_at"],
                    y=plot_df["bb_lower"],
                    mode="lines",
                    name="BB Lower",
                    line=dict(width=1, dash="dot"),
                    fill="tonexty"
                ),
                row=current_row,
                col=1
            )

    if show_flags:
        pump_dump_df = (
            plot_df[plot_df["possible_pump_dump"]].copy()
            if "possible_pump_dump" in plot_df.columns
            else pd.DataFrame()
        )

        spoofing_df = (
            plot_df[plot_df["possible_spoofing"]].copy()
            if "possible_spoofing" in plot_df.columns
            else pd.DataFrame()
        )

        if all(
            col in plot_df.columns
            for col in ["volume_spike", "possible_pump_dump", "possible_spoofing"]
        ):
            volume_spike_df = plot_df[
                (plot_df["volume_spike"])
                & (~plot_df["possible_pump_dump"])
                & (~plot_df["possible_spoofing"])
            ].copy()
        elif "volume_spike" in plot_df.columns:
            volume_spike_df = plot_df[plot_df["volume_spike"]].copy()
        else:
            volume_spike_df = pd.DataFrame()

        if not pump_dump_df.empty:
            custom_cols = ["price_change_pct", "volume_zscore", "manipulation_reason"]
            for col in custom_cols:
                if col not in pump_dump_df.columns:
                    pump_dump_df[col] = np.nan if col != "manipulation_reason" else ""

            fig.add_trace(
                go.Scatter(
                    x=pump_dump_df["snapped_at"],
                    y=pump_dump_df["high"] * 1.02,
                    mode="markers",
                    name="Possible Pump/Dump",
                    marker=dict(symbol="triangle-up", size=12, color="red"),
                    customdata=pump_dump_df[custom_cols],
                    hovertemplate=(
                        "Date: %{x}<br>"
                        "Price Change: %{customdata[0]:.2f}%<br>"
                        "Volume Z-Score: %{customdata[1]:.2f}<br>"
                        "Reason: %{customdata[2]}<extra></extra>"
                    )
                ),
                row=current_row,
                col=1
            )

        if not spoofing_df.empty:
            custom_cols = ["price_change_pct", "volume_zscore", "manipulation_reason"]
            for col in custom_cols:
                if col not in spoofing_df.columns:
                    spoofing_df[col] = np.nan if col != "manipulation_reason" else ""

            fig.add_trace(
                go.Scatter(
                    x=spoofing_df["snapped_at"],
                    y=spoofing_df["high"] * 1.015,
                    mode="markers",
                    name="Possible Spoofing",
                    marker=dict(symbol="diamond", size=11, color="orange"),
                    customdata=spoofing_df[custom_cols],
                    hovertemplate=(
                        "Date: %{x}<br>"
                        "Price Change: %{customdata[0]:.2f}%<br>"
                        "Volume Z-Score: %{customdata[1]:.2f}<br>"
                        "Reason: %{customdata[2]}<extra></extra>"
                    )
                ),
                row=current_row,
                col=1
            )

        if not volume_spike_df.empty:
            custom_cols = ["price_change_pct", "volume_zscore", "manipulation_reason"]
            for col in custom_cols:
                if col not in volume_spike_df.columns:
                    volume_spike_df[col] = np.nan if col != "manipulation_reason" else ""

            fig.add_trace(
                go.Scatter(
                    x=volume_spike_df["snapped_at"],
                    y=volume_spike_df["high"] * 1.01,
                    mode="markers",
                    name="Volume Spike",
                    marker=dict(symbol="circle", size=8, color="yellow"),
                    customdata=volume_spike_df[custom_cols],
                    hovertemplate=(
                        "Date: %{x}<br>"
                        "Price Change: %{customdata[0]:.2f}%<br>"
                        "Volume Z-Score: %{customdata[1]:.2f}<br>"
                        "Reason: %{customdata[2]}<extra></extra>"
                    )
                ),
                row=current_row,
                col=1
            )

    fig.update_yaxes(title_text="Price", row=current_row, col=1)

    if has_volume:
        current_row += 1

        if "close" in plot_df.columns and "open" in plot_df.columns:
            volume_colors = np.where(
                plot_df["close"] >= plot_df["open"],
                "rgba(0, 200, 120, 0.65)",
                "rgba(255, 80, 80, 0.65)"
            )
        else:
            volume_colors = "rgba(120, 120, 120, 0.65)"

        fig.add_trace(
            go.Bar(
                x=plot_df["snapped_at"],
                y=pd.to_numeric(plot_df[volume_col], errors="coerce"),
                name="Volume",
                marker=dict(color=volume_colors, line=dict(width=0)),
                opacity=0.9
            ),
            row=current_row,
            col=1
        )

        volume_sma_col = _find_first_existing_column(
            plot_df,
            ["volume_sma_30", "volume_sma_20", "volume_sma_9"]
        )

        if volume_sma_col is not None:
            fig.add_trace(
                go.Scatter(
                    x=plot_df["snapped_at"],
                    y=pd.to_numeric(plot_df[volume_sma_col], errors="coerce"),
                    mode="lines",
                    name=volume_sma_col.replace("_", " ").upper(),
                    line=dict(width=1.5, color="rgba(255, 215, 0, 0.95)")
                ),
                row=current_row,
                col=1
            )

        fig.update_yaxes(title_text="Volume", row=current_row, col=1)

    if has_rsi:
        current_row += 1

        rsi_df = plot_df[["snapped_at", "rsi"]].copy()
        rsi_df["rsi"] = pd.to_numeric(rsi_df["rsi"], errors="coerce")
        rsi_df = rsi_df.replace([np.inf, -np.inf], np.nan)
        rsi_df = rsi_df.dropna(subset=["snapped_at", "rsi"]).copy()

        if not rsi_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=rsi_df["snapped_at"],
                    y=rsi_df["rsi"],
                    mode="lines",
                    name="RSI",
                    line=dict(width=1.5, color="rgba(120, 130, 255, 1)")
                ),
                row=current_row,
                col=1
            )

            fig.add_hline(y=70, line_dash="dash", line_color="rgba(255, 80, 80, 0.75)", row=current_row, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="rgba(0, 200, 120, 0.75)", row=current_row, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="rgba(220, 220, 220, 0.45)", row=current_row, col=1)

            fig.update_yaxes(
                title_text="RSI",
                range=[0, 100],
                tickvals=[0, 30, 50, 70, 100],
                row=current_row,
                col=1
            )

    if has_stoch:
        current_row += 1

        stoch_df = plot_df[["snapped_at", "stoch_rsi_k", "stoch_rsi_d"]].copy()
        stoch_df["stoch_rsi_k"] = pd.to_numeric(stoch_df["stoch_rsi_k"], errors="coerce")
        stoch_df["stoch_rsi_d"] = pd.to_numeric(stoch_df["stoch_rsi_d"], errors="coerce")
        stoch_df = stoch_df.replace([np.inf, -np.inf], np.nan)
        stoch_df = stoch_df.dropna(subset=["snapped_at", "stoch_rsi_k", "stoch_rsi_d"]).copy()

        if not stoch_df.empty:
            if (
                stoch_df["stoch_rsi_k"].max() <= 1.5
                and stoch_df["stoch_rsi_d"].max() <= 1.5
            ):
                stoch_df["stoch_rsi_k"] = stoch_df["stoch_rsi_k"] * 100
                stoch_df["stoch_rsi_d"] = stoch_df["stoch_rsi_d"] * 100

            stoch_df["stoch_rsi_k"] = stoch_df["stoch_rsi_k"].clip(0, 100)
            stoch_df["stoch_rsi_d"] = stoch_df["stoch_rsi_d"].clip(0, 100)

            stoch_df["stoch_rsi_k_smooth"] = stoch_df["stoch_rsi_k"].rolling(window=3, min_periods=1).mean()
            stoch_df["stoch_rsi_d_smooth"] = stoch_df["stoch_rsi_d"].rolling(window=3, min_periods=1).mean()

            fig.add_trace(
                go.Scatter(
                    x=stoch_df["snapped_at"],
                    y=stoch_df["stoch_rsi_k_smooth"],
                    mode="lines",
                    name="Stoch RSI %K",
                    line=dict(width=1.5, color="rgba(80, 160, 255, 1)")
                ),
                row=current_row,
                col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=stoch_df["snapped_at"],
                    y=stoch_df["stoch_rsi_d_smooth"],
                    mode="lines",
                    name="Stoch RSI %D",
                    line=dict(width=1.5, color="rgba(255, 170, 60, 1)")
                ),
                row=current_row,
                col=1
            )

            fig.add_hline(y=80, line_dash="dash", line_color="rgba(255, 80, 80, 0.75)", row=current_row, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="rgba(0, 200, 120, 0.75)", row=current_row, col=1)
            fig.add_hline(y=50, line_dash="dot", line_color="rgba(220, 220, 220, 0.45)", row=current_row, col=1)

            fig.update_yaxes(
                title_text="Stoch",
                range=[0, 100],
                tickvals=[0, 20, 50, 80, 100],
                row=current_row,
                col=1
            )

    if has_macd:
        current_row += 1

        macd_df = plot_df[["snapped_at", "macd", "macd_signal"]].copy()
        macd_df["macd"] = pd.to_numeric(macd_df["macd"], errors="coerce")
        macd_df["macd_signal"] = pd.to_numeric(macd_df["macd_signal"], errors="coerce")

        if "macd_hist" in plot_df.columns:
            macd_df["macd_hist"] = pd.to_numeric(plot_df["macd_hist"], errors="coerce")
        else:
            macd_df["macd_hist"] = macd_df["macd"] - macd_df["macd_signal"]

        macd_df = macd_df.replace([np.inf, -np.inf], np.nan)
        macd_df = macd_df.dropna(subset=["snapped_at", "macd", "macd_signal", "macd_hist"]).copy()

        if not macd_df.empty:
            hist_colors = np.where(
                macd_df["macd_hist"] >= 0,
                "rgba(0, 200, 120, 0.85)",
                "rgba(255, 80, 80, 0.85)"
            )

            fig.add_trace(
                go.Bar(
                    x=macd_df["snapped_at"],
                    y=macd_df["macd_hist"],
                    name="MACD Histogram",
                    marker=dict(color=hist_colors, line=dict(width=0)),
                    opacity=0.9
                ),
                row=current_row,
                col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=macd_df["snapped_at"],
                    y=macd_df["macd"],
                    mode="lines",
                    name="MACD",
                    line=dict(width=1.5, color="rgba(80, 160, 255, 1)")
                ),
                row=current_row,
                col=1
            )

            fig.add_trace(
                go.Scatter(
                    x=macd_df["snapped_at"],
                    y=macd_df["macd_signal"],
                    mode="lines",
                    name="MACD Signal",
                    line=dict(width=1.5, color="rgba(255, 190, 80, 1)")
                ),
                row=current_row,
                col=1
            )

            fig.add_hline(
                y=0,
                line_dash="dash",
                line_color="rgba(220, 220, 220, 0.55)",
                row=current_row,
                col=1
            )

            fig.update_yaxes(title_text="MACD", row=current_row, col=1)

    if events is not None and isinstance(events, pd.DataFrame) and not events.empty:
        min_date = plot_df["snapped_at"].min()
        max_date = plot_df["snapped_at"].max()

        events_df = events.copy()

        if "event_date" in events_df.columns:
            events_df["event_date"] = pd.to_datetime(events_df["event_date"], errors="coerce")
            events_df = events_df.dropna(subset=["event_date"]).copy()

            events_df = events_df[
                (events_df["event_date"] >= min_date)
                & (events_df["event_date"] <= max_date)
            ].copy()

            max_labeled_events = 40

            for idx, (_, event) in enumerate(events_df.iterrows()):
                event_date = pd.to_datetime(event.get("event_date"), errors="coerce")

                if pd.isna(event_date):
                    continue

                event_title = str(event.get("event_title", "Event"))
                event_category = str(event.get("event_category", "Uncategorized"))
                event_description = str(event.get("event_description", ""))
                source_table = str(event.get("event_source_table", ""))

                if source_table == "bitcoin_historical_events":
                    color = "rgba(255, 215, 0, 0.80)"
                elif source_table == "world_historical_events":
                    color = "rgba(255, 255, 255, 0.60)"
                else:
                    color = "rgba(255, 255, 255, 0.45)"

                fig.add_vline(
                    x=event_date,
                    line_width=1,
                    line_dash="dot",
                    line_color=color,
                    row=1,
                    col=1
                )

                if idx < max_labeled_events:
                    fig.add_annotation(
                        x=event_date,
                        y=1.02,
                        xref="x",
                        yref="paper",
                        text=event_title[:24],
                        showarrow=True,
                        arrowhead=2,
                        ax=0,
                        ay=-25,
                        font=dict(size=9, color="white"),
                        bgcolor="rgba(0,0,0,0.70)",
                        bordercolor=color,
                        borderwidth=1,
                        hovertext=(
                            f"<b>{event_title}</b><br>"
                            f"Category: {event_category}<br>"
                            f"Date: {event_date.date()}<br>"
                            f"Source: {source_table}<br>"
                            f"{event_description}"
                        )
                    )

    fig.update_layout(
        title=f"{display_name} - Technical Dashboard",
        template="plotly_dark",
        height=chart_height,
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        margin=dict(l=60, r=40, t=110, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.08,
            xanchor="left",
            x=0,
            font=dict(size=9)
        )
    )

    for row in range(1, current_row + 1):
        fig.update_xaxes(rangeslider_visible=False, row=row, col=1)

    fig.update_xaxes(title_text="Date", row=current_row, col=1)

    return fig


# =========================
# LINE CHART
# =========================

def make_asset_line_chart(df: pd.DataFrame, display_name: str):
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df["close"],
            mode="lines",
            name=display_name
        )
    )

    fig.update_layout(
        title=f"{display_name} - Line Chart",
        template="plotly_dark",
        height=520,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Price",
        margin=dict(l=20, r=20, t=60, b=40)
    )

    return fig


# =========================
# VOLUME CHARTS
# =========================

def make_volume_chart(df: pd.DataFrame, display_name: str):
    volume_col = _get_volume_column(df)

    if volume_col is None:
        return None

    if pd.to_numeric(df[volume_col], errors="coerce").notna().sum() == 0:
        return None

    plot_df = df.copy()
    plot_df[volume_col] = pd.to_numeric(plot_df[volume_col], errors="coerce")

    if "close" in plot_df.columns and "open" in plot_df.columns:
        volume_colors = np.where(
            plot_df["close"] >= plot_df["open"],
            "rgba(0, 200, 120, 0.75)",
            "rgba(255, 80, 80, 0.75)"
        )
    else:
        volume_colors = "rgba(120, 120, 120, 0.75)"

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=plot_df["snapped_at"],
            y=plot_df[volume_col],
            name="Volume",
            marker=dict(
                color=volume_colors,
                line=dict(width=0)
            ),
            opacity=0.95
        )
    )

    volume_sma_col = _find_first_existing_column(
        plot_df,
        ["volume_sma_30", "volume_sma_20", "volume_sma_9"]
    )

    if volume_sma_col is not None:
        fig.add_trace(
            go.Scatter(
                x=plot_df["snapped_at"],
                y=pd.to_numeric(plot_df[volume_sma_col], errors="coerce"),
                mode="lines",
                name=volume_sma_col.replace("_", " ").upper(),
                line=dict(
                    width=2,
                    color="rgba(255, 215, 0, 0.95)"
                )
            )
        )

    fig.update_layout(
        title=f"{display_name} - Volume",
        template="plotly_dark",
        height=420,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Volume",
        bargap=0,
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )

    return fig

def make_volume_zscore_chart(df: pd.DataFrame, display_name: str):
    if "volume_zscore" not in df.columns or df["volume_zscore"].notna().sum() == 0:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df["volume_zscore"],
            mode="lines",
            name="Volume Z-Score",
            line=dict(
                width=2,
                color="rgba(255, 215, 0, 0.95)"
            )
        )
    )

    fig.add_hline(
        y=2.5,
        line_dash="dash",
        line_color="rgba(255, 80, 80, 0.75)"
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(220, 220, 220, 0.45)"
    )

    fig.update_layout(
        title=f"{display_name} - Volume Z-Score",
        template="plotly_dark",
        height=430,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Z-Score",
        margin=dict(l=20, r=20, t=60, b=40)
    )

    return fig


# =========================
# MOMENTUM CHARTS
# =========================

def make_rsi_chart(df: pd.DataFrame, display_name: str):
    if "rsi" not in df.columns:
        return None

    plot_df = df[["snapped_at", "rsi"]].copy()
    plot_df["rsi"] = pd.to_numeric(plot_df["rsi"], errors="coerce")
    plot_df = plot_df.replace([np.inf, -np.inf], np.nan)
    plot_df = plot_df.dropna(subset=["snapped_at", "rsi"]).copy()

    if plot_df.empty:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df["rsi"],
            mode="lines",
            name="RSI",
            line=dict(
                width=2,
                color="rgba(120, 130, 255, 1)"
            )
        )
    )

    fig.add_hrect(
        y0=70,
        y1=100,
        fillcolor="rgba(255, 80, 80, 0.08)",
        line_width=0
    )

    fig.add_hrect(
        y0=0,
        y1=30,
        fillcolor="rgba(0, 200, 120, 0.08)",
        line_width=0
    )

    fig.add_hline(
        y=70,
        line_dash="dash",
        line_color="rgba(255, 80, 80, 0.75)"
    )

    fig.add_hline(
        y=30,
        line_dash="dash",
        line_color="rgba(0, 200, 120, 0.75)"
    )

    fig.add_hline(
        y=50,
        line_dash="dot",
        line_color="rgba(220, 220, 220, 0.45)"
    )

    fig.update_layout(
        title=f"{display_name} - RSI",
        template="plotly_dark",
        height=360,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="RSI",
        yaxis=dict(
            range=[0, 100],
            tickmode="array",
            tickvals=[0, 30, 50, 70, 100]
        ),
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )

    return fig


def make_stoch_rsi_chart(df: pd.DataFrame, display_name: str):
    if "stoch_rsi_k" not in df.columns or "stoch_rsi_d" not in df.columns:
        return None

    plot_df = df[["snapped_at", "stoch_rsi_k", "stoch_rsi_d"]].copy()

    plot_df["stoch_rsi_k"] = pd.to_numeric(plot_df["stoch_rsi_k"], errors="coerce")
    plot_df["stoch_rsi_d"] = pd.to_numeric(plot_df["stoch_rsi_d"], errors="coerce")

    plot_df = plot_df.replace([np.inf, -np.inf], np.nan)
    plot_df = plot_df.dropna(
        subset=["snapped_at", "stoch_rsi_k", "stoch_rsi_d"]
    ).copy()

    if plot_df.empty:
        return None

    if plot_df["stoch_rsi_k"].max() <= 1.5 and plot_df["stoch_rsi_d"].max() <= 1.5:
        plot_df["stoch_rsi_k"] = plot_df["stoch_rsi_k"] * 100
        plot_df["stoch_rsi_d"] = plot_df["stoch_rsi_d"] * 100

    plot_df["stoch_rsi_k"] = plot_df["stoch_rsi_k"].clip(0, 100)
    plot_df["stoch_rsi_d"] = plot_df["stoch_rsi_d"].clip(0, 100)

    plot_df["stoch_rsi_k_smooth"] = plot_df["stoch_rsi_k"].rolling(
        window=3,
        min_periods=1
    ).mean()

    plot_df["stoch_rsi_d_smooth"] = plot_df["stoch_rsi_d"].rolling(
        window=3,
        min_periods=1
    ).mean()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df["stoch_rsi_k_smooth"],
            mode="lines",
            name="Stoch RSI %K",
            line=dict(
                width=2,
                color="rgba(80, 160, 255, 1)"
            )
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df["stoch_rsi_d_smooth"],
            mode="lines",
            name="Stoch RSI %D",
            line=dict(
                width=2,
                color="rgba(255, 170, 60, 1)"
            )
        )
    )

    fig.add_hrect(
        y0=80,
        y1=100,
        fillcolor="rgba(255, 80, 80, 0.08)",
        line_width=0
    )

    fig.add_hrect(
        y0=0,
        y1=20,
        fillcolor="rgba(0, 200, 120, 0.08)",
        line_width=0
    )

    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color="rgba(255, 80, 80, 0.75)"
    )

    fig.add_hline(
        y=20,
        line_dash="dash",
        line_color="rgba(0, 200, 120, 0.75)"
    )

    fig.add_hline(
        y=50,
        line_dash="dot",
        line_color="rgba(220, 220, 220, 0.45)"
    )

    fig.update_layout(
        title=f"{display_name} - Stochastic RSI",
        template="plotly_dark",
        height=360,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Stoch RSI",
        yaxis=dict(
            range=[0, 100],
            tickmode="array",
            tickvals=[0, 20, 50, 80, 100]
        ),
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )

    return fig


def make_macd_chart(df: pd.DataFrame, display_name: str):
    if "macd" not in df.columns or "macd_signal" not in df.columns:
        return None

    plot_df = df.copy()

    if "macd_hist" not in plot_df.columns:
        plot_df["macd_hist"] = plot_df["macd"] - plot_df["macd_signal"]

    plot_df["macd"] = pd.to_numeric(plot_df["macd"], errors="coerce")
    plot_df["macd_signal"] = pd.to_numeric(plot_df["macd_signal"], errors="coerce")
    plot_df["macd_hist"] = pd.to_numeric(plot_df["macd_hist"], errors="coerce")

    plot_df = plot_df.replace([np.inf, -np.inf], np.nan)
    plot_df = plot_df.dropna(
        subset=["snapped_at", "macd", "macd_signal", "macd_hist"]
    ).copy()

    if plot_df.empty:
        return None

    hist_colors = np.where(
        plot_df["macd_hist"] >= 0,
        "rgba(0, 200, 120, 0.85)",
        "rgba(255, 80, 80, 0.85)"
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=plot_df["snapped_at"],
            y=plot_df["macd_hist"],
            name="MACD Histogram",
            marker=dict(
                color=hist_colors,
                line=dict(width=0)
            ),
            opacity=0.95
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df["macd"],
            mode="lines",
            name="MACD",
            line=dict(
                width=2,
                color="rgba(80, 160, 255, 1)"
            )
        )
    )

    fig.add_trace(
        go.Scatter(
            x=plot_df["snapped_at"],
            y=plot_df["macd_signal"],
            mode="lines",
            name="MACD Signal",
            line=dict(
                width=2,
                color="rgba(255, 190, 80, 1)"
            )
        )
    )

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(220, 220, 220, 0.55)"
    )

    fig.update_layout(
        title=f"{display_name} - MACD",
        template="plotly_dark",
        height=360,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="MACD",
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0
        )
    )

    return fig


# =========================
# RISK / EVENT CHARTS
# =========================

def make_suspicious_events_bar_chart(df: pd.DataFrame, display_name: str):
    events = {
        "Volume Spike": int(df["volume_spike"].sum()) if "volume_spike" in df.columns else 0,
        "Possible Pump/Dump": int(df["possible_pump_dump"].sum()) if "possible_pump_dump" in df.columns else 0,
        "Possible Spoofing": int(df["possible_spoofing"].sum()) if "possible_spoofing" in df.columns else 0,
        "Extreme RSI": int(df["extreme_rsi"].sum()) if "extreme_rsi" in df.columns else 0,
    }

    events_df = pd.DataFrame(
        {
            "event": list(events.keys()),
            "count": list(events.values())
        }
    )

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=events_df["event"],
            y=events_df["count"],
            name="Events",
            marker=dict(
                color=[
                    "rgba(255, 215, 0, 0.85)",
                    "rgba(255, 80, 80, 0.85)",
                    "rgba(255, 170, 60, 0.85)",
                    "rgba(120, 130, 255, 0.85)"
                ]
            )
        )
    )

    fig.update_layout(
        title=f"{display_name} - Suspicious / Risk Event Counts",
        template="plotly_dark",
        height=450,
        xaxis_title="Event Type",
        yaxis_title="Count",
        margin=dict(l=20, r=20, t=60, b=40)
    )

    return fig


def make_volume_price_scatter(df: pd.DataFrame, display_name: str):
    scatter_df = df.dropna(subset=["volume_zscore", "price_change_pct"]).copy()

    if scatter_df.empty:
        return None

    scatter_df["event_type"] = "Normal"

    if "volume_spike" in scatter_df.columns:
        scatter_df.loc[scatter_df["volume_spike"], "event_type"] = "Volume Spike"

    if "possible_pump_dump" in scatter_df.columns:
        scatter_df.loc[scatter_df["possible_pump_dump"], "event_type"] = "Possible Pump/Dump"

    if "possible_spoofing" in scatter_df.columns:
        scatter_df.loc[scatter_df["possible_spoofing"], "event_type"] = "Possible Spoofing"

    fig = go.Figure()

    color_map = {
        "Normal": "rgba(120, 130, 255, 0.55)",
        "Volume Spike": "rgba(255, 215, 0, 0.85)",
        "Possible Pump/Dump": "rgba(255, 80, 80, 0.9)",
        "Possible Spoofing": "rgba(255, 170, 60, 0.9)"
    }

    for event_type in scatter_df["event_type"].unique():
        part = scatter_df[scatter_df["event_type"] == event_type]

        fig.add_trace(
            go.Scatter(
                x=part["volume_zscore"],
                y=part["price_change_pct"],
                mode="markers",
                name=event_type,
                text=part["snapped_at"].dt.strftime("%Y-%m-%d"),
                marker=dict(
                    size=7,
                    color=color_map.get(event_type, "rgba(160, 160, 160, 0.7)")
                ),
                hovertemplate=(
                    "Date: %{text}<br>"
                    "Volume Z-Score: %{x:.2f}<br>"
                    "Price Change: %{y:.2f}%<extra></extra>"
                )
            )
        )

    fig.add_vline(
        x=2.5,
        line_dash="dash",
        line_color="rgba(255, 215, 0, 0.75)"
    )

    fig.add_hline(
        y=5,
        line_dash="dash",
        line_color="rgba(255, 80, 80, 0.75)"
    )

    fig.add_hline(
        y=-5,
        line_dash="dash",
        line_color="rgba(255, 80, 80, 0.75)"
    )

    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color="rgba(220, 220, 220, 0.45)"
    )

    fig.add_vline(
        x=0,
        line_dash="dot",
        line_color="rgba(220, 220, 220, 0.45)"
    )

    fig.update_layout(
        title=f"{display_name} - Volume Z-Score vs Price Change %",
        template="plotly_dark",
        height=600,
        xaxis_title="Volume Z-Score",
        yaxis_title="Price Change %",
        margin=dict(l=20, r=20, t=60, b=40)
    )

    return fig


def make_returns_boxplot(df: pd.DataFrame, display_name: str):
    box_df = df.dropna(subset=["daily_return_pct"]).copy()

    if box_df.empty:
        return None

    if "suspicious_event" not in box_df.columns:
        box_df["suspicious_event"] = False

    box_df["event_group"] = np.where(
        box_df["suspicious_event"],
        "Suspicious Event",
        "Normal"
    )

    fig = go.Figure()

    color_map = {
        "Normal": "rgba(120, 130, 255, 0.65)",
        "Suspicious Event": "rgba(255, 80, 80, 0.75)"
    }

    for group in ["Normal", "Suspicious Event"]:
        part = box_df[box_df["event_group"] == group]

        if part.empty:
            continue

        fig.add_trace(
            go.Box(
                y=part["daily_return_pct"],
                name=group,
                boxpoints="outliers",
                marker=dict(
                    color=color_map[group]
                ),
                line=dict(
                    color=color_map[group]
                )
            )
        )

    fig.update_layout(
        title=f"{display_name} - Returns Distribution: Normal vs Suspicious Events",
        template="plotly_dark",
        height=520,
        yaxis_title="Daily Return %",
        margin=dict(l=20, r=20, t=60, b=40)
    )

    return fig


def make_drawdown_chart(df: pd.DataFrame, display_name: str):
    if "drawdown_pct" not in df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df["drawdown_pct"],
            mode="lines",
            name="Drawdown %",
            fill="tozeroy",
            line=dict(
                width=2,
                color="rgba(255, 80, 80, 0.85)"
            ),
            fillcolor="rgba(255, 80, 80, 0.18)"
        )
    )

    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color="rgba(220, 220, 220, 0.55)"
    )

    fig.update_layout(
        title=f"{display_name} - Drawdown",
        template="plotly_dark",
        height=430,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Drawdown %",
        margin=dict(l=20, r=20, t=60, b=40)
    )

    return fig


def make_volatility_chart(df: pd.DataFrame, display_name: str):
    if "rolling_volatility_30d" not in df.columns:
        return None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df["snapped_at"],
            y=df["rolling_volatility_30d"],
            mode="lines",
            name="Rolling Volatility 30D",
            line=dict(
                width=2,
                color="rgba(255, 215, 0, 0.95)"
            )
        )
    )

    fig.update_layout(
        title=f"{display_name} - Rolling Volatility 30D",
        template="plotly_dark",
        height=430,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Volatility %",
        margin=dict(l=20, r=20, t=60, b=40)
    )

    return fig


# =========================
# BACKWARD COMPATIBILITY
# =========================

def make_asset_technical_chart(
    df: pd.DataFrame,
    asset_key: str,
    display_name: str,
    show_emas: bool = True,
    show_bollinger: bool = True,
    show_flags: bool = True,
    show_volume: bool = True,
    show_rsi: bool = True,
    show_stoch: bool = True,
    show_macd: bool = True,
    events_df: pd.DataFrame | None = None,
    show_events: bool = True
):
    """
    Backward compatibility wrapper.
    Returns the integrated technical dashboard chart.
    """

    events = events_df if show_events else None

    return make_price_chart(
        df=df,
        display_name=display_name,
        show_emas=show_emas,
        show_bollinger=show_bollinger,
        show_flags=show_flags,
        show_volume=show_volume,
        show_rsi=show_rsi,
        show_stoch_rsi=show_stoch,
        show_macd=show_macd,
        events=events
    )
