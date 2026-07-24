from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_CONFIG, get_sqlalchemy_database_url


# =========================
# SETTINGS
# =========================

EXPORT_REPORT = True
OUTPUT_FILE = "euro_series_inventory.csv"

# Start with the most useful / least complex tables
EURO_TABLES_TO_SCAN = {
    "EURO_RETAIL_INTEREST_RATES": {
        "table_name": "euro_retail_interest_rates",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA"
    },

    "EURO_MFI_INTEREST_RATES": {
        "table_name": "euro_mfi_interest_rate_statistics",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT",
        "freq_col": "FREQ",
        "area_col": "REF_AREA"
    },

    "EURO_CONSUMER_PRICES": {
        "table_name": "euro_indices_consumer_prices",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit",
        "freq_col": "freq",
        "area_col": "ref_area"
    },

    "EURO_LOSSES_FRAUD": {
        "table_name": "euro_losses_due_to_fraud",
        "date_col": "time_period",
        "value_col": "obs_value",
        "key_col": "key_code",
        "title_col": "title",
        "unit_col": "unit_measure",
        "freq_col": "freq",
        "area_col": "ref_area"
    },

    "EURO_PAYMENT_SYSTEMS": {
        "table_name": "euro_transactions_payments_systems",
        "date_col": "TIME_PERIOD",
        "value_col": "OBS_VALUE",
        "key_col": "key_code",
        "title_col": "TITLE",
        "unit_col": "UNIT_MEASURE",
        "freq_col": "FREQ",
        "area_col": "REF_AREA"
    }
}


# To test only one:
# ONLY_MACRO_KEYS = ["EURO_RETAIL_INTEREST_RATES"]
ONLY_MACRO_KEYS = []


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# HELPERS
# =========================

def tabela_existe(table_name):
    query = """
    SELECT COUNT(*) AS table_count
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


def coluna_existe(table_name, column_name):
    query = """
    SELECT COUNT(*) AS column_count
    FROM information_schema.columns
    WHERE table_schema = :database
      AND table_name = :table_name
      AND column_name = :column_name;
    """

    with engine.begin() as conn:
        result = conn.execute(
            text(query),
            {
                "database": DB_CONFIG["database"],
                "table_name": table_name,
                "column_name": column_name
            }
        ).fetchone()

    return result[0] > 0


def safe_col(cfg, col_key):
    value = cfg.get(col_key)

    if value is None:
        return None

    return value


def build_select_column(table_name, column_name, alias_name):
    if column_name is None:
        return f"NULL AS `{alias_name}`"

    if not coluna_existe(table_name, column_name):
        return f"NULL AS `{alias_name}`"

    return f"`{column_name}` AS `{alias_name}`"


# =========================
# SINGLE TABLE INVENTORY
# =========================

def inventariar_tabela(macro_key, cfg):
    table_name = cfg["table_name"]

    print("\n" + "=" * 130)
    print(f"EURO SERIES INVENTORY - {macro_key} | {table_name}")
    print("=" * 130)

    if not tabela_existe(table_name):
        print(f"ERROR: table does not exist: {table_name}")
        return pd.DataFrame([{
            "macro_key": macro_key,
            "table_name": table_name,
            "key_code": None,
            "status": "ERRORR",
            "issues": "table_not_found"
        }])

    required_cols = [
        cfg["key_col"],
        cfg["date_col"],
        cfg["value_col"]
    ]

    missing = [
        col for col in required_cols
        if not coluna_existe(table_name, col)
    ]

    if missing:
        print(f"ERROR: required columns missing: {missing}")
        return pd.DataFrame([{
            "macro_key": macro_key,
            "table_name": table_name,
            "key_code": None,
            "status": "ERRORR",
            "issues": f"missing_required_cols: {missing}"
        }])

    key_col = cfg["key_col"]
    date_col = cfg["date_col"]
    value_col = cfg["value_col"]

    title_select = build_select_column(
        table_name,
        safe_col(cfg, "title_col"),
        "title"
    )

    unit_select = build_select_column(
        table_name,
        safe_col(cfg, "unit_col"),
        "unit"
    )

    freq_select = build_select_column(
        table_name,
        safe_col(cfg, "freq_col"),
        "freq"
    )

    area_select = build_select_column(
        table_name,
        safe_col(cfg, "area_col"),
        "ref_area"
    )

    query = f"""
    SELECT
        '{macro_key}' AS macro_key,
        '{table_name}' AS table_name,
        `{key_col}` AS key_code,

        COUNT(*) AS observations,
        MIN(`{date_col}`) AS min_period,
        MAX(`{date_col}`) AS max_period,

        MIN(`{value_col}`) AS min_value,
        MAX(`{value_col}`) AS max_value,

        {title_select},
        {unit_select},
        {freq_select},
        {area_select}

    FROM `{table_name}`

    WHERE `{key_col}` IS NOT NULL
      AND `{date_col}` IS NOT NULL
      AND `{value_col}` IS NOT NULL

    GROUP BY
        `{key_col}`,
        title,
        unit,
        freq,
        ref_area

    ORDER BY
        observations DESC,
        max_period DESC;
    """

    df = pd.read_sql(query, engine)

    if df.empty:
        print("WARNING: sem series encontradas.")
        return pd.DataFrame([{
            "macro_key": macro_key,
            "table_name": table_name,
            "key_code": None,
            "status": "WARNING",
            "issues": "no_series_found"
        }])

    df["status"] = "OK"
    df["issues"] = "OK"

    print(f"Series encontradas: {len(df):,}")
    print(df.head(20).to_string())

    return df


# =========================
# MAIN
# =========================

def main():
    print("\nA iniciar Euro Series Inventory...")

    all_results = []

    items = EURO_TABLES_TO_SCAN.items()

    if ONLY_MACRO_KEYS:
        items = [
            (macro_key, cfg)
            for macro_key, cfg in EURO_TABLES_TO_SCAN.items()
            if macro_key in ONLY_MACRO_KEYS
        ]

    for idx, (macro_key, cfg) in enumerate(items, start=1):
        print("\n" + "#" * 130)
        print(f"[{idx}/{len(items)}] {macro_key}")
        print("#" * 130)

        try:
            df = inventariar_tabela(
                macro_key=macro_key,
                cfg=cfg
            )

            all_results.append(df)

        except Exception as e:
            print(f"ERROR inesperado em {macro_key}: {e}")

            all_results.append(pd.DataFrame([{
                "macro_key": macro_key,
                "table_name": cfg.get("table_name"),
                "key_code": None,
                "status": "ERRORR",
                "issues": str(e)
            }]))

    if all_results:
        final_df = pd.concat(
            all_results,
            ignore_index=True
        )
    else:
        final_df = pd.DataFrame()

    if EXPORT_REPORT:
        final_df.to_csv(
            OUTPUT_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print("\nReport exportado:")
        print(OUTPUT_FILE)

    print("\n" + "=" * 130)
    print("SUMMARY FINAL")
    print("=" * 130)

    if not final_df.empty:
        print(final_df.groupby(["macro_key", "status"]).size().reset_index(name="count"))

        print("\nTop 30 series por observations:")
        cols = [
            "macro_key",
            "table_name",
            "key_code",
            "observations",
            "min_period",
            "max_period",
            "title",
            "unit",
            "freq",
            "ref_area",
            "status"
        ]

        existing_cols = [
            col for col in cols
            if col in final_df.columns
        ]

        ok_df = final_df[final_df["status"] == "OK"].copy()

        if not ok_df.empty:
            print(
                ok_df[existing_cols]
                .sort_values("observations", ascending=False)
                .head(30)
                .to_string()
            )

    print("=" * 130)
    print("\nEuro Series Inventory completed.")


if __name__ == "__main__":
    main()

