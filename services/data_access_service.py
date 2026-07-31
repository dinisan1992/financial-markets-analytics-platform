import pandas as pd


EVENT_COLUMNS = [
    "event_date",
    "date_precision",
    "event_title",
    "event_category",
    "event_description",
    "event_source_table",
]


def empty_events_frame():
    return pd.DataFrame(columns=EVENT_COLUMNS)


def get_table_columns(engine, table_name):
    query = f"SHOW COLUMNS FROM `{table_name}`;"
    columns_df = pd.read_sql(query, engine)

    return columns_df["Field"].tolist()


def detect_column(columns, candidates):
    columns_lower = {
        col.lower(): col
        for col in columns
    }

    for candidate in candidates:
        if candidate.lower() in columns_lower:
            return columns_lower[candidate.lower()]

    return None


def table_exists(engine, table_name):
    query = """
    SELECT COUNT(*) AS table_exists
    FROM information_schema.tables
    WHERE table_schema = DATABASE()
      AND table_name = %s;
    """

    df = pd.read_sql(query, engine, params=(table_name,))

    return int(df["table_exists"].iloc[0]) > 0


def load_events_from_table(
    engine,
    table_name,
    start_date=None,
    end_date=None,
    table_exists_func=None,
    get_table_columns_func=None,
):
    exists = table_exists_func or (lambda table: table_exists(engine, table))
    columns_loader = get_table_columns_func or (lambda table: get_table_columns(engine, table))

    if not exists(table_name):
        return empty_events_frame()

    columns = columns_loader(table_name)

    if table_name == "world_historical_events":
        return _load_world_historical_events(
            engine=engine,
            start_date=start_date,
            end_date=end_date,
        )

    return _load_generic_events_table(
        engine=engine,
        table_name=table_name,
        columns=columns,
        start_date=start_date,
        end_date=end_date,
    )


def _load_world_historical_events(engine, start_date=None, end_date=None):
    query = """
    SELECT
        `year`,
        `event`,
        `macro_impact`,
        `affected_markets`
    FROM `world_historical_events`
    WHERE `year` IS NOT NULL
    ORDER BY `year`;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        return empty_events_frame()

    df["event_date"] = pd.to_datetime(
        df["year"].astype(str) + "-01-01",
        errors="coerce",
    )

    df["event_title"] = df["event"].astype(str)
    df["date_precision"] = "year"
    df["event_category"] = "World / Geopolitical"
    df["event_description"] = (
        "Macro impact: "
        + df["macro_impact"].fillna("").astype(str)
        + " | Affected markets: "
        + df["affected_markets"].fillna("").astype(str)
    )
    df["event_source_table"] = "world_historical_events"

    return _filter_and_format_events(df, start_date=start_date, end_date=end_date)


def _load_generic_events_table(engine, table_name, columns, start_date=None, end_date=None):
    date_col = detect_column(
        columns,
        [
            "event_date",
            "date",
            "snapped_at",
            "event_datetime",
            "created_at",
            "published_at",
        ],
    )

    title_col = detect_column(
        columns,
        [
            "event_title",
            "title",
            "event",
            "name",
            "headline",
        ],
    )

    category_col = detect_column(
        columns,
        [
            "event_category",
            "category",
            "type",
            "event_type",
        ],
    )

    description_col = detect_column(
        columns,
        [
            "event_description",
            "description",
            "details",
            "notes",
            "content",
            "macro_impact",
            "affected_markets",
        ],
    )

    if date_col is None:
        return empty_events_frame()

    select_cols = [date_col]

    if title_col is not None:
        select_cols.append(title_col)

    if category_col is not None:
        select_cols.append(category_col)

    if description_col is not None:
        select_cols.append(description_col)

    select_clause = ", ".join([f"`{col}`" for col in select_cols])

    query = f"""
    SELECT {select_clause}
    FROM `{table_name}`
    WHERE `{date_col}` IS NOT NULL
    ORDER BY `{date_col}`;
    """

    df = pd.read_sql(query, engine)

    rename_map = {
        date_col: "event_date",
    }

    if title_col is not None:
        rename_map[title_col] = "event_title"

    if category_col is not None:
        rename_map[category_col] = "event_category"

    if description_col is not None:
        rename_map[description_col] = "event_description"

    df = df.rename(columns=rename_map)

    if "event_title" not in df.columns:
        df["event_title"] = "Event"

    df["date_precision"] = "exact"

    if "event_category" not in df.columns:
        df["event_category"] = table_name

    if "event_description" not in df.columns:
        df["event_description"] = ""

    df["event_source_table"] = table_name

    return _filter_and_format_events(df, start_date=start_date, end_date=end_date)


def _filter_and_format_events(df, start_date=None, end_date=None):
    if df.empty:
        return empty_events_frame()

    df["event_date"] = pd.to_datetime(
        df["event_date"],
        errors="coerce",
    )

    df = df.dropna(subset=["event_date"]).copy()

    if start_date is not None:
        df = df[df["event_date"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["event_date"] <= pd.to_datetime(end_date)]

    df = df[EVENT_COLUMNS].copy()
    df = df.sort_values("event_date").reset_index(drop=True)

    return df


def load_asset_events(load_events_from_table_func, start_date=None, end_date=None):
    event_frames = []

    btc_events = load_events_from_table_func(
        table_name="bitcoin_historical_events",
        start_date=start_date,
        end_date=end_date,
    )

    if not btc_events.empty:
        event_frames.append(btc_events)

    world_events = load_events_from_table_func(
        table_name="world_historical_events",
        start_date=start_date,
        end_date=end_date,
    )

    if not world_events.empty:
        event_frames.append(world_events)

    if not event_frames:
        return empty_events_frame()

    events_df = pd.concat(event_frames, ignore_index=True)

    events_df = events_df.drop_duplicates(
        subset=[
            "event_date",
            "event_title",
            "event_source_table",
        ]
    )

    events_df = events_df.sort_values("event_date").reset_index(drop=True)

    return events_df


def load_asset_data(
    engine,
    assets_config,
    asset_key,
    start_date=None,
    end_date=None,
    get_table_columns_func=None,
):
    asset_cfg = assets_config[asset_key]
    table_name = asset_cfg["table_name"]

    columns_loader = get_table_columns_func or (lambda table: get_table_columns(engine, table))
    columns = columns_loader(table_name)

    date_col = detect_column(
        columns,
        [
            "snapped_at",
            "date",
            "datetime",
            "timestamp",
        ],
    )

    if date_col is None:
        raise ValueError(f"The table {table_name} does not have a recognized date column.")

    query = f"""
    SELECT *
    FROM `{table_name}`
    WHERE `{date_col}` IS NOT NULL
    """

    params = []

    if start_date is not None:
        query += f" AND `{date_col}` >= %s"
        params.append(start_date)

    if end_date is not None:
        query += f" AND `{date_col}` <= %s"
        params.append(end_date)

    query += f" ORDER BY `{date_col}` ASC"

    df = pd.read_sql(query, engine, params=tuple(params))

    if df.empty:
        return df

    if date_col != "snapped_at":
        df = df.rename(columns={date_col: "snapped_at"})

    df["snapped_at"] = pd.to_datetime(
        df["snapped_at"],
        errors="coerce",
    )

    df = df.dropna(subset=["snapped_at"]).copy()
    df = df.sort_values("snapped_at").reset_index(drop=True)

    if "close" not in df.columns and "price" in df.columns:
        df["close"] = pd.to_numeric(df["price"], errors="coerce")

    return df


def load_fed_macro_pair(
    engine,
    align_macro_func,
    macro_key,
    market_asset,
    start_date,
    end_date,
):
    return align_macro_func(
        macro_key=macro_key,
        market_asset=market_asset,
        engine=engine,
        start_date=start_date,
        end_date=end_date,
        how="outer",
        forward_fill=True,
    )


def load_euro_macro_pair(
    engine,
    align_euro_func,
    euro_series_key,
    market_asset,
    start_date,
    end_date,
):
    return align_euro_func(
        euro_series_key=euro_series_key,
        market_asset=market_asset,
        engine=engine,
        start_date=start_date,
        end_date=end_date,
        how="outer",
        forward_fill=True,
    )
