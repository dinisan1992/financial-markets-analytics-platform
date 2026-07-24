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

START_DATE = "2020-01-01"
END_DATE = None

SELECTED_ASSETS = [
    "SP500",
    "NASDAQ100",
    "BTC",
    "GOLD",
    "DXY",
    "BRENT_OIL",
    "VIX",
    "US10Y"
]

EVENTS_TABLE = "world_historical_events"

USE_DATABASE_EVENTS = True

EXPORT_REPORT = True

pio.renderers.default = "browser"


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
# CARREGAR ATIVO
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
        f"{asset_key:20s} | "
        f"{display_name:40s} | "
        f"{len(df):7d} rows | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# LOAD ASSETS
# =========================

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
# VERIFICAR TABELA DE EVENTOS
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


# =========================
# DETETAR COLUNAS DE EVENTOS
# =========================

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

    print(f"\nEventos carregados da base de data: {len(df)}")
    print(f"Table: {EVENTS_TABLE}")

    return df


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

    print(f"\nManual events carregados: {len(df)}")

    return df


def load_events(start_date=None, end_date=None):
    if USE_DATABASE_EVENTS:
        try:
            df_events = load_events_database(
                start_date=start_date,
                end_date=end_date
            )

            if not df_events.empty:
                return df_events

            print("Warning: event table empty for the period. Using manual events.")

        except Exception as e:
            print(f"Warning: not foi possible load events da base: {e}")
            print("Using manual events.")

    return load_events_manual(
        start_date=start_date,
        end_date=end_date
    )


# =========================
# SUMMARY DE EVENTOS
# =========================

def mostrar_summary_events(df_events):
    print("\n" + "=" * 120)
    print("EVENTS USED IN THE OVERLAY")
    print("=" * 120)

    if df_events.empty:
        print("No events no period.")
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
    print(
        df_events["event_category"]
        .value_counts()
        .reset_index()
        .rename(
            columns={
                "index": "event_category",
                "event_category": "count"
            }
        )
    )

    print("=" * 120)


# =========================
# CHART
# =========================

def gerar_grafico_event_overlay(normalized_df, df_events):
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

    # Linha base 100
    fig.add_hline(
        y=100,
        line_dash="dash",
        opacity=0.5,
        annotation_text="Base 100",
        annotation_position="bottom right"
    )

    # Eventos
    max_y = normalized_df[asset_cols].max().max()
    min_y = normalized_df[asset_cols].min().min()

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
            text=event_title[:35],
            showarrow=True,
            arrowhead=2,
            ax=0,
            ay=-40,
            font=dict(
                size=10,
                color="white"
            ),
            bgcolor="rgba(0,0,0,0.65)",
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
                "Market Performance with Historical Event Overlay"
                f" | From {START_DATE if START_DATE else 'Start'}"
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
            r=260,
            t=120,
            b=70
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

def export_resultados(normalized_df, df_events):
    if not EXPORT_REPORT:
        return

    normalized_df.to_csv(
        "event_overlay_normalized_assets.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    df_events.to_csv(
        "event_overlay_events_used.csv",
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nReports exported:")
    print("event_overlay_normalized_assets.csv")
    print("event_overlay_events_used.csv")


# =========================
# MAIN
# =========================

def main():
    print("\nA iniciar Event Overlay Analysis...")
    print(f"Start date: {START_DATE}")
    print(f"End date: {END_DATE}")
    print(f"Assets: {SELECTED_ASSETS}")
    print(f"Usar events da base: {USE_DATABASE_EVENTS}")

    prices_df = load_assets(
        asset_keys=SELECTED_ASSETS,
        start_date=START_DATE,
        end_date=END_DATE
    )

    print("\nData combinados:")
    print(f"Rows: {len(prices_df)}")
    print(f"Minimum date: {prices_df['snapped_at'].min().date()}")
    print(f"Maximum date: {prices_df['snapped_at'].max().date()}")

    normalized_df = normalizar_base_100(prices_df)

    df_events = load_events(
        start_date=START_DATE,
        end_date=END_DATE
    )

    mostrar_summary_events(df_events)

    print("\nGenerating chart com events...")
    gerar_grafico_event_overlay(
        normalized_df=normalized_df,
        df_events=df_events
    )

    export_resultados(
        normalized_df=normalized_df,
        df_events=df_events
    )

    print("\nEvent Overlay Analysis completed.")


if __name__ == "__main__":
    main()
