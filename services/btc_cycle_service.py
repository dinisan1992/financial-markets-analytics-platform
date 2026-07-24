import numpy as np
import pandas as pd



def extract_btc_halving_events(events_df: pd.DataFrame):
    """
    Extract BTC halving events from bitcoin_historical_events.

    This keeps the analysis data-driven:
    halving dates come from the event table, not from hardcoded Python lists.
    """
    if events_df is None or events_df.empty:
        return pd.DataFrame()

    df = events_df.copy()

    if "event_source_table" in df.columns:
        df = df[df["event_source_table"] == "bitcoin_historical_events"].copy()

    if df.empty or "event_date" not in df.columns:
        return pd.DataFrame()

    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df = df.dropna(subset=["event_date"]).copy()

    text_cols = [
        col for col in [
            "event_title",
            "event_category",
            "event_description"
        ]
        if col in df.columns
    ]

    if not text_cols:
        return pd.DataFrame()

    for col in text_cols:
        df[col] = df[col].fillna("").astype(str)

    df["search_text"] = df[text_cols].agg(" ".join, axis=1).str.lower()

    halving_mask = (
        df["search_text"].str.contains("halving", na=False)
        | df["search_text"].str.contains("halv", na=False)
        | df["search_text"].str.contains("block reward", na=False)
        | df["search_text"].str.contains("block subsidy", na=False)
    )

    halvings_df = df[halving_mask].copy()

    if halvings_df.empty:
        return pd.DataFrame()

    halvings_df = halvings_df.sort_values("event_date").reset_index(drop=True)

    output_cols = [
        col for col in [
            "event_date",
            "event_title",
            "event_category",
            "event_description",
            "event_source_table"
        ]
        if col in halvings_df.columns
    ]

    return halvings_df[output_cols].copy()



def prepare_btc_price_frame(price_df: pd.DataFrame):
    if price_df is None or price_df.empty:
        return pd.DataFrame()

    if "snapped_at" not in price_df.columns or "close" not in price_df.columns:
        return pd.DataFrame()

    prices = price_df[["snapped_at", "close"]].copy()

    prices["snapped_at"] = pd.to_datetime(
        prices["snapped_at"],
        errors="coerce"
    )

    prices["close"] = pd.to_numeric(
        prices["close"],
        errors="coerce"
    )

    prices = prices.dropna(
        subset=["snapped_at", "close"]
    ).copy()

    prices = prices.sort_values("snapped_at").reset_index(drop=True)

    return prices



def get_first_price_on_or_after(prices: pd.DataFrame, target_date, max_days_gap=3):
    if prices is None or prices.empty:
        return None

    target_date = pd.to_datetime(target_date, errors="coerce")

    if pd.isna(target_date):
        return None

    rows = prices[prices["snapped_at"] >= target_date].copy()

    if rows.empty:
        return None

    first_row = rows.iloc[0]
    gap_days = int((first_row["snapped_at"] - target_date).days)

    if gap_days > max_days_gap:
        return None

    return first_row



def calculate_btc_halving_impact_from_events(
    price_df: pd.DataFrame,
    events_df: pd.DataFrame,
    analysis_window_days: int = 1095,
    return_horizons=(30, 90, 180, 365, 730, 1095),
    max_halving_price_gap_days: int = 3
):
    """
    BTC Halving Impact analysis.

    This is NOT a BTC cycle detector.
    It measures fixed forward performance after each halving.

    Main outputs:
    - Price at Halving
    - Return +30D, +90D, +180D, +365D, +730D, +1095D
    - Forward Window Days
    - Available Coverage Days
    - Window Low / Window High
    - Max Drawdown / Max Upside from Halving

    Important:
    - Forward Window Days is a fixed comparison window, not a cycle duration.
    - Auto-Detected Cycles should be used for macro BTC cycle analysis.
    """
    prices = prepare_btc_price_frame(price_df)
    halvings_df = extract_btc_halving_events(events_df)

    if prices.empty or halvings_df.empty:
        return pd.DataFrame()

    max_price_date = prices["snapped_at"].max()
    rows = []

    for _, halving in halvings_df.iterrows():
        halving_date = pd.to_datetime(halving["event_date"], errors="coerce")

        if pd.isna(halving_date):
            continue

        halving_row = get_first_price_on_or_after(
            prices=prices,
            target_date=halving_date,
            max_days_gap=max_halving_price_gap_days
        )

        # Example: first halving is skipped if local BTC price data starts months later.
        if halving_row is None:
            continue

        halving_market_date = halving_row["snapped_at"]
        halving_price = halving_row["close"]

        if pd.isna(halving_price) or halving_price == 0:
            continue

        target_window_end = halving_market_date + pd.Timedelta(days=analysis_window_days)
        window_end = min(target_window_end, max_price_date)

        window_df = prices[
            (prices["snapped_at"] >= halving_market_date)
            & (prices["snapped_at"] <= window_end)
        ].copy()

        if window_df.empty:
            continue

        low_row = window_df.sort_values("close", ascending=True).iloc[0]
        high_row = window_df.sort_values("close", ascending=False).iloc[0]

        low_date = low_row["snapped_at"]
        high_date = high_row["snapped_at"]
        low_price = low_row["close"]
        high_price = high_row["close"]

        coverage_days = int((window_end - halving_market_date).days)

        if coverage_days >= analysis_window_days:
            coverage_status = "Complete"
        else:
            coverage_status = "Partial / Current"

        row = {
            "Halving Event": halving.get("event_title", "BTC Halving"),
            "Halving Date": halving_date.date(),
            "Market Date": halving_market_date.date(),
            "Price at Halving": halving_price,

            "Forward Window Days": analysis_window_days,
            "Available Coverage Days": coverage_days,
            "Coverage Status": coverage_status,
            "Window End": window_end.date(),

            "Window Low Date": low_date.date(),
            "Window Low": low_price,
            "Days to Window Low": int((low_date - halving_market_date).days),
            "Max Drawdown from Halving %": ((low_price / halving_price) - 1) * 100,

            "Window High Date": high_date.date(),
            "Window High": high_price,
            "Days to Window High": int((high_date - halving_market_date).days),
            "Max Upside from Halving %": ((high_price / halving_price) - 1) * 100,
        }

        for horizon in return_horizons:
            target_date = halving_market_date + pd.Timedelta(days=int(horizon))
            future_rows = prices[prices["snapped_at"] >= target_date].copy()

            if future_rows.empty:
                row[f"Return +{horizon}D %"] = np.nan
                row[f"Price +{horizon}D"] = np.nan
                row[f"Date +{horizon}D"] = None
            else:
                future_row = future_rows.iloc[0]
                future_price = future_row["close"]

                if pd.isna(future_price) or halving_price == 0:
                    row[f"Return +{horizon}D %"] = np.nan
                else:
                    row[f"Return +{horizon}D %"] = ((future_price / halving_price) - 1) * 100

                row[f"Price +{horizon}D"] = future_price
                row[f"Date +{horizon}D"] = future_row["snapped_at"].date()

        rows.append(row)

    result_df = pd.DataFrame(rows)

    if result_df.empty:
        return result_df

    # Column order for a cleaner Streamlit table.
    preferred_cols = [
        "Halving Event",
        "Halving Date",
        "Market Date",
        "Price at Halving",
        "Forward Window Days",
        "Available Coverage Days",
        "Coverage Status",
        "Window End",
        "Return +30D %",
        "Return +90D %",
        "Return +180D %",
        "Return +365D %",
        "Return +730D %",
        "Return +1095D %",
        "Window Low Date",
        "Window Low",
        "Days to Window Low",
        "Max Drawdown from Halving %",
        "Window High Date",
        "Window High",
        "Days to Window High",
        "Max Upside from Halving %",
        "Price +30D",
        "Date +30D",
        "Price +90D",
        "Date +90D",
        "Price +180D",
        "Date +180D",
        "Price +365D",
        "Date +365D",
        "Price +730D",
        "Date +730D",
        "Price +1095D",
        "Date +1095D",
    ]

    existing_preferred_cols = [
        col for col in preferred_cols
        if col in result_df.columns
    ]

    other_cols = [
        col for col in result_df.columns
        if col not in existing_preferred_cols
    ]

    result_df = result_df[existing_preferred_cols + other_cols].copy()

    numeric_cols = [
        "Price at Halving",
        "Window Low",
        "Max Drawdown from Halving %",
        "Window High",
        "Max Upside from Halving %",
    ]

    for horizon in return_horizons:
        numeric_cols.extend([
            f"Return +{horizon}D %",
            f"Price +{horizon}D",
        ])

    for col in numeric_cols:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors="coerce").round(2)

    return result_df



def calculate_btc_full_market_cycles_from_events(
    price_df: pd.DataFrame,
    events_df: pd.DataFrame,
    max_halving_price_gap_days: int = 3,
    pre_halving_bottom_lookback_months: int = 24
):
    """
    Full BTC Market Cycle view around each halving.

    v4 logic:
    The previous version could fail when BTC made a new all-time high BEFORE the halving
    (for example 2024, due to ETF inflows). In that case, simply taking the highest price
    before the halving as "Previous Top" incorrectly ignored the 2021 top / 2022 bottom cycle.

    This version separates the cycle into three phases:

    1. Halving price:
       First price on or shortly after the halving date.

    2. Pre-halving bear-market bottom:
       Lowest close in the final N months before the halving.
       Default: 24 months.
       This captures the typical BTC cycle bottom before the halving:
       - 2015 bottom before 2016 halving
       - 2018 bottom before 2020 halving
       - 2022 bottom before 2024 halving

    3. Previous top:
       Highest close between previous halving and the detected bottom date.
       This captures the previous bull-market top before the bear-market bottom.

    4. Post-halving top:
       Highest close from the halving date until the next halving/current end.

    Output includes:
    - Halving Date
    - Price at Halving
    - Previous Top
    - Cycle Bottom
    - Cycle Top
    - Days to Bottom
    - Days to Top
    - Drawdown from Halving
    - Upside from Halving
    - Days Down
    - Days Up
    - Cycle Duration
    """
    prices = prepare_btc_price_frame(price_df)
    halvings_df = extract_btc_halving_events(events_df)

    if prices.empty or halvings_df.empty:
        return pd.DataFrame()

    first_price_date = prices["snapped_at"].min()
    max_price_date = prices["snapped_at"].max()
    rows = []

    for idx, halving in halvings_df.iterrows():
        halving_date = pd.to_datetime(halving["event_date"], errors="coerce")

        if pd.isna(halving_date):
            continue

        halving_row = get_first_price_on_or_after(
            prices=prices,
            target_date=halving_date,
            max_days_gap=max_halving_price_gap_days
        )

        # Example: first halving is skipped if local BTC price data starts months later.
        if halving_row is None:
            continue

        halving_market_date = halving_row["snapped_at"]
        halving_price = halving_row["close"]

        if pd.isna(halving_price) or halving_price == 0:
            continue

        if idx > 0:
            previous_halving_date = pd.to_datetime(
                halvings_df.iloc[idx - 1]["event_date"],
                errors="coerce"
            )

            if pd.isna(previous_halving_date):
                previous_halving_date = first_price_date
        else:
            previous_halving_date = first_price_date

        if idx + 1 < len(halvings_df):
            next_halving_date = pd.to_datetime(
                halvings_df.iloc[idx + 1]["event_date"],
                errors="coerce"
            )

            if pd.isna(next_halving_date):
                next_halving_date = max_price_date
        else:
            next_halving_date = max_price_date

        # Bear-market bottom search window:
        # final N months before the halving, bounded by available data and previous halving.
        bottom_window_start = halving_market_date - pd.DateOffset(
            months=pre_halving_bottom_lookback_months
        )

        if pd.notna(previous_halving_date):
            bottom_window_start = max(
                pd.to_datetime(bottom_window_start),
                pd.to_datetime(previous_halving_date),
                pd.to_datetime(first_price_date)
            )
        else:
            bottom_window_start = max(
                pd.to_datetime(bottom_window_start),
                pd.to_datetime(first_price_date)
            )

        bottom_window_df = prices[
            (prices["snapped_at"] >= bottom_window_start)
            & (prices["snapped_at"] <= halving_market_date)
        ].copy()

        if bottom_window_df.empty:
            continue

        bottom_row = bottom_window_df.sort_values("close", ascending=True).iloc[0]
        bottom_date = bottom_row["snapped_at"]
        bottom_price = bottom_row["close"]

        # Previous top must happen before the detected bear-market bottom.
        previous_top_window_df = prices[
            (prices["snapped_at"] >= previous_halving_date)
            & (prices["snapped_at"] <= bottom_date)
        ].copy()

        if previous_top_window_df.empty:
            previous_top_date = pd.NaT
            previous_top_price = np.nan
            days_down = np.nan
            drawdown_top_to_bottom_pct = np.nan
        else:
            previous_top_row = previous_top_window_df.sort_values("close", ascending=False).iloc[0]
            previous_top_date = previous_top_row["snapped_at"]
            previous_top_price = previous_top_row["close"]

            days_down = int((bottom_date - previous_top_date).days)

            drawdown_top_to_bottom_pct = (
                ((bottom_price / previous_top_price) - 1) * 100
                if previous_top_price and previous_top_price != 0
                else np.nan
            )

        post_halving_df = prices[
            (prices["snapped_at"] >= halving_market_date)
            & (prices["snapped_at"] <= next_halving_date)
        ].copy()

        if post_halving_df.empty:
            continue

        top_row = post_halving_df.sort_values("close", ascending=False).iloc[0]
        top_date = top_row["snapped_at"]
        top_price = top_row["close"]

        days_to_bottom = int((bottom_date - halving_market_date).days)
        days_to_top = int((top_date - halving_market_date).days)
        days_up = int((top_date - bottom_date).days)

        if days_to_bottom < 0:
            bottom_timing = "Before halving"
        elif days_to_bottom > 0:
            bottom_timing = "After halving"
        else:
            bottom_timing = "On halving date"

        if days_to_top < 0:
            top_timing = "Before halving"
        elif days_to_top > 0:
            top_timing = "After halving"
        else:
            top_timing = "On halving date"

        upside_bottom_to_top_pct = (
            ((top_price / bottom_price) - 1) * 100
            if bottom_price and bottom_price != 0
            else np.nan
        )

        rows.append(
            {
                "Halving Event": halving.get("event_title", "BTC Halving"),
                "Halving Date": halving_date.date(),
                "Market Date": halving_market_date.date(),
                "Cycle Start": pd.to_datetime(previous_halving_date).date(),
                "Cycle End": pd.to_datetime(next_halving_date).date(),
                "Price at Halving": halving_price,
                "Previous Top Date": previous_top_date.date() if pd.notna(previous_top_date) else None,
                "Previous Top Price": previous_top_price,
                "Cycle Bottom Date": bottom_date.date(),
                "Cycle Bottom": bottom_price,
                "Days to Bottom": days_to_bottom,
                "Bottom Timing": bottom_timing,
                "Drawdown from Halving %": ((bottom_price / halving_price) - 1) * 100,
                "Drawdown Top to Bottom %": drawdown_top_to_bottom_pct,
                "Days Down": days_down,
                "Cycle Top Date": top_date.date(),
                "Cycle Top": top_price,
                "Days to Top": days_to_top,
                "Top Timing": top_timing,
                "Upside from Halving %": ((top_price / halving_price) - 1) * 100,
                "Upside Bottom to Top %": upside_bottom_to_top_pct,
                "Days Up": days_up,
                "Cycle Duration": int((pd.to_datetime(next_halving_date) - pd.to_datetime(previous_halving_date)).days),
            }
        )

    result_df = pd.DataFrame(rows)

    return format_btc_cycle_numeric_columns(result_df)



def format_btc_cycle_numeric_columns(cycle_df: pd.DataFrame):
    if cycle_df is None or cycle_df.empty:
        return pd.DataFrame()

    result_df = cycle_df.copy()

    numeric_cols = [
        "Price at Halving",
        "Cycle Bottom",
        "Drawdown from Halving %",
        "Cycle Top",
        "Upside from Halving %",
        "Previous Top Price",
        "Drawdown Top to Bottom %",
        "Upside Bottom to Top %",
    ]

    for col in numeric_cols:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors="coerce").round(2)

    return result_df



def build_btc_cycle_interpretation(cycle_df: pd.DataFrame, mode_label: str):
    if cycle_df is None or cycle_df.empty:
        return "No BTC cycle interpretation is available."

    parts = []

    if "Upside from Halving %" in cycle_df.columns:
        upside_df = cycle_df.dropna(subset=["Upside from Halving %"]).copy()

        if not upside_df.empty:
            avg_upside = upside_df["Upside from Halving %"].mean()
            best_cycle = upside_df.sort_values(
                "Upside from Halving %",
                ascending=False
            ).iloc[0]

            parts.append(
                f"In the {mode_label.lower()} view, the average upside from halving to cycle top is {avg_upside:,.2f}%."
            )

            parts.append(
                f"The strongest available cycle was {best_cycle['Halving Event']}, with an upside from halving of {best_cycle['Upside from Halving %']:,.2f}%."
            )

    if "Drawdown from Halving %" in cycle_df.columns:
        drawdown_df = cycle_df.dropna(subset=["Drawdown from Halving %"]).copy()

        if not drawdown_df.empty:
            avg_drawdown = drawdown_df["Drawdown from Halving %"].mean()

            parts.append(
                f"The average drawdown from halving to cycle bottom is {avg_drawdown:,.2f}%."
            )

    if "Days to Top" in cycle_df.columns:
        days_top_df = cycle_df.dropna(subset=["Days to Top"]).copy()

        if not days_top_df.empty:
            avg_days_to_top = days_top_df["Days to Top"].mean()

            parts.append(
                f"The average time from halving to cycle top is approximately {avg_days_to_top:,.0f} days."
            )

    if "Bottom Timing" in cycle_df.columns:
        bottom_before = (cycle_df["Bottom Timing"] == "Before halving").sum()

        if bottom_before > 0:
            parts.append(
                f"In {bottom_before} available cycle(s), the cycle bottom occurred before the halving, which is why the full market cycle view is more realistic than a purely post-halving view."
            )

    if not parts:
        return "BTC cycle data is available, but there is not enough information to generate an interpretation."

    return " ".join(parts)



def detect_btc_major_bear_cycles(
    price_df: pd.DataFrame,
    min_drawdown_pct: float = 60.0,
    recovery_ratio: float = 1.0,
    min_days_after_top: int = 30
):
    """
    Detect major BTC bear cycles automatically from price data.

    Logic:
    - Track cumulative all-time highs.
    - When price falls at least min_drawdown_pct from the latest ATH, a major bear phase is confirmed.
    - Track the lowest price during the bear phase.
    - When price recovers back to the previous ATH level, close that bear cycle.
    - The next major ATH before a later drawdown becomes the next bull top.

    This is intentionally conservative and designed for BTC macro cycles,
    not short-term swings.
    """
    prices = prepare_btc_price_frame(price_df)

    if prices.empty:
        return []

    cycles = []

    state = "bull"

    ath_price = prices.iloc[0]["close"]
    ath_date = prices.iloc[0]["snapped_at"]

    bear_top_price = np.nan
    bear_top_date = pd.NaT
    bottom_price = np.nan
    bottom_date = pd.NaT

    for _, row in prices.iterrows():
        current_date = row["snapped_at"]
        current_price = row["close"]

        if pd.isna(current_price) or current_price <= 0:
            continue

        if state == "bull":
            if current_price >= ath_price:
                ath_price = current_price
                ath_date = current_date

            days_since_ath = int((current_date - ath_date).days)
            drawdown_from_ath = ((current_price / ath_price) - 1) * 100 if ath_price else 0

            if drawdown_from_ath <= -abs(min_drawdown_pct) and days_since_ath >= min_days_after_top:
                state = "bear"
                bear_top_price = ath_price
                bear_top_date = ath_date
                bottom_price = current_price
                bottom_date = current_date

        elif state == "bear":
            if current_price < bottom_price:
                bottom_price = current_price
                bottom_date = current_date

            if current_price >= bear_top_price * recovery_ratio:
                cycles.append(
                    {
                        "bear_top_date": bear_top_date,
                        "bear_top_price": bear_top_price,
                        "cycle_bottom_date": bottom_date,
                        "cycle_bottom_price": bottom_price,
                        "recovery_date": current_date,
                        "recovery_price": current_price,
                        "status": "Closed",
                    }
                )

                state = "bull"
                ath_price = current_price
                ath_date = current_date

    # If a major bear phase is still open, keep it as open.
    if state == "bear":
        cycles.append(
            {
                "bear_top_date": bear_top_date,
                "bear_top_price": bear_top_price,
                "cycle_bottom_date": bottom_date,
                "cycle_bottom_price": bottom_price,
                "recovery_date": pd.NaT,
                "recovery_price": np.nan,
                "status": "Open Bear Phase",
            }
        )

    return cycles



def calculate_btc_auto_detected_cycles(
    price_df: pd.DataFrame,
    events_df: pd.DataFrame,
    min_drawdown_pct: float = 60.0,
    recovery_ratio: float = 1.0,
    min_days_after_top: int = 30,
    max_halving_price_gap_days: int = 3
):
    """
    Build BTC macro swing-cycle table automatically.

    For each detected bear cycle:
    - Bear Top = ATH before a major drawdown.
    - Cycle Bottom = lowest price before recovery.
    - Next Bull Top = next detected bear top, or latest available high after bottom for the current cycle.

    Halvings are extracted from bitcoin_historical_events and overlaid as cycle markers.
    """
    prices = prepare_btc_price_frame(price_df)
    halvings_df = extract_btc_halving_events(events_df)

    if prices.empty:
        return pd.DataFrame()

    bear_cycles = detect_btc_major_bear_cycles(
        price_df=price_df,
        min_drawdown_pct=min_drawdown_pct,
        recovery_ratio=recovery_ratio,
        min_days_after_top=min_days_after_top
    )

    if not bear_cycles:
        return pd.DataFrame()

    rows = []

    for idx, cycle in enumerate(bear_cycles):
        bear_top_date = pd.to_datetime(cycle.get("bear_top_date"), errors="coerce")
        bear_top_price = cycle.get("bear_top_price")

        bottom_date = pd.to_datetime(cycle.get("cycle_bottom_date"), errors="coerce")
        bottom_price = cycle.get("cycle_bottom_price")

        if pd.isna(bear_top_date) or pd.isna(bottom_date):
            continue

        if idx + 1 < len(bear_cycles):
            next_top_date = pd.to_datetime(
                bear_cycles[idx + 1].get("bear_top_date"),
                errors="coerce"
            )
            next_top_price = bear_cycles[idx + 1].get("bear_top_price")
            status = "Closed"
        else:
            after_bottom_df = prices[prices["snapped_at"] >= bottom_date].copy()

            if after_bottom_df.empty:
                next_top_date = pd.NaT
                next_top_price = np.nan
            else:
                next_top_row = after_bottom_df.sort_values("close", ascending=False).iloc[0]
                next_top_date = next_top_row["snapped_at"]
                next_top_price = next_top_row["close"]

            if cycle.get("status") == "Open Bear Phase":
                status = "Open Bear Phase"
            else:
                status = "Tentative / Current"

        days_down = int((bottom_date - bear_top_date).days)

        drawdown_pct = (
            ((bottom_price / bear_top_price) - 1) * 100
            if bear_top_price and bear_top_price != 0
            else np.nan
        )

        days_up = np.nan
        upside_pct = np.nan

        if pd.notna(next_top_date):
            days_up = int((next_top_date - bottom_date).days)

        if bottom_price and bottom_price != 0 and pd.notna(next_top_price):
            upside_pct = ((next_top_price / bottom_price) - 1) * 100

        halving_event = None

        if pd.notna(bottom_date) and pd.notna(next_top_date):
            halving_event = get_halving_between_dates(
                halvings_df=halvings_df,
                start_date=bottom_date,
                end_date=next_top_date
            )

        halving_name = None
        halving_date = pd.NaT
        price_at_halving = np.nan
        halving_price_date = pd.NaT
        days_bottom_to_halving = np.nan
        days_halving_to_top = np.nan
        return_bottom_to_halving_pct = np.nan
        return_halving_to_top_pct = np.nan

        if halving_event is not None:
            halving_name = halving_event.get("event_title", "BTC Halving")
            halving_date = pd.to_datetime(halving_event.get("event_date"), errors="coerce")

            if pd.notna(halving_date):
                days_bottom_to_halving = int((halving_date - bottom_date).days)

                if pd.notna(next_top_date):
                    days_halving_to_top = int((next_top_date - halving_date).days)

                halving_price_row = get_first_price_on_or_after(
                    prices=prices,
                    target_date=halving_date,
                    max_days_gap=max_halving_price_gap_days
                )

                if halving_price_row is not None:
                    price_at_halving = halving_price_row["close"]
                    halving_price_date = halving_price_row["snapped_at"]

                    if bottom_price and bottom_price != 0:
                        return_bottom_to_halving_pct = ((price_at_halving / bottom_price) - 1) * 100

                    if price_at_halving and price_at_halving != 0 and pd.notna(next_top_price):
                        return_halving_to_top_pct = ((next_top_price / price_at_halving) - 1) * 100

        rows.append(
            {
                "Cycle": f"{bear_top_date.date()} Top -> {bottom_date.date()} Bottom",
                "Status": status,
                "Bear Top Date": bear_top_date.date(),
                "Bear Top Price": bear_top_price,
                "Cycle Bottom Date": bottom_date.date(),
                "Cycle Bottom Price": bottom_price,
                "Days Down": days_down,
                "Drawdown %": drawdown_pct,
                "Next Bull Top Date": next_top_date.date() if pd.notna(next_top_date) else None,
                "Next Bull Top Price": next_top_price,
                "Days Up": days_up,
                "Upside %": upside_pct,
                "Halving Event": halving_name,
                "Halving Date": halving_date.date() if pd.notna(halving_date) else None,
                "Halving Price Date": halving_price_date.date() if pd.notna(halving_price_date) else None,
                "Price at Halving": price_at_halving,
                "Days Bottom to Halving": days_bottom_to_halving,
                "Days Halving to Top": days_halving_to_top,
                "Return Bottom to Halving %": return_bottom_to_halving_pct,
                "Return Halving to Top %": return_halving_to_top_pct,
            }
        )

    result_df = pd.DataFrame(rows)

    numeric_cols = [
        "Bear Top Price",
        "Cycle Bottom Price",
        "Drawdown %",
        "Next Bull Top Price",
        "Upside %",
        "Price at Halving",
        "Return Bottom to Halving %",
        "Return Halving to Top %",
    ]

    for col in numeric_cols:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors="coerce").round(2)

    return result_df



BTC_VALIDATED_CYCLE_ANCHORS = [
    {
        "cycle_label": "2011 Bear -> 2013 Bull",
        "bear_top_date": "2011-06-09",
        "bear_top_price": 30.86,
        "cycle_bottom_date": "2011-11-14",
        "cycle_bottom_price": 2.06,
        "next_bull_top_date": "2013-11-30",
        "next_bull_top_price": 1161.00,
        "status": "Closed",
    },
    {
        "cycle_label": "2013 Bear -> 2017 Bull",
        "bear_top_date": "2013-11-30",
        "bear_top_price": 1161.00,
        "cycle_bottom_date": "2015-01-14",
        "cycle_bottom_price": 165.00,
        "next_bull_top_date": "2017-12-15",
        "next_bull_top_price": 19940.00,
        "status": "Closed",
    },
    {
        "cycle_label": "2017 Bear -> 2021 Bull",
        "bear_top_date": "2017-12-15",
        "bear_top_price": 19940.00,
        "cycle_bottom_date": "2018-12-14",
        "cycle_bottom_price": 3165.00,
        "next_bull_top_date": "2021-11-12",
        "next_bull_top_price": 68800.00,
        "status": "Closed",
    },
    {
        "cycle_label": "2021 Bear -> 2025 Bull?",
        "bear_top_date": "2021-11-12",
        "bear_top_price": 68800.00,
        "cycle_bottom_date": "2022-11-21",
        "cycle_bottom_price": 15000.00,
        "next_bull_top_date": "2025-08-13",
        "next_bull_top_price": 124000.00,
        "status": "Tentative / Current",
    },
    {
        "cycle_label": "2025 Bear? -> Open",
        "bear_top_date": "2025-08-13",
        "bear_top_price": 124000.00,
        "cycle_bottom_date": None,
        "cycle_bottom_price": None,
        "next_bull_top_date": None,
        "next_bull_top_price": None,
        "status": "Open / Unconfirmed",
    },
]



def get_halving_between_dates(halvings_df: pd.DataFrame, start_date, end_date):
    if halvings_df is None or halvings_df.empty:
        return None

    start_date = pd.to_datetime(start_date, errors="coerce")
    end_date = pd.to_datetime(end_date, errors="coerce")

    if pd.isna(start_date) or pd.isna(end_date):
        return None

    df = halvings_df.copy()
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    df = df.dropna(subset=["event_date"]).copy()

    matched = df[
        (df["event_date"] >= start_date)
        & (df["event_date"] <= end_date)
    ].copy()

    if matched.empty:
        return None

    return matched.sort_values("event_date").iloc[0]



def calculate_btc_validated_swing_cycles(
    price_df: pd.DataFrame,
    events_df: pd.DataFrame,
    max_halving_price_gap_days: int = 3
):
    """
    BTC validated swing-cycle analysis.

    This is intentionally semi-manual:
    BTC cycle tops and bottoms are defined as historical anchors, not detected automatically.
    Halvings are still extracted from bitcoin_historical_events and used as cycle markers.

    This avoids false automatic cycle detection caused by special cases such as:
    - missing early BTC price history before 2013
    - new ATH before the 2024 halving due to ETF inflows
    - post-halving local lows being mistaken for full bear-market bottoms
    """
    prices = prepare_btc_price_frame(price_df)
    halvings_df = extract_btc_halving_events(events_df)

    rows = []

    for anchor in BTC_VALIDATED_CYCLE_ANCHORS:
        bear_top_date = pd.to_datetime(anchor.get("bear_top_date"), errors="coerce")
        cycle_bottom_date = pd.to_datetime(anchor.get("cycle_bottom_date"), errors="coerce")
        next_bull_top_date = pd.to_datetime(anchor.get("next_bull_top_date"), errors="coerce")

        bear_top_price = anchor.get("bear_top_price")
        cycle_bottom_price = anchor.get("cycle_bottom_price")
        next_bull_top_price = anchor.get("next_bull_top_price")

        status = anchor.get("status", "-")

        days_down = np.nan
        drawdown_pct = np.nan
        days_up = np.nan
        upside_pct = np.nan

        if pd.notna(bear_top_date) and pd.notna(cycle_bottom_date):
            days_down = int((cycle_bottom_date - bear_top_date).days)

        if bear_top_price and cycle_bottom_price and bear_top_price != 0:
            drawdown_pct = ((cycle_bottom_price / bear_top_price) - 1) * 100

        if pd.notna(cycle_bottom_date) and pd.notna(next_bull_top_date):
            days_up = int((next_bull_top_date - cycle_bottom_date).days)

        if cycle_bottom_price and next_bull_top_price and cycle_bottom_price != 0:
            upside_pct = ((next_bull_top_price / cycle_bottom_price) - 1) * 100

        halving_event = None

        # The most useful halving marker for a swing cycle is the halving between bottom and next bull top.
        if pd.notna(cycle_bottom_date) and pd.notna(next_bull_top_date):
            halving_event = get_halving_between_dates(
                halvings_df=halvings_df,
                start_date=cycle_bottom_date,
                end_date=next_bull_top_date
            )

        halving_name = None
        halving_date = pd.NaT
        price_at_halving = np.nan
        halving_price_date = pd.NaT
        days_bottom_to_halving = np.nan
        days_halving_to_top = np.nan
        return_bottom_to_halving_pct = np.nan
        return_halving_to_top_pct = np.nan

        if halving_event is not None:
            halving_name = halving_event.get("event_title", "BTC Halving")
            halving_date = pd.to_datetime(halving_event.get("event_date"), errors="coerce")

            if pd.notna(halving_date):
                if pd.notna(cycle_bottom_date):
                    days_bottom_to_halving = int((halving_date - cycle_bottom_date).days)

                if pd.notna(next_bull_top_date):
                    days_halving_to_top = int((next_bull_top_date - halving_date).days)

                if not prices.empty:
                    halving_price_row = get_first_price_on_or_after(
                        prices=prices,
                        target_date=halving_date,
                        max_days_gap=max_halving_price_gap_days
                    )

                    if halving_price_row is not None:
                        price_at_halving = halving_price_row["close"]
                        halving_price_date = halving_price_row["snapped_at"]

                        if cycle_bottom_price and cycle_bottom_price != 0:
                            return_bottom_to_halving_pct = ((price_at_halving / cycle_bottom_price) - 1) * 100

                        if price_at_halving and price_at_halving != 0 and next_bull_top_price:
                            return_halving_to_top_pct = ((next_bull_top_price / price_at_halving) - 1) * 100

        rows.append(
            {
                "Cycle": anchor.get("cycle_label"),
                "Status": status,
                "Bear Top Date": bear_top_date.date() if pd.notna(bear_top_date) else None,
                "Bear Top Price": bear_top_price,
                "Cycle Bottom Date": cycle_bottom_date.date() if pd.notna(cycle_bottom_date) else None,
                "Cycle Bottom Price": cycle_bottom_price,
                "Days Down": days_down,
                "Drawdown %": drawdown_pct,
                "Next Bull Top Date": next_bull_top_date.date() if pd.notna(next_bull_top_date) else None,
                "Next Bull Top Price": next_bull_top_price,
                "Days Up": days_up,
                "Upside %": upside_pct,
                "Halving Event": halving_name,
                "Halving Date": halving_date.date() if pd.notna(halving_date) else None,
                "Halving Price Date": halving_price_date.date() if pd.notna(halving_price_date) else None,
                "Price at Halving": price_at_halving,
                "Days Bottom to Halving": days_bottom_to_halving,
                "Days Halving to Top": days_halving_to_top,
                "Return Bottom to Halving %": return_bottom_to_halving_pct,
                "Return Halving to Top %": return_halving_to_top_pct,
            }
        )

    result_df = pd.DataFrame(rows)

    numeric_cols = [
        "Bear Top Price",
        "Cycle Bottom Price",
        "Drawdown %",
        "Next Bull Top Price",
        "Upside %",
        "Price at Halving",
        "Return Bottom to Halving %",
        "Return Halving to Top %",
    ]

    for col in numeric_cols:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors="coerce").round(2)

    return result_df
