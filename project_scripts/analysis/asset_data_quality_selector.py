from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine

from config import get_sqlalchemy_database_url
from asset_config import ASSETS
from analysis_groups import ASSET_GROUPS


# =========================
# SETTINGS
# =========================

EXTREME_RETURN_THRESHOLD = 0.20
EXPORT_REPORT = True


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# MENU
# =========================

def mostrar_menu():
    print("\n" + "=" * 100)
    print("SELETOR DE DATA QUALITY")
    print("=" * 100)
    print("1 - Validar todos os assets")
    print("2 - Validar grupo de assets")
    print("3 - Validar asset individual")
    print("0 - Exit")
    print("=" * 100)


def mostrar_menu_grupos():
    print("\n" + "=" * 110)
    print("AVAILABLE GROUPS")
    print("=" * 110)

    group_items = list(ASSET_GROUPS.items())

    for i, (group_key, group_data) in enumerate(group_items, start=1):
        print(
            f"{i:02d} - "
            f"{group_data['name']} "
            f"| {group_data['description']}"
        )

    print("=" * 110)

    return group_items


def chooser_grupo():
    group_items = mostrar_menu_grupos()

    while True:
        choice = input("\nChoose the group: ").strip()

        if not choice.isdigit():
            print("Invalid choice.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(group_items):
            print("Number outside the list.")
            continue

        group_key, group_data = group_items[choice_num - 1]

        return group_key, group_data


def chooser_asset_individual():
    asset_keys = list(ASSETS.keys())

    print("\n" + "=" * 110)
    print("AVAILABLE ASSETS")
    print("=" * 110)

    for i, asset_key in enumerate(asset_keys, start=1):
        asset = ASSETS[asset_key]

        print(
            f"{i:02d} - "
            f"{asset_key:22s} | "
            f"{asset['display_name']} | "
            f"{asset['market_type']}"
        )

    print("=" * 110)

    while True:
        choice = input("\nChoose the asset: ").strip()

        if not choice.isdigit():
            print("Invalid choice.")
            continue

        choice_num = int(choice)

        if choice_num < 1 or choice_num > len(asset_keys):
            print("Number outside the list.")
            continue

        return asset_keys[choice_num - 1]


# =========================
# CARREGAR DADOS
# =========================

def load_data(asset_key):
    asset = ASSETS[asset_key]
    table_name = asset["table_name"]

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

    df = df.sort_values("snapped_at").reset_index(drop=True)

    return df


# =========================
# VALIDAR ATIVO
# =========================

def validar_asset(asset_key):
    asset = ASSETS[asset_key]

    table_name = asset["table_name"]
    display_name = asset["display_name"]
    market_type = asset["market_type"]

    print("\n" + "=" * 110)
    print(f"A validar: {asset_key} | {display_name} | {table_name}")
    print("=" * 110)

    df = load_data(asset_key)

    total_rows = len(df)

    null_dates = df["snapped_at"].isna().sum()
    null_prices = df["price"].isna().sum()

    duplicate_dates = df["snapped_at"].duplicated().sum()

    valid_df = df.dropna(subset=["snapped_at", "price"]).copy()
    valid_df = valid_df.sort_values("snapped_at").reset_index(drop=True)

    if valid_df.empty:
        raise ValueError(f"No valid data: {asset_key}")

    min_date = valid_df["snapped_at"].min()
    max_date = valid_df["snapped_at"].max()

    zero_prices = (valid_df["price"] == 0).sum()
    negative_prices = (valid_df["price"] < 0).sum()

    valid_df["daily_return"] = valid_df["price"].pct_change()

    valid_df["price_repeated"] = (
        valid_df["price"] == valid_df["price"].shift(1)
    )

    repeated_price_days = valid_df["price_repeated"].sum()

    repeated_price_pct = (
        repeated_price_days / len(valid_df) * 100
        if len(valid_df) > 0
        else 0
    )

    extreme_returns_df = valid_df[
        valid_df["daily_return"].abs() > EXTREME_RETURN_THRESHOLD
    ].copy()

    extreme_returns = len(extreme_returns_df)

    max_daily_return = valid_df["daily_return"].max()
    min_daily_return = valid_df["daily_return"].min()

    max_return_date = None
    min_return_date = None

    if pd.notna(max_daily_return):
        max_return_date = valid_df.loc[
            valid_df["daily_return"].idxmax(),
            "snapped_at"
        ]

    if pd.notna(min_daily_return):
        min_return_date = valid_df.loc[
            valid_df["daily_return"].idxmin(),
            "snapped_at"
        ]

    first_price = valid_df["price"].iloc[0]
    last_price = valid_df["price"].iloc[-1]

    total_return_pct = None

    if first_price != 0 and pd.notna(first_price):
        total_return_pct = ((last_price / first_price) - 1) * 100

    warning_flags = []

    if null_prices > 0:
        warning_flags.append("null_prices")

    if null_dates > 0:
        warning_flags.append("null_dates")

    if duplicate_dates > 0:
        warning_flags.append("duplicate_dates")

    if zero_prices > 0:
        warning_flags.append("zero_prices")

    if negative_prices > 0:
        warning_flags.append("negative_prices")

    if repeated_price_pct > 20:
        warning_flags.append("many_repeated_prices")

    if extreme_returns > 0:
        warning_flags.append("extreme_returns")

    print(f"Rows totais: {total_rows}")
    print(f"Minimum date: {min_date.date()}")
    print(f"Maximum date: {max_date.date()}")
    print(f"Prices nulos: {null_prices}")
    print(f"Datas nulas: {null_dates}")
    print(f"Datas duplicadas: {duplicate_dates}")
    print(f"Prices zero: {zero_prices}")
    print(f"Prices negatives: {negative_prices}")
    print(f"Prices repetidos: {repeated_price_days} ({repeated_price_pct:.2f}%)")
    print(f"Returns extremos > {EXTREME_RETURN_THRESHOLD * 100:.0f}%: {extreme_returns}")

    if pd.notna(max_daily_return):
        print(
            f"Largest daily gain: {max_daily_return * 100:.2f}% "
            f"em {max_return_date.date()}"
        )

    if pd.notna(min_daily_return):
        print(
            f"Largest daily loss: {min_daily_return * 100:.2f}% "
            f"em {min_return_date.date()}"
        )

    if total_return_pct is not None:
        print(f"Return total: {total_return_pct:.2f}%")

    if warning_flags:
        print(f"Flags: {', '.join(warning_flags)}")
    else:
        print("Flags: OK")

    return {
        "asset_key": asset_key,
        "display_name": display_name,
        "table_name": table_name,
        "market_type": market_type,
        "total_rows": total_rows,
        "min_date": min_date.date(),
        "max_date": max_date.date(),
        "null_dates": int(null_dates),
        "null_prices": int(null_prices),
        "duplicate_dates": int(duplicate_dates),
        "zero_prices": int(zero_prices),
        "negative_prices": int(negative_prices),
        "repeated_price_days": int(repeated_price_days),
        "repeated_price_pct": round(repeated_price_pct, 2),
        "extreme_returns": int(extreme_returns),
        "max_daily_return_pct": round(max_daily_return * 100, 2) if pd.notna(max_daily_return) else None,
        "max_return_date": max_return_date.date() if max_return_date is not None else None,
        "min_daily_return_pct": round(min_daily_return * 100, 2) if pd.notna(min_daily_return) else None,
        "min_return_date": min_return_date.date() if min_return_date is not None else None,
        "first_price": first_price,
        "last_price": last_price,
        "total_return_pct": round(total_return_pct, 2) if total_return_pct is not None else None,
        "warning_flags": ", ".join(warning_flags) if warning_flags else "OK"
    }


# =========================
# RUN VALIDATION
# =========================

def executar_validacao(asset_keys, label):
    print("\n" + "=" * 120)
    print(f"DATA QUALITY VALIDATION - {label}")
    print("=" * 120)

    resultados = []

    for asset_key in asset_keys:
        try:
            resultado = validar_asset(asset_key)
            resultados.append(resultado)

        except Exception as e:
            print(f"\nERROR in {asset_key}: {e}")

            resultados.append({
                "asset_key": asset_key,
                "display_name": ASSETS.get(asset_key, {}).get("display_name"),
                "table_name": ASSETS.get(asset_key, {}).get("table_name"),
                "market_type": ASSETS.get(asset_key, {}).get("market_type"),
                "warning_flags": f"ERRORR: {e}"
            })

    report_df = pd.DataFrame(resultados)

    print("\n" + "=" * 120)
    print("SUMMARY FINAL DE QUALIDADE")
    print("=" * 120)

    cols_to_show = [
        "asset_key",
        "display_name",
        "total_rows",
        "min_date",
        "max_date",
        "null_prices",
        "duplicate_dates",
        "repeated_price_pct",
        "extreme_returns",
        "max_daily_return_pct",
        "min_daily_return_pct",
        "total_return_pct",
        "warning_flags"
    ]

    existing_cols = [
        col for col in cols_to_show
        if col in report_df.columns
    ]

    print(report_df[existing_cols])
    print("=" * 120)

    if EXPORT_REPORT:
        safe_label = (
            label.lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

        output_path = f"data_quality_report_{safe_label}.csv"

        report_df.to_csv(
            output_path,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print(f"\nReport saved to: {output_path}")

    print("\nValidation completed.")


# =========================
# MAIN
# =========================

def main():
    while True:
        mostrar_menu()

        choice = input("\nChoose an option: ").strip()

        if choice == "0":
            print("\nExiting the quality selector.")
            break

        elif choice == "1":
            asset_keys = list(ASSETS.keys())
            executar_validacao(
                asset_keys=asset_keys,
                label="all_assets"
            )

            input("\nPressiona ENTER para voltar ao menu...")

        elif choice == "2":
            group_key, group_data = chooser_grupo()

            executar_validacao(
                asset_keys=group_data["assets"],
                label=group_key
            )

            input("\nPressiona ENTER para voltar ao menu...")

        elif choice == "3":
            asset_key = chooser_asset_individual()

            executar_validacao(
                asset_keys=[asset_key],
                label=asset_key
            )

            input("\nPressiona ENTER para voltar ao menu...")

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()
