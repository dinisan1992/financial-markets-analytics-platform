from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.graph_objects as go
import plotly.io as pio

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# SETTINGS
# =========================

EVENTS_TABLE = "world_historical_events"

EXPORT_REPORT = True

pio.renderers.default = "browser"


# =========================
# ASSET GROUPS
# =========================

ASSET_GROUPS = {
    "core_macro": {
        "name": "Core Macro View",
        "description": "SP500, Nasdaq, BTC, Gold, DXY, Brent, VIX, US10Y.",
        "assets": [
            "SP500",
            "NASDAQ100",
            "BTC",
            "GOLD",
            "DXY",
            "BRENT_OIL",
            "VIX",
            "US10Y"
        ]
    },

    "risk_assets": {
        "name": "Risk Assets",
        "description": "BTC and major US equity indices.",
        "assets": [
            "BTC",
            "SP500",
            "NASDAQ100",
            "DOWJONES",
            "RUSSELL2000"
        ]
    },

    "global_equities": {
        "name": "Global Equity Indices",
        "description": "Major global equity indices.",
        "assets": [
            "SP500",
            "NASDAQ100",
            "DOWJONES",
            "RUSSELL2000",
            "STOXX600",
            "EUROSTOXX50",
            "DAX",
            "CAC40",
            "FTSE100",
            "NIKKEI225",
            "SSECOMPOSITE",
            "EMERGING_MARKETS"
        ]
    },

    "commodities": {
        "name": "Commodities",
        "description": "Energy, metals and agricultural commodities.",
        "assets": [
            "GOLD",
            "SILVER",
            "BRENT_OIL",
            "WTI_OIL",
            "NATURAL_GAS",
            "COPPER",
            "WHEAT",
            "CORN"
        ]
    },

    "energy": {
        "name": "Energy",
        "description": "Oil and natural gas.",
        "assets": [
            "BRENT_OIL",
            "WTI_OIL",
            "NATURAL_GAS"
        ]
    },

    "safe_havens_fx": {
        "name": "Safe Havens / FX",
        "description": "Gold, US dollar, yen and Swiss franc.",
        "assets": [
            "GOLD",
            "DXY",
            "YEN",
            "SWISS_FRANC"
        ]
    },

    "stress": {
        "name": "Stress Indicators",
        "description": "VIX, MOVE, Financial Conditions and TED Spread.",
        "assets": [
            "VIX",
            "MOVE_INDEX",
            "FINANCIAL_CONDITIONS",
            "TED_SPREAD"
        ]
    },

    "yields": {
        "name": "Government Bond Yields",
        "description": "US, Germany, UK and Japan yields.",
        "assets": [
            "US2Y",
            "US10Y",
            "US30Y",
            "GERMANY10Y",
            "UK10Y",
            "JAPAN10Y"
        ]
    }
}


# =========================
# MANUAL FALLBACK EVENTS
# =========================

MANUAL_EVENTS = [
    {
        "event_date": "2020-03-11",
        "event_title": "WHO declares COVID-19 pandemic",
        "event_category": "Pandemic / Financial Stress",
        "event_description": "Global COVID-19 pandemic declaration."
    },
    {
        "event_date": "2020-03-23",
        "event_title": "Fed emergency support / market bottom",
        "event_category": "Monetary Policy / Liquidity",
        "event_description": "Major liquidity intervention period during COVID shock."
    },
    {
        "event_date": "2021-11-10",
        "event_title": "US inflation shock accelerates",
        "event_category": "Inflation Shock",
        "event_description": "Inflation pressure becomes dominant macro theme."
    },
    {
        "event_date": "2022-02-24",
        "event_title": "Russia invades Ukraine",
        "event_category": "Geopolitical / War / Energy",
        "event_description": "Major geopolitical and commodity shock."
    },
    {
        "event_date": "2022-06-15",
        "event_title": "Fed aggressive hiking cycle",
        "event_category": "Monetary Policy / Inflation",
        "event_description": "Period of aggressive rate hikes."
    },
    {
        "event_date": "2022-11-11",
        "event_title": "FTX collapse",
        "event_category": "Crypto Event / Financial Stress",
        "event_description": "Crypto market stress after FTX collapse."
    },
    {
        "event_date": "2023-03-10",
        "event_title": "Silicon Valley Bank collapse",
        "event_category": "Banking Stress",
        "event_description": "US regional banking stress episode."
    },
    {
        "event_date": "2023-10-07",
        "event_title": "Israel-Hamas war begins",
        "event_category": "Geopolitical / War / Energy",
        "event_description": "Geopolitical shock with potential energy market implications."
    },
    {
        "event_date": "2024-04-13",
        "event_title": "Iran-Israel escalation",
        "event_category": "Geopolitical / Energy",
        "event_description": "Middle East escalation risk."
    }
]


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# GROUP MENU
# =========================

def mostrar_menu_grupos():
    print("\n" + "=" * 110)
    print("EVENT OVERLAY SELECTOR - ASSET GROUPS")
    print("=" * 110)

    group_items = list(ASSET_GROUPS.items())

    for i, (group_key, group_data) in enumerate(group_items, start=1):
        print(
            f"{i:02d} - "
            f"{group_data['name']} "
            f"| {group_data['description']}"
        )

    print("=" * 110)
    print("98 - Custom group")
    print("0  - Exit")
    print("=" * 110)

    return group_items


def chooser_grupo(group_items):
    while True:
        choice = input("\nChoose the group: ").strip()

        if choice == "0":
            return None

        if choice == "98":
            return chooser_grupo_personalizado()

        if not choice.isdigit():
            print("Invalid choice. Enter the number only.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(group_items):
            print("Number outside the list.")
            continue

        return group_items[choice_num - 1]


def chooser_grupo_personalizado():
    print("\nAvailable assets:")
    print("-" * 100)

    asset_keys = list(ASSETS.keys())

    for i, asset_key in enumerate(asset_keys, start=1):
        asset = ASSETS[asset_key]
        print(
            f"{i:02d} - "
            f"{asset_key:22s} | "
            f"{asset['display_name']} | "
            f"{asset['market_type']}"
        )

    print("-" * 100)
    print("Choose several assets separated by commas.")
    print("Example: 1,3,5,8")

    while True:
        choice = input("\nAssets: ").strip()

        try:
            indices = [
                int(x.strip())
                for x in choice.split(",")
                if x.strip() != ""
            ]

            if not indices:
                raise ValueError("Empty list.")

            selected_assets = []

            for idx in indices:
                if idx < 1 or idx > len(asset_keys):
                    raise ValueError(f"Number outside the list: {idx}")

                selected_assets.append(asset_keys[idx - 1])

            selected_assets = list(dict.fromkeys(selected_assets))

            group_data = {
                "name": "Custom Asset Group",
                "description": "Custom group selected manually.",
                "assets": selected_assets
            }

            return "custom_group", group_data

        except Exception as e:
            print(f"Invalid choice: {e}")


# =========================
# PERIOD MENU
# =========================

def calcular_data_inicio_anos(anos):
    hoje = pd.Timestamp.today().normalize()
    data_inicio = hoje - pd.DateOffset(years=anos)

    return data_inicio.strftime("%Y-%m-%d")


def chooser_periodo_personalizado():
    print("\nRecommended format: YYYY-MM-DD")
    print("Example: 2015-01-01")

    while True:
        start_date = input("\nStart date: ").strip()

        try:
            pd.to_datetime(start_date)
            break

        except Exception:
            print("Invalid start date. Use the YYYY-MM-DD format.")

    end_date = input("End date or ENTER to use the end: ").strip()

    if end_date == "":
        end_date = None

    else:
        try:
            pd.to_datetime(end_date)

        except Exception:
            print("Invalid end date. Using the end.")
            end_date = None

    label = f"{start_date} until {end_date if end_date else 'end'}"

    return start_date, end_date, label


def chooser_periodo():
    print("\n" + "=" * 80)
    print("CHOOSE PERIOD")
    print("=" * 80)
    print("1 - Since 2020")
    print("2 - Last 1 year")
    print("3 - Last 3 years")
    print("4 - Last 5 years")
    print("5 - Last 10 years")
    print("6 - Full available history")
    print("7 - Custom date")
    print("=" * 80)

    while True:
        choice = input("\nChoose the period: ").strip()

        if choice == "1":
            return "2020-01-01", None, "Since 2020"

        elif choice == "2":
            return calcular_data_inicio_anos(1), None, "Last 1 year"

        elif choice == "3":
            return calcular_data_inicio_anos(3), None, "Last 3 years"

        elif choice == "4":
            return calcular_data_inicio_anos(5), None, "Last 5 years"

        elif choice == "5":
            return calcular_data_inicio_anos(10), None, "Last 10 years"

        elif choice == "6":
            return None, None, "Full history"

        elif choice == "7":
            return chooser_periodo_personalizado()

        else:
            print("Invalid choice. Enter a number from 1 to 7.")


# =========================
# EVENT SOURCE MENU
# =========================

def chooser_fonte_events():
    print("\n" + "=" * 80)
    print("CHOOSE EVENT SOURCE")
    print("=" * 80)
    print("1 - Use SQL database events")
    print("2 - Use manual fallback events")
    print("=" * 80)

    while True:
        choice = input("\nChoose a source: ").strip()

        if choice == "1":
            return "database", "SQL database"

        elif choice == "2":
            return "manual", "Manual events"

        else:
            print("Invalid choice. Enter 1 or 2.")


# =========================
# LOAD ASSETS
# =========================

def load_asset(asset_key, start_date=None, end_date=None):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Asset not found: {asset_key}")

    asset = ASSETS[asset_key]
    table_name = asset["table_name"]
    display_name = asset["display_name"]

    query = f"""
    SELECT
        snapped_at,
        price
    FROM `{table_name}`
    ORDER BY snapped_at;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        raise ValueError(f"Empty table: {table_name}")

    df["snapped_at"] = pd.to_datetime(
        df["snapped_at"],
        errors="coerce"
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    df = df.dropna(subset=["snapped_at", "price"])
    df = df.sort_values("snapped_at").reset_index(drop=True)

    if start_date is not None:
        df = df[df["snapped_at"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["snapped_at"] <= pd.to_datetime(end_date)]

    if df.empty:
        raise ValueError(f"No data after filters: {asset_key}")

    df = df[["snapped_at", "price"]].copy()
    df = df.rename(columns={"price": asset_key})

    print(
        f"{asset_key:22s} | "
        f"{display_name:40s} | "
        f"{len(df):7d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


def load_assets(asset_keys, start_date=None, end_date=None):
    merged_df = None

    print("\nLoading assets:")
    print("-" * 120)

    for asset_key in asset_keys:
        try:
            df_asset = load_asset(
                asset_key=asset_key,
                start_date=start_date,
                end_date=end_date
            )

            if merged_df is None:
                merged_df = df_asset

            else:
                merged_df = pd.merge(
                    merged_df,
                    df_asset,
                    on="snapped_at",
                    how="outer"
                )

        except Exception as e:
            print(f"ERROR in {asset_key}: {e}")

    if merged_df is None or merged_df.empty:
        raise ValueError("No asset was loaded.")

    merged_df = merged_df.sort_values("snapped_at").reset_index(drop=True)

    asset_cols = [
        col for col in merged_df.columns
        if col != "snapped_at"
    ]

    merged_df[asset_cols] = merged_df[asset_cols].ffill()

    return merged_df


# =========================
# NORMALIZE BASE 100
# =========================

def normalizar_base_100(df):
    normalized_df = pd.DataFrame()
    normalized_df["snapped_at"] = df["snapped_at"]

    asset_cols = [
        col for col in df.columns
        if col != "snapped_at"
    ]

    for col in asset_cols:
        series = df[col].copy()
        first_valid = series.dropna()

        if first_valid.empty:
            print(f"Warning: {col} has no valid values.")
            continue

        base_value = first_valid.iloc[0]

        if base_value == 0:
            print(f"Warning: {col} has a zero base value.")
            continue

        normalized_df[col] = (series / base_value) * 100

    return normalized_df


# =========================
# EVENTOS - DATABASE
# =========================

def tabela_existe(table_name):
    query = """
    SELECT COUNT(*)
    FROM information_schema.tables
    WHERE table_schema = :database
      AND table_name = :table_name;
    """

    with engine.begin() as conn:
        result = conn.execute(
            text(query),
            {
                "database": DB_CONFIG["database"],
                "table_name": table_name
            }
        ).fetchone()

    return result[0] > 0


def obter_columns_tabela(table_name):
    query = f"""
    SHOW COLUMNS FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return df["Field"].tolist()


def detectar_coluna(columns, candidatos):
    columns_lower = {
        col.lower(): col
        for col in columns
    }

    for candidato in candidatos:
        if candidato.lower() in columns_lower:
            return columns_lower[candidato.lower()]

    return None


def load_events_database(start_date=None, end_date=None):
    if not tabela_existe(EVENTS_TABLE):
        raise ValueError(f"Table does not exist: {EVENTS_TABLE}")

    columns = obter_columns_tabela(EVENTS_TABLE)

    date_col = detectar_coluna(
        columns,
        [
            "event_date",
            "date",
            "snapped_at",
            "event_datetime",
            "created_at"
        ]
    )

    title_col = detectar_coluna(
        columns,
        [
            "event_title",
            "title",
            "event",
            "name",
            "headline"
        ]
    )

    category_col = detectar_coluna(
        columns,
        [
            "event_category",
            "category",
            "type",
            "event_type"
        ]
    )

    description_col = detectar_coluna(
        columns,
        [
            "event_description",
            "description",
            "details",
            "notes"
        ]
    )

    if date_col is None:
        raise ValueError(
            f"No date column found in {EVENTS_TABLE}. "
            f"Available columns: {columns}"
        )

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
    FROM `{EVENTS_TABLE}`
    ORDER BY `{date_col}`;
    """

    df = pd.read_sql(query, engine)

    rename_map = {
        date_col: "event_date"
    }

    if title_col is not None:
        rename_map[title_col] = "event_title"

    if category_col is not None:
        rename_map[category_col] = "event_category"

    if description_col is not None:
        rename_map[description_col] = "event_description"

    df = df.rename(columns=rename_map)

    if "event_title" not in df.columns:
        df["event_title"] = "Historical event"

    if "event_category" not in df.columns:
        df["event_category"] = "Uncategorized"

    if "event_description" not in df.columns:
        df["event_description"] = ""

    df["event_date"] = pd.to_datetime(
        df["event_date"],
        errors="coerce"
    )

    df = df.dropna(subset=["event_date"])
    df = df.sort_values("event_date").reset_index(drop=True)

    if start_date is not None:
        df = df[df["event_date"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["event_date"] <= pd.to_datetime(end_date)]

    df = df.reset_index(drop=True)

    return df


# =========================
# EVENTOS - MANUAL
# =========================

def load_events_manual(start_date=None, end_date=None):
    df = pd.DataFrame(MANUAL_EVENTS)

    df["event_date"] = pd.to_datetime(
        df["event_date"],
        errors="coerce"
    )

    df = df.dropna(subset=["event_date"])
    df = df.sort_values("event_date").reset_index(drop=True)

    if start_date is not None:
        df = df[df["event_date"] >= pd.to_datetime(start_date)]

    if end_date is not None:
        df = df[df["event_date"] <= pd.to_datetime(end_date)]

    df = df.reset_index(drop=True)

    return df


def load_events(source, start_date=None, end_date=None):
    if source == "database":
        try:
            df_events = load_events_database(
                start_date=start_date,
                end_date=end_date
            )

            if not df_events.empty:
                print(f"\nEvents loaded from the SQL database: {len(df_events)}")
                return df_events

            print("Warning: no events in the database for the period. Using manual fallback.")
            return load_events_manual(
                start_date=start_date,
                end_date=end_date
            )

        except Exception as e:
            print(f"Warning: unable to load events from the SQL database: {e}")
            print("Using manual fallback.")

            return load_events_manual(
                start_date=start_date,
                end_date=end_date
            )

    print("\nUsing manual events.")
    return load_events_manual(
        start_date=start_date,
        end_date=end_date
    )


# =========================
# CATEGORY MENU
# =========================

def chooser_categorias_events(df_events):
    if df_events.empty:
        return df_events, "No events"

    categories = sorted(
        df_events["event_category"]
        .fillna("Uncategorized")
        .astype(str)
        .unique()
        .tolist()
    )

    print("\n" + "=" * 100)
    print("AVAILABLE EVENT CATEGORIES")
    print("=" * 100)

    for i, category in enumerate(categories, start=1):
        count = len(df_events[df_events["event_category"].astype(str) == category])

        print(
            f"{i:02d} - "
            f"{category} "
            f"({count} events)"
        )

    print("=" * 100)
    print("0 - Use all categories")
    print("=" * 100)

    choice = input(
        "\nChoose categories separated by commas "
        "or 0 for all: "
    ).strip()

    if choice == "0" or choice == "":
        return df_events, "All categories"

    try:
        indices = [
            int(x.strip())
            for x in choice.split(",")
            if x.strip() != ""
        ]

        selected_categories = []

        for idx in indices:
            if idx < 1 or idx > len(categories):
                raise ValueError(f"Number outside the list: {idx}")

            selected_categories.append(categories[idx - 1])

        selected_categories = list(dict.fromkeys(selected_categories))

        filtered_events = df_events[
            df_events["event_category"].astype(str).isin(selected_categories)
        ].reset_index(drop=True)

        label = ", ".join(selected_categories)

        return filtered_events, label

    except Exception as e:
        print(f"Invalid choice: {e}")
        print("A usar todas as categorias.")

        return df_events, "All categories"


# =========================
# SUMMARY
# =========================

def mostrar_summary_events(df_events):
    print("\n" + "=" * 120)
    print("EVENTS USED IN THE OVERLAY")
    print("=" * 120)

    if df_events.empty:
        print("No events in the selected period/categories.")
        return

    cols = [
        "event_date",
        "event_title",
        "event_category",
        "event_description"
    ]

    existing_cols = [
        col for col in cols
        if col in df_events.columns
    ]

    print(df_events[existing_cols])

    print("\nEvents by category:")
    category_counts = (
        df_events["event_category"]
        .value_counts()
        .reset_index()
    )

    category_counts.columns = [
        "event_category",
        "count"
    ]

    print(category_counts)

    print("=" * 120)


# =========================
# CHART
# =========================

def gerar_grafico_event_overlay(
    normalized_df,
    df_events,
    group_data,
    period_label,
    source_label,
    category_label
):
    fig = go.Figure()

    asset_cols = [
        col for col in normalized_df.columns
        if col != "snapped_at"
    ]

    for col in asset_cols:
        asset = ASSETS.get(col, {})
        display_name = asset.get("display_name", col)
        market_type = asset.get("market_type", "unknown")

        fig.add_trace(
            go.Scatter(
                x=normalized_df["snapped_at"],
                y=normalized_df[col],
                mode="lines",
                name=display_name,
                hovertemplate=(
                    f"<b>{display_name}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    "Base 100: %{y:.2f}<br>"
                    f"Type: {market_type}"
                    "<extra></extra>"
                )
            )
        )

    fig.add_hline(
        y=100,
        line_dash="dash",
        opacity=0.5,
        annotation_text="Base 100",
        annotation_position="bottom right"
    )

    if asset_cols:
        max_y = normalized_df[asset_cols].max().max()
    else:
        max_y = 100

    for _, event in df_events.iterrows():
        event_date = event["event_date"]
        event_title = str(event.get("event_title", "Event"))
        event_category = str(event.get("event_category", "Uncategorized"))
        event_description = str(event.get("event_description", ""))

        if event_date < normalized_df["snapped_at"].min():
            continue

        if event_date > normalized_df["snapped_at"].max():
            continue

        fig.add_vline(
            x=event_date,
            line_width=1,
            line_dash="dot",
            line_color="rgba(255,255,255,0.45)"
        )

        fig.add_annotation(
            x=event_date,
            y=max_y,
            text=event_title[:32],
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40,
            font=dict(
                size=10,
                color="white"
            ),
            bgcolor="rgba(0,0,0,0.72)",
            bordercolor="rgba(255,255,255,0.35)",
            borderwidth=1,
            hovertext=(
                f"<b>{event_title}</b><br>"
                f"Category: {event_category}<br>"
                f"Date: {event_date.date()}<br>"
                f"{event_description}"
            )
        )

    fig.update_layout(
        title=dict(
            text=(
                f"{group_data['name']} - Event Overlay"
                f" | {period_label}"
                f" | Events: {source_label}"
            ),
            x=0.5,
            xanchor="center",
            font=dict(
                size=20,
                color="white"
            )
        ),
        template="plotly_dark",
        height=900,
        width=1600,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Normalized Performance Base 100",
        margin=dict(
            l=80,
            r=270,
            t=125,
            b=75
        ),
        legend=dict(
            title="Assets",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(
                size=11,
                color="white"
            ),
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(255,255,255,0.25)",
            borderwidth=1
        ),
        annotations=[
            *list(fig.layout.annotations),
            dict(
                text=f"Categories: {category_label}",
                xref="paper",
                yref="paper",
                x=0,
                y=1.12,
                showarrow=False,
                font=dict(
                    size=11,
                    color="white"
                ),
                bgcolor="rgba(0,0,0,0.45)",
                bordercolor="rgba(255,255,255,0.25)",
                borderwidth=1
            )
        ],
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117"
    )

    fig.update_xaxes(
        rangeslider_visible=False,
        rangeselector=dict(
            bgcolor="#1E1E1E",
            activecolor="#4A90E2",
            bordercolor="#FFFFFF",
            borderwidth=1,
            font=dict(
                color="#FFFFFF",
                size=12
            ),
            x=0.01,
            y=1.08,
            buttons=list([
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(count=3, label="3Y", step="year", stepmode="backward"),
                dict(count=5, label="5Y", step="year", stepmode="backward"),
                dict(count=10, label="10Y", step="year", stepmode="backward"),
                dict(step="all", label="ALL")
            ])
        ),
        gridcolor="rgba(255,255,255,0.12)",
        tickfont=dict(color="white"),
        title_font=dict(color="white")
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.12)",
        tickfont=dict(color="white"),
        title_font=dict(color="white")
    )

    fig.show(
        config={
            "scrollZoom": True,
            "displayModeBar": True
        }
    )

    return fig


# =========================
# EXPORTAR
# =========================

def export_resultados(
    normalized_df,
    df_events,
    group_key,
    source_label,
    category_label
):
    if not EXPORT_REPORT:
        return

    safe_group = group_key.replace(" ", "_").replace("/", "_").lower()
    safe_source = source_label.replace(" ", "_").replace("/", "_").lower()
    safe_category = (
        category_label
        .replace(" ", "_")
        .replace("/", "_")
        .replace(",", "_")
        .lower()
    )[:80]

    normalized_output = (
        f"event_overlay_assets_{safe_group}_{safe_source}.csv"
    )

    events_output = (
        f"event_overlay_events_{safe_group}_{safe_source}_{safe_category}.csv"
    )

    normalized_df.to_csv(
        normalized_output,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    df_events.to_csv(
        events_output,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nReports exported:")
    print(normalized_output)
    print(events_output)


# =========================
# EXECUTAR
# =========================

def executar_event_overlay():
    group_items = mostrar_menu_grupos()

    selected_group = chooser_grupo(group_items)

    if selected_group is None:
        return False

    group_key, group_data = selected_group

    start_date, end_date, period_label = chooser_periodo()

    event_source, source_label = chooser_fonte_events()

    print("\n" + "=" * 120)
    print("EVENT OVERLAY ANALYSIS")
    print("=" * 120)
    print(f"Group: {group_data['name']}")
    print(f"Assets: {group_data['assets']}")
    print(f"Period: {period_label}")
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print(f"Fonte de events: {source_label}")
    print("=" * 120)

    prices_df = load_assets(
        asset_keys=group_data["assets"],
        start_date=start_date,
        end_date=end_date
    )

    print("\nData combinados:")
    print(f"Rows: {len(prices_df)}")
    print(f"Minimum date: {prices_df['snapped_at'].min().date()}")
    print(f"Maximum date: {prices_df['snapped_at'].max().date()}")

    normalized_df = normalizar_base_100(prices_df)

    df_events = load_events(
        source=event_source,
        start_date=start_date,
        end_date=end_date
    )

    df_events, category_label = chooser_categorias_events(df_events)

    mostrar_summary_events(df_events)

    print("\nGenerating chart com events...")

    gerar_grafico_event_overlay(
        normalized_df=normalized_df,
        df_events=df_events,
        group_data=group_data,
        period_label=period_label,
        source_label=source_label,
        category_label=category_label
    )

    export_resultados(
        normalized_df=normalized_df,
        df_events=df_events,
        group_key=group_key,
        source_label=source_label,
        category_label=category_label
    )

    print("\nEvent Overlay Analysis completed.")

    return True


# =========================
# MAIN
# =========================

def main():
    while True:
        print("\n" + "=" * 90)
        print("SELETOR DE EVENT OVERLAY ANALYSIS")
        print("=" * 90)
        print("1 - Executar Event Overlay")
        print("0 - Exit")
        print("=" * 90)

        choice = input("\nChoose an option: ").strip()

        if choice == "0":
            print("\nExiting the Event Overlay selector.")
            break

        elif choice == "1":
            try:
                continuar = executar_event_overlay()

                if not continuar:
                    continue

            except Exception as e:
                print("\nERROR while running Event Overlay:")
                print(e)

            input("\nPressiona ENTER para voltar ao menu...")

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
