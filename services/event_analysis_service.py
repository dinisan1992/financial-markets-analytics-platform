import numpy as np
import pandas as pd



EVENT_RETURN_COLUMNS = [
    "Return +1D %",
    "Return +7D %",
    "Return +30D %",
    "Return +90D %",
    "Return +180D %",
    "Return +365D %",
]



def filter_events_for_chart(events_df: pd.DataFrame, event_filter: str):
    if events_df is None or events_df.empty:
        return events_df

    if event_filter == "Hide Events":
        return None

    filtered_df = events_df.copy()

    if event_filter == "BTC Events":
        filtered_df = filtered_df[
            filtered_df["event_source_table"] == "bitcoin_historical_events"
        ].copy()

    elif event_filter == "World Events":
        filtered_df = filtered_df[
            filtered_df["event_source_table"] == "world_historical_events"
        ].copy()

    return filtered_df



def calculate_event_forward_returns(
    events_df: pd.DataFrame,
    price_df: pd.DataFrame,
    horizons=(1, 7, 30, 90, 180, 365),
    include_approximate=False,
):
    if events_df is None or events_df.empty:
        return pd.DataFrame()

    if price_df is None or price_df.empty:
        return events_df.copy()

    if "snapped_at" not in price_df.columns or "close" not in price_df.columns:
        return events_df.copy()

    events = events_df.copy()
    if not include_approximate and "date_precision" in events.columns:
        events = events[events["date_precision"].eq("exact")].copy()
    prices = price_df[["snapped_at", "close"]].copy()

    events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce")
    prices["snapped_at"] = pd.to_datetime(prices["snapped_at"], errors="coerce")
    prices["close"] = pd.to_numeric(prices["close"], errors="coerce")

    events = events.dropna(subset=["event_date"]).copy()
    prices = prices.dropna(subset=["snapped_at", "close"]).copy()

    if events.empty or prices.empty:
        return pd.DataFrame()

    prices = prices.sort_values("snapped_at").reset_index(drop=True)
    events = events.sort_values("event_date").reset_index(drop=True)

    output_rows = []

    for _, event in events.iterrows():
        event_date = event["event_date"]
        base_rows = prices[prices["snapped_at"] >= event_date]

        row = event.to_dict()

        if base_rows.empty:
            row["market_date"] = pd.NaT
            row["event_close"] = np.nan

            for horizon in horizons:
                row[f"return_{horizon}d_pct"] = np.nan

            output_rows.append(row)
            continue

        base_row = base_rows.iloc[0]
        base_date = base_row["snapped_at"]
        base_price = base_row["close"]

        row["market_date"] = base_date
        row["event_close"] = base_price

        for horizon in horizons:
            target_date = base_date + pd.Timedelta(days=horizon)
            future_rows = prices[prices["snapped_at"] >= target_date]

            if future_rows.empty or pd.isna(base_price) or base_price == 0:
                row[f"return_{horizon}d_pct"] = np.nan
            else:
                future_price = future_rows.iloc[0]["close"]
                row[f"return_{horizon}d_pct"] = ((future_price / base_price) - 1) * 100

        output_rows.append(row)

    result_df = pd.DataFrame(output_rows)

    return_columns = [f"return_{int(horizon)}d_pct" for horizon in horizons]
    display_cols = [
        "event_date",
        "date_precision",
        "market_date",
        "event_title",
        "event_category",
        "event_source_table",
        "event_close",
        *return_columns,
        "event_description",
    ]

    existing_cols = [col for col in display_cols if col in result_df.columns]
    result_df = result_df[existing_cols].copy()

    rename_map = {
        "event_date": "Event Date",
        "date_precision": "Date Precision",
        "market_date": "Market Date",
        "event_title": "Event",
        "event_category": "Category",
        "event_source_table": "Source",
        "event_close": "Close at Event",
        "event_description": "Description",
    }
    rename_map.update(
        {
            f"return_{int(horizon)}d_pct": f"Return +{int(horizon)}D %"
            for horizon in horizons
        }
    )

    result_df = result_df.rename(columns=rename_map)

    numeric_cols = [
        "Close at Event",
        *[f"Return +{int(horizon)}D %" for horizon in horizons],
    ]

    for col in numeric_cols:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors="coerce").round(2)

    return result_df



def calculate_event_impact_summary(event_returns_df: pd.DataFrame):
    if event_returns_df is None or event_returns_df.empty:
        return {}

    df = event_returns_df.copy()

    available_return_cols = [
        col for col in EVENT_RETURN_COLUMNS
        if col in df.columns
    ]

    if not available_return_cols:
        return {
            "events_count": len(df),
            "avg_7d": np.nan,
            "avg_30d": np.nan,
            "avg_90d": np.nan,
            "best_event": None,
            "best_return": np.nan,
            "worst_event": None,
            "worst_return": np.nan,
            "most_impacted_source": "-",
        }

    for col in available_return_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    source_col = "Source" if "Source" in df.columns else None

    most_impacted_source = "-"

    if source_col is not None and "Return +30D %" in df.columns:
        source_impact = (
            df.dropna(subset=["Return +30D %"])
            .groupby(source_col)["Return +30D %"]
            .apply(lambda s: s.abs().mean())
            .sort_values(ascending=False)
        )

        if not source_impact.empty:
            most_impacted_source = str(source_impact.index[0])

    best_event = None
    worst_event = None
    best_return = np.nan
    worst_return = np.nan

    ranking_col = "Return +30D %" if "Return +30D %" in df.columns else available_return_cols[0]
    ranking_df = df.dropna(subset=[ranking_col]).copy()

    if not ranking_df.empty:
        best_row = ranking_df.sort_values(ranking_col, ascending=False).iloc[0]
        worst_row = ranking_df.sort_values(ranking_col, ascending=True).iloc[0]

        best_event = best_row.get("Event", "-")
        worst_event = worst_row.get("Event", "-")
        best_return = best_row.get(ranking_col, np.nan)
        worst_return = worst_row.get(ranking_col, np.nan)

    return {
        "events_count": len(df),
        "avg_7d": df["Return +7D %"].mean() if "Return +7D %" in df.columns else np.nan,
        "avg_30d": df["Return +30D %"].mean() if "Return +30D %" in df.columns else np.nan,
        "avg_90d": df["Return +90D %"].mean() if "Return +90D %" in df.columns else np.nan,
        "best_event": best_event,
        "best_return": best_return,
        "worst_event": worst_event,
        "worst_return": worst_return,
        "most_impacted_source": most_impacted_source,
    }



def build_best_worst_event_tables(event_returns_df: pd.DataFrame, ranking_col="Return +30D %", n=10):
    if event_returns_df is None or event_returns_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    if ranking_col not in event_returns_df.columns:
        return pd.DataFrame(), pd.DataFrame()

    df = event_returns_df.copy()
    df[ranking_col] = pd.to_numeric(df[ranking_col], errors="coerce")
    df = df.dropna(subset=[ranking_col]).copy()

    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    selected_cols = [
        col for col in [
            "Event Date",
            "Event",
            "Category",
            "Source",
            "Close at Event",
            "Return +7D %",
            "Return +30D %",
            "Return +90D %",
            "Return +180D %",
            "Return +365D %",
        ]
        if col in df.columns
    ]

    best_df = df.sort_values(ranking_col, ascending=False)[selected_cols].head(n)
    worst_df = df.sort_values(ranking_col, ascending=True)[selected_cols].head(n)

    return best_df, worst_df



def build_event_source_comparison_table(event_returns_df: pd.DataFrame):
    if event_returns_df is None or event_returns_df.empty or "Source" not in event_returns_df.columns:
        return pd.DataFrame()

    return_cols = [
        col for col in [
            "Return +1D %",
            "Return +7D %",
            "Return +30D %",
            "Return +90D %",
            "Return +180D %",
            "Return +365D %",
        ]
        if col in event_returns_df.columns
    ]

    if not return_cols:
        return pd.DataFrame()

    df = event_returns_df.copy()

    for col in return_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    comparison_df = (
        df.groupby("Source")
        .agg(
            Events=("Event", "count"),
            **{col: (col, "mean") for col in return_cols}
        )
        .reset_index()
    )

    for col in return_cols:
        comparison_df[col] = comparison_df[col].round(2)

    return comparison_df



def build_event_impact_interpretation(event_returns_df: pd.DataFrame):
    if event_returns_df is None or event_returns_df.empty:
        return "No event impact interpretation is available."

    comparison_df = build_event_source_comparison_table(event_returns_df)

    if comparison_df.empty:
        return "Event impact data is available, but there is not enough information to compare event sources."

    horizon = "Return +30D %" if "Return +30D %" in comparison_df.columns else None

    if horizon is None:
        return "Event impact data is available, but forward return horizons are missing."

    valid_df = comparison_df.dropna(subset=[horizon]).copy()

    if valid_df.empty:
        return "Event impact data is available, but forward returns are not available for the selected horizon."

    best_source_row = valid_df.sort_values(horizon, ascending=False).iloc[0]
    worst_source_row = valid_df.sort_values(horizon, ascending=True).iloc[0]

    best_source = best_source_row["Source"]
    worst_source = worst_source_row["Source"]
    best_value = best_source_row[horizon]
    worst_value = worst_source_row[horizon]

    if best_source == worst_source:
        return (
            f"In the selected period, {best_source} is the only event source with enough forward return data. "
            f"The average {horizon.replace('Return ', '').replace(' %', '')} reaction is {best_value:,.2f}%."
        )

    return (
        f"In the selected period, {best_source} shows the strongest average {horizon.replace('Return ', '').replace(' %', '')} "
        f"reaction at {best_value:,.2f}%, while {worst_source} shows the weakest average reaction at {worst_value:,.2f}%."
    )



def _format_event_label(event_date, event_title, max_title_len: int = 46):
    event_date = pd.to_datetime(event_date, errors="coerce")

    if pd.isna(event_date):
        date_part = "-"
    else:
        date_part = event_date.strftime("%Y-%m-%d")

    title = str(event_title) if event_title is not None else "Event"
    title = title.strip()

    if len(title) > max_title_len:
        title = title[:max_title_len - 1] + "..."

    return f"{date_part} - {title}"



def calculate_cross_asset_event_impact(
    events_df: pd.DataFrame,
    asset_keys: list[str],
    start_date=None,
    end_date=None,
    horizons=(1, 7, 30, 90, 180, 365),
    assets_config=None,
    load_asset_data_func=None,
    include_approximate=False,
    return_load_report=False,
):
    """
    Calculates cross-asset forward returns after historical events.
    Output is long-form: one row per event + asset.
    """
    if events_df is None or events_df.empty:
        empty = pd.DataFrame()
        return (empty, empty.copy()) if return_load_report else empty

    if not asset_keys:
        empty = pd.DataFrame()
        return (empty, empty.copy()) if return_load_report else empty

    if assets_config is None or load_asset_data_func is None:
        empty = pd.DataFrame()
        return (empty, empty.copy()) if return_load_report else empty

    events = events_df.copy()
    if not include_approximate and "date_precision" in events.columns:
        events = events[events["date_precision"].eq("exact")].copy()
    events["event_date"] = pd.to_datetime(events["event_date"], errors="coerce")
    events = events.dropna(subset=["event_date"]).copy()

    if start_date is not None:
        events = events[events["event_date"] >= pd.to_datetime(start_date)].copy()

    if end_date is not None:
        events = events[events["event_date"] <= pd.to_datetime(end_date)].copy()

    events = events.sort_values("event_date").reset_index(drop=True)

    if events.empty:
        empty = pd.DataFrame()
        return (empty, empty.copy()) if return_load_report else empty

    rows = []
    load_rows = []

    for asset_key in asset_keys:
        if asset_key not in assets_config:
            load_rows.append({
                "asset": asset_key,
                "status": "failed",
                "rows": 0,
                "reason": "Asset is not configured",
            })
            continue

        asset_cfg = assets_config[asset_key]
        asset_name = asset_cfg.get("display_name", asset_key)

        try:
            extended_end_date = None

            if end_date is not None:
                extended_end_date = pd.to_datetime(end_date) + pd.Timedelta(days=max(horizons) + 10)

            price_df = load_asset_data_func(
                asset_key=asset_key,
                start_date=start_date,
                end_date=extended_end_date
            )
        except Exception as exc:
            load_rows.append({
                "asset": asset_key,
                "status": "failed",
                "rows": 0,
                "reason": str(exc),
            })
            continue

        if price_df is None or price_df.empty:
            load_rows.append({
                "asset": asset_key,
                "status": "empty",
                "rows": 0,
                "reason": "No price rows returned",
            })
            continue

        if "snapped_at" not in price_df.columns or "close" not in price_df.columns:
            load_rows.append({
                "asset": asset_key,
                "status": "failed",
                "rows": len(price_df),
                "reason": "Missing snapped_at or close column",
            })
            continue

        prices = price_df[["snapped_at", "close"]].copy()
        prices["snapped_at"] = pd.to_datetime(prices["snapped_at"], errors="coerce")
        prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
        prices = prices.dropna(subset=["snapped_at", "close"]).sort_values("snapped_at").reset_index(drop=True)

        if prices.empty:
            load_rows.append({
                "asset": asset_key,
                "status": "empty",
                "rows": 0,
                "reason": "No valid dated prices",
            })
            continue

        load_rows.append({
            "asset": asset_key,
            "status": "loaded",
            "rows": len(prices),
            "reason": "",
        })

        for _, event in events.iterrows():
            event_date = event["event_date"]
            base_rows = prices[prices["snapped_at"] >= event_date]

            row = {
                "Event Date": event_date.date(),
                "Event": event.get("event_title", "Event"),
                "Date Precision": event.get("date_precision", "exact"),
                "Category": event.get("event_category", "Uncategorized"),
                "Source": event.get("event_source_table", ""),
                "Description": event.get("event_description", ""),
                "Asset": asset_key,
                "Asset Name": asset_name,
            }

            if base_rows.empty:
                row["Market Date"] = pd.NaT
                row["Close at Event"] = np.nan

                for horizon in horizons:
                    row[f"Return +{horizon}D %"] = np.nan
                    row[f"Price +{horizon}D"] = np.nan

                rows.append(row)
                continue

            base_row = base_rows.iloc[0]
            base_date = base_row["snapped_at"]
            base_price = base_row["close"]

            row["Market Date"] = base_date.date()
            row["Close at Event"] = base_price

            for horizon in horizons:
                target_date = base_date + pd.Timedelta(days=int(horizon))
                future_rows = prices[prices["snapped_at"] >= target_date]

                if future_rows.empty or pd.isna(base_price) or base_price == 0:
                    row[f"Return +{horizon}D %"] = np.nan
                    row[f"Price +{horizon}D"] = np.nan
                else:
                    future_price = future_rows.iloc[0]["close"]
                    row[f"Return +{horizon}D %"] = ((future_price / base_price) - 1) * 100
                    row[f"Price +{horizon}D"] = future_price

            rows.append(row)

    result_df = pd.DataFrame(rows)

    load_report = pd.DataFrame(load_rows)

    if result_df.empty:
        return (result_df, load_report) if return_load_report else result_df

    numeric_cols = ["Close at Event"]

    for horizon in horizons:
        numeric_cols.extend([
            f"Return +{horizon}D %",
            f"Price +{horizon}D",
        ])

    for col in numeric_cols:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors="coerce").round(2)

    result_df["Event Label"] = result_df.apply(
        lambda row: _format_event_label(row.get("Event Date"), row.get("Event")),
        axis=1
    )

    preferred_cols = [
        "Event Date",
        "Event",
        "Date Precision",
        "Category",
        "Source",
        "Asset",
        "Asset Name",
        "Market Date",
        "Close at Event",
    ]

    for horizon in horizons:
        preferred_cols.append(f"Return +{int(horizon)}D %")

    preferred_cols.extend([
        "Event Label",
        "Description",
    ])

    existing_preferred_cols = [col for col in preferred_cols if col in result_df.columns]
    other_cols = [col for col in result_df.columns if col not in existing_preferred_cols]

    result_df = result_df[existing_preferred_cols + other_cols].copy()
    return (result_df, load_report) if return_load_report else result_df



def build_event_impact_matrix(cross_asset_df: pd.DataFrame, return_col: str):
    if cross_asset_df is None or cross_asset_df.empty:
        return pd.DataFrame()

    if return_col not in cross_asset_df.columns:
        return pd.DataFrame()

    matrix = cross_asset_df.pivot_table(
        index="Event Label",
        columns="Asset",
        values=return_col,
        aggfunc="mean"
    )

    return matrix.sort_index()



def calculate_event_category_asset_summary(cross_asset_df: pd.DataFrame, return_col: str):
    if cross_asset_df is None or cross_asset_df.empty:
        return pd.DataFrame()

    if return_col not in cross_asset_df.columns:
        return pd.DataFrame()

    summary = (
        cross_asset_df
        .groupby(["Category", "Asset"], as_index=False)
        .agg(
            Average_Return=(return_col, "mean"),
            Median_Return=(return_col, "median"),
            Events_Count=(return_col, "count")
        )
    )

    summary["Average_Return"] = pd.to_numeric(summary["Average_Return"], errors="coerce").round(2)
    summary["Median_Return"] = pd.to_numeric(summary["Median_Return"], errors="coerce").round(2)

    return summary.sort_values(["Category", "Asset"]).reset_index(drop=True)



def calculate_risk_on_off_snapshot(cross_asset_df: pd.DataFrame, return_col: str):
    if cross_asset_df is None or cross_asset_df.empty:
        return pd.DataFrame()

    if return_col not in cross_asset_df.columns:
        return pd.DataFrame()

    risk_assets = [
        asset for asset in ["SP500", "NASDAQ100", "DOWJONES", "STOXX600", "FTSE100", "BTC"]
        if asset in cross_asset_df["Asset"].unique()
    ]

    defensive_assets = [
        asset for asset in ["GOLD", "DXY", "US10Y", "VIX"]
        if asset in cross_asset_df["Asset"].unique()
    ]

    grouped = cross_asset_df.copy()
    grouped[return_col] = pd.to_numeric(grouped[return_col], errors="coerce")

    rows = []

    for event_label, part in grouped.groupby("Event Label"):
        event_info = part.iloc[0]

        risk_mean = part[part["Asset"].isin(risk_assets)][return_col].mean()
        defensive_mean = part[part["Asset"].isin(defensive_assets)][return_col].mean()

        if pd.isna(risk_mean) and pd.isna(defensive_mean):
            regime = "Insufficient Data"
        elif pd.notna(risk_mean) and risk_mean > 0 and (pd.isna(defensive_mean) or defensive_mean <= risk_mean):
            regime = "Risk-On"
        elif pd.notna(risk_mean) and risk_mean < 0 and pd.notna(defensive_mean) and defensive_mean > risk_mean:
            regime = "Risk-Off"
        else:
            regime = "Mixed"

        rows.append({
            "Event Date": event_info.get("Event Date"),
            "Event": event_info.get("Event"),
            "Category": event_info.get("Category"),
            "Risk Assets Avg Return %": risk_mean,
            "Defensive Assets Avg Return %": defensive_mean,
            "Risk/Defensive Spread %": risk_mean - defensive_mean if pd.notna(risk_mean) and pd.notna(defensive_mean) else np.nan,
            "Regime Read": regime,
        })

    snapshot_df = pd.DataFrame(rows)

    for col in [
        "Risk Assets Avg Return %",
        "Defensive Assets Avg Return %",
        "Risk/Defensive Spread %"
    ]:
        if col in snapshot_df.columns:
            snapshot_df[col] = pd.to_numeric(snapshot_df[col], errors="coerce").round(2)

    return snapshot_df.sort_values("Event Date").reset_index(drop=True)


def calculate_event_recovery_analysis(
    event: dict,
    asset_keys: list[str],
    assets_config: dict,
    load_asset_data_func,
    horizon_days: int = 365,
):
    """Measure drawdown and recovery from the first market price after an event."""
    if not event or event.get("date_precision", "exact") != "exact":
        return pd.DataFrame(), pd.DataFrame()

    event_date = pd.to_datetime(event.get("event_date"), errors="coerce")
    if pd.isna(event_date):
        return pd.DataFrame(), pd.DataFrame()

    end_date = event_date + pd.Timedelta(days=int(horizon_days))
    rows = []
    load_rows = []

    for asset_key in asset_keys:
        try:
            frame = load_asset_data_func(
                asset_key=asset_key,
                start_date=event_date - pd.Timedelta(days=7),
                end_date=end_date,
            )
        except Exception as exc:
            load_rows.append({"asset": asset_key, "status": "failed", "reason": str(exc)})
            continue

        if frame is None or frame.empty or "snapped_at" not in frame or "close" not in frame:
            load_rows.append({"asset": asset_key, "status": "empty", "reason": "No usable prices"})
            continue

        prices = frame[["snapped_at", "close"]].copy()
        prices["snapped_at"] = pd.to_datetime(prices["snapped_at"], errors="coerce")
        prices["close"] = pd.to_numeric(prices["close"], errors="coerce")
        prices = prices.dropna().sort_values("snapped_at")
        prices = prices[(prices["snapped_at"] >= event_date) & (prices["snapped_at"] <= end_date)]

        if prices.empty:
            load_rows.append({"asset": asset_key, "status": "empty", "reason": "No prices in event window"})
            continue

        base = prices.iloc[0]
        base_price = base["close"]
        path = prices.copy()
        path["return_from_event_pct"] = ((path["close"] / base_price) - 1) * 100
        trough = path.sort_values("return_from_event_pct").iloc[0]
        after_trough = path[path["snapped_at"] >= trough["snapped_at"]]
        recovered = after_trough[after_trough["close"] >= base_price]

        if recovered.empty:
            recovery_date = pd.NaT
            recovery_days = np.nan
            recovery_status = "Not recovered within window"
        else:
            recovery_date = recovered.iloc[0]["snapped_at"]
            recovery_days = int((recovery_date - base["snapped_at"]).days)
            recovery_status = "Recovered"

        rows.append(
            {
                "Asset": asset_key,
                "Asset Name": assets_config.get(asset_key, {}).get("display_name", asset_key),
                "Event Date": event_date.date(),
                "Market Date": base["snapped_at"].date(),
                "Event Price": base_price,
                "Trough Date": trough["snapped_at"].date(),
                "Max Drawdown %": trough["return_from_event_pct"],
                "Days to Trough": int((trough["snapped_at"] - base["snapped_at"]).days),
                "Recovery Date": recovery_date.date() if pd.notna(recovery_date) else None,
                "Recovery Days": recovery_days,
                "Recovery Status": recovery_status,
                "Window Days": int(horizon_days),
            }
        )
        load_rows.append({"asset": asset_key, "status": "loaded", "reason": ""})

    result = pd.DataFrame(rows)
    for column in ["Event Price", "Max Drawdown %"]:
        if column in result:
            result[column] = pd.to_numeric(result[column], errors="coerce").round(2)

    return result, pd.DataFrame(load_rows)
