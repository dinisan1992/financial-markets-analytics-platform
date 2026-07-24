from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine
import plotly.graph_objects as go
import plotly.io as pio

from config import DB_CONFIG, get_sqlalchemy_database_url
from asset_config import ASSETS


# =========================
# GENERAL SETTINGS
# =========================

DEFAULT_WINDOWS = [30, 90, 180]
MIN_PERIODS_RATIO = 0.7
EXPORT_REPORT = True

pio.renderers.default = "browser"


# =========================
# PARES PREDEFINIDOS
# =========================

PAIR_CONFIGS = {
    "btc_nasdaq": {
        "name": "BTC vs NASDAQ 100",
        "asset_a": "BTC",
        "asset_b": "NASDAQ100",
        "description": "Relationship between Bitcoin and technology/risk assets."
    },

    "btc_gold": {
        "name": "BTC vs Gold",
        "asset_a": "BTC",
        "asset_b": "GOLD",
        "description": "Bitcoin comparado com ouro como possible reserva de valor."
    },

    "btc_dxy": {
        "name": "BTC vs DXY",
        "asset_a": "BTC",
        "asset_b": "DXY",
        "description": "Bitcoin vs dollar strength."
    },

    "sp500_vix": {
        "name": "S&P 500 vs VIX",
        "asset_a": "SP500",
        "asset_b": "VIX",
        "description": "Equities americanas contra volatilidade/stress."
    },

    "nasdaq_us10y": {
        "name": "NASDAQ 100 vs US 10Y",
        "asset_a": "NASDAQ100",
        "asset_b": "US10Y",
        "description": "Tecnologia/growth stocks contra yields longas."
    },

    "gold_dxy": {
        "name": "Gold vs DXY",
        "asset_a": "GOLD",
        "asset_b": "DXY",
        "description": "Gold vs dollar."
    },

    "brent_dxy": {
        "name": "Brent Oil vs DXY",
        "asset_a": "BRENT_OIL",
        "asset_b": "DXY",
        "description": "Brent oil vs dollar."
    },

    "brent_us10y": {
        "name": "Brent Oil vs US 10Y",
        "asset_a": "BRENT_OIL",
        "asset_b": "US10Y",
        "description": "Brent oil vs long yields."
    },

    "sp500_us10y": {
        "name": "S&P 500 vs US 10Y",
        "asset_a": "SP500",
        "asset_b": "US10Y",
        "description": "Equities americanas contra yields longas."
    },

    "gold_us10y": {
        "name": "Gold vs US 10Y",
        "asset_a": "GOLD",
        "asset_b": "US10Y",
        "description": "Ouro contra yields longas."
    },

    "vix_us10y": {
        "name": "VIX vs US 10Y",
        "asset_a": "VIX",
        "asset_b": "US10Y",
        "description": "Volatilidade acionista contra yields longas."
    },

    "vix_move": {
        "name": "VIX vs MOVE Index",
        "asset_a": "VIX",
        "asset_b": "MOVE_INDEX",
        "description": "Volatilidade acionista contra volatilidade obrigacionista."
    },

    "dxy_yen": {
        "name": "DXY vs Yen",
        "asset_a": "DXY",
        "asset_b": "YEN",
        "description": "Dollar vs yen."
    },

    "dxy_swiss_franc": {
        "name": "DXY vs Swiss Franc",
        "asset_a": "DXY",
        "asset_b": "SWISS_FRANC",
        "description": "Dollar vs Swiss franc."
    },

    "copper_nasdaq": {
        "name": "Copper vs NASDAQ 100",
        "asset_a": "COPPER",
        "asset_b": "NASDAQ100",
        "description": "Copper as an economic-cycle proxy vs technology."
    },

    "oil_gold": {
        "name": "Brent Oil vs Gold",
        "asset_a": "BRENT_OIL",
        "asset_b": "GOLD",
        "description": "Energy vs safe-haven asset."
    }
}


# =========================
# DATABASE CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# MENU DE PARES
# =========================

def mostrar_menu_pares():
    print("\n" + "=" * 110)
    print("SELETOR DE ROLLING CORRELATION - PARES DE MERCADO")
    print("=" * 110)

    pair_items = list(PAIR_CONFIGS.items())

    for i, (pair_key, pair_data) in enumerate(pair_items, start=1):
        print(
            f"{i:02d} - "
            f"{pair_data['name']} "
            f"| {pair_data['description']}"
        )

    print("=" * 110)
    print("98 - Par personalizado")
    print("0  - Exit")
    print("=" * 110)

    return pair_items


def chooser_par(pair_items):
    while True:
        choice = input("\nChoose the number for par: ").strip()

        if choice == "0":
            return None

        if choice == "98":
            return chooser_par_personalizado()

        if not choice.isdigit():
            print("Invalid choice. Enter the number only.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(pair_items):
            print("Number outside the list.")
            continue

        return pair_items[choice_num - 1]


def chooser_par_personalizado():
    print("\nAvailable assets:")
    print("-" * 80)

    asset_keys = list(ASSETS.keys())

    for i, asset_key in enumerate(asset_keys, start=1):
        asset = ASSETS[asset_key]
        print(
            f"{i:02d} - "
            f"{asset_key:20s} | "
            f"{asset['display_name']} | "
            f"{asset['market_type']}"
        )

    print("-" * 80)

    asset_a = chooser_asset_key(asset_keys, "primeiro asset")
    asset_b = chooser_asset_key(asset_keys, "segundo asset")

    pair_key = f"custom_{asset_a.lower()}_{asset_b.lower()}"

    pair_data = {
        "name": f"{ASSETS[asset_a]['display_name']} vs {ASSETS[asset_b]['display_name']}",
        "asset_a": asset_a,
        "asset_b": asset_b,
        "description": "Par personalizado escolhido manualmente."
    }

    return pair_key, pair_data


def chooser_asset_key(asset_keys, label):
    while True:
        choice = input(f"\nChoose the number for {label}: ").strip()

        if not choice.isdigit():
            print("Invalid choice. Enter the number only.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(asset_keys):
            print("Number outside the list.")
            continue

        return asset_keys[choice_num - 1]


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
# MENU DE JANELAS
# =========================

def chooser_janelas():
    print("\n" + "=" * 80)
    print("ESCOLHER JANELAS ROLLING")
    print("=" * 80)
    print("1 - 30, 90, 180 dias")
    print("2 - 30 e 90 dias")
    print("3 - 90 e 180 dias")
    print("4 - 60, 120, 252 dias")
    print("5 - 252 dias")
    print("6 - Personalizado")
    print("=" * 80)

    while True:
        choice = input("\nChoose as janelas: ").strip()

        if choice == "1":
            return [30, 90, 180], "30/90/180D"

        elif choice == "2":
            return [30, 90], "30/90D"

        elif choice == "3":
            return [90, 180], "90/180D"

        elif choice == "4":
            return [60, 120, 252], "60/120/252D"

        elif choice == "5":
            return [252], "252D"

        elif choice == "6":
            return chooser_janelas_personalizadas()

        else:
            print("Invalid choice. Enter a number de 1 a 6.")


def chooser_janelas_personalizadas():
    print("\nEnter windows separated by commas.")
    print("Example: 20,60,120")

    while True:
        texto = input("\nJanelas: ").strip()

        try:
            windows = [
                int(x.strip())
                for x in texto.split(",")
                if x.strip() != ""
            ]

            windows = sorted(list(set(windows)))

            if not windows:
                raise ValueError("Empty list.")

            if any(w < 2 for w in windows):
                raise ValueError("As janelas devem ser >= 2.")

            label = "/".join([f"{w}D" for w in windows])

            return windows, label

        except Exception as e:
            print(f"Janelas invalid: {e}")


# =========================
# LOAD PRICES
# =========================

def load_precos(asset_key, start_date=None, end_date=None):
    asset_key = asset_key.upper()

    if asset_key not in ASSETS:
        raise ValueError(f"Asset not found in ASSETS: {asset_key}")

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

    df = pd.read_sql(
        query,
        engine
    )

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
        f"{len(df):7d} prices | "
        f"{df['snapped_at'].min().date()} -> {df['snapped_at'].max().date()}"
    )

    return df


# =========================
# PREPARAR RETORNOS DO PAR
# =========================

def preparar_returns_par(asset_a, asset_b, start_date=None, end_date=None):
    print("\n" + "=" * 100)
    print(f"A preparar par: {asset_a} vs {asset_b}")
    print("=" * 100)

    df_a = load_precos(
        asset_key=asset_a,
        start_date=start_date,
        end_date=end_date
    )

    df_b = load_precos(
        asset_key=asset_b,
        start_date=start_date,
        end_date=end_date
    )

    merged = pd.merge(
        df_a,
        df_b,
        on="snapped_at",
        how="inner"
    )

    merged = merged.sort_values("snapped_at").reset_index(drop=True)

    if merged.empty:
        raise ValueError(
            f"Sem datas comuns para {asset_a} vs {asset_b}"
        )

    merged[f"{asset_a}_return"] = merged[asset_a].pct_change()
    merged[f"{asset_b}_return"] = merged[asset_b].pct_change()

    returns_df = merged[
        [
            "snapped_at",
            f"{asset_a}_return",
            f"{asset_b}_return"
        ]
    ].copy()

    returns_df = returns_df.dropna().reset_index(drop=True)

    print(f"Datas comuns: {len(merged)}")
    print(f"Returns valid: {len(returns_df)}")
    print(f"Common minimum date: {returns_df['snapped_at'].min().date()}")
    print(f"Common maximum date: {returns_df['snapped_at'].max().date()}")

    return returns_df


# =========================
# CALCULAR ROLLING CORRELATION
# =========================

def calcular_rolling_correlation(returns_df, asset_a, asset_b, rolling_windows):
    df = returns_df.copy()

    col_a = f"{asset_a}_return"
    col_b = f"{asset_b}_return"

    for window in rolling_windows:
        min_periods = max(
            2,
            int(window * MIN_PERIODS_RATIO)
        )

        corr_col = f"rolling_corr_{window}d"

        df[corr_col] = (
            df[col_a]
            .rolling(
                window=window,
                min_periods=min_periods
            )
            .corr(df[col_b])
        )

    return df


# =========================
# SUMMARY
# =========================

def resumir_rolling_corr(df, pair_label):
    corr_cols = [
        col for col in df.columns
        if col.startswith("rolling_corr_")
    ]

    rows = []

    for col in corr_cols:
        series = df[col].dropna()

        if series.empty:
            continue

        rows.append({
            "pair": pair_label,
            "window": col.replace("rolling_corr_", "").replace("d", ""),
            "observations": len(series),
            "mean_corr": round(series.mean(), 4),
            "median_corr": round(series.median(), 4),
            "min_corr": round(series.min(), 4),
            "max_corr": round(series.max(), 4),
            "latest_corr": round(series.iloc[-1], 4),
            "positive_pct": round((series > 0).mean() * 100, 2),
            "negative_pct": round((series < 0).mean() * 100, 2)
        })

    summary_df = pd.DataFrame(rows)

    print("\n" + "=" * 100)
    print("SUMMARY ROLLING CORRELATION")
    print("=" * 100)
    print(summary_df)
    print("=" * 100)

    return summary_df


# =========================
# GENERATE CHART
# =========================

def gerar_grafico_par(df, pair_label, period_label, windows_label):
    fig = go.Figure()

    corr_cols = [
        col for col in df.columns
        if col.startswith("rolling_corr_")
    ]

    for col in corr_cols:
        window_label = col.replace("rolling_corr_", "").replace("d", "")

        fig.add_trace(
            go.Scatter(
                x=df["snapped_at"],
                y=df[col],
                mode="lines",
                name=f"{window_label}D Rolling Corr",
                hovertemplate=(
                    f"<b>{pair_label}</b><br>"
                    "Date: %{x|%Y-%m-%d}<br>"
                    f"Window: {window_label}D<br>"
                    "Correlation: %{y:.3f}"
                    "<extra></extra>"
                )
            )
        )

    fig.add_hline(
        y=0,
        line_dash="dash",
        opacity=0.75,
        annotation_text="Zero correlation",
        annotation_position="bottom right"
    )

    fig.add_hline(
        y=0.5,
        line_dash="dot",
        opacity=0.35,
        annotation_text="+0.5",
        annotation_position="top right"
    )

    fig.add_hline(
        y=-0.5,
        line_dash="dot",
        opacity=0.35,
        annotation_text="-0.5",
        annotation_position="bottom right"
    )

    fig.update_layout(
        title=dict(
            text=(
                f"Rolling Correlation - {pair_label}"
                f" | {period_label}"
                f" | Windows: {windows_label}"
            ),
            x=0.5,
            xanchor="center",
            font=dict(
                size=19,
                color="white"
            )
        ),
        template="plotly_dark",
        height=750,
        width=1450,
        hovermode="x unified",
        xaxis_title="Date",
        yaxis_title="Rolling Correlation",
        yaxis=dict(
            range=[-1, 1]
        ),
        margin=dict(
            l=80,
            r=190,
            t=110,
            b=70
        ),
        legend=dict(
            title="Windows",
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
            y=1.09,
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
# EXPORTAR RESULTADOS
# =========================

def export_resultados(rolling_df, summary_df, pair_key):
    if not EXPORT_REPORT:
        return

    safe_pair_key = pair_key.replace(" ", "_").replace("/", "_").lower()

    rolling_output = f"rolling_correlation_{safe_pair_key}.csv"
    summary_output = f"rolling_correlation_summary_{safe_pair_key}.csv"

    rolling_df.to_csv(
        rolling_output,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    summary_df.to_csv(
        summary_output,
        index=False,
        sep=";",
        encoding="utf-8-sig"
    )

    print("\nReports exported:")
    print(rolling_output)
    print(summary_output)


# =========================
# EXECUTAR PAR
# =========================

def executar_par(pair_key, pair_data):
    start_date, end_date, period_label = chooser_periodo()
    rolling_windows, windows_label = chooser_janelas()

    asset_a = pair_data["asset_a"]
    asset_b = pair_data["asset_b"]
    pair_label = pair_data["name"]

    print("\n" + "=" * 110)
    print(f"PAR: {pair_label}")
    print(f"Description: {pair_data['description']}")
    print(f"Asset A: {asset_a} | {ASSETS[asset_a]['display_name']}")
    print(f"Asset B: {asset_b} | {ASSETS[asset_b]['display_name']}")
    print(f"Period: {period_label}")
    print(f"Start date: {start_date}")
    print(f"End date: {end_date}")
    print(f"Janelas: {rolling_windows}")
    print("=" * 110)

    returns_df = preparar_returns_par(
        asset_a=asset_a,
        asset_b=asset_b,
        start_date=start_date,
        end_date=end_date
    )

    rolling_df = calcular_rolling_correlation(
        returns_df=returns_df,
        asset_a=asset_a,
        asset_b=asset_b,
        rolling_windows=rolling_windows
    )

    summary_df = resumir_rolling_corr(
        df=rolling_df,
        pair_label=pair_label
    )

    gerar_grafico_par(
        df=rolling_df,
        pair_label=pair_label,
        period_label=period_label,
        windows_label=windows_label
    )

    export_resultados(
        rolling_df=rolling_df,
        summary_df=summary_df,
        pair_key=pair_key
    )

    print("\nRolling correlation completed.")


# =========================
# MAIN
# =========================

def main():
    while True:
        pair_items = mostrar_menu_pares()

        selected_pair = chooser_par(pair_items)

        if selected_pair is None:
            print("\nExiting the rolling correlation selector.")
            break

        pair_key, pair_data = selected_pair

        try:
            executar_par(pair_key, pair_data)

        except Exception as e:
            print("\nERROR while running pair:")
            print(e)

        input("\nPressiona ENTER para voltar ao menu...")


if __name__ == "__main__":
    main()
