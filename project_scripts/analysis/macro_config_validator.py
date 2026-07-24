from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_CONFIG, get_sqlalchemy_database_url
from macro_config import MACRO_ASSETS, MACRO_GROUPS


# =========================
# SETTINGS
# =========================

EXPORT_REPORT = True

OUTPUT_FILE = "macro_config_validation_report.csv"


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# SQL HELPERS
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


def obter_columns(table_name):
    query = f"""
    SHOW COLUMNS FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return df


def coluna_existe(columns_df, column_name):
    if column_name is None:
        return False

    columns = columns_df["Field"].tolist()

    return column_name in columns


def contar_rows(table_name):
    query = f"""
    SELECT COUNT(*) AS total_rows
    FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return int(df["total_rows"].iloc[0])


def obter_min_max_datas(table_name, date_col):
    query = f"""
    SELECT
        MIN(`{date_col}`) AS min_date,
        MAX(`{date_col}`) AS max_date
    FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return df["min_date"].iloc[0], df["max_date"].iloc[0]


def obter_valid_values_stats(table_name, date_col, value_col):
    query = f"""
    SELECT
        COUNT(*) AS total_rows,
        SUM(CASE WHEN `{date_col}` IS NULL THEN 1 ELSE 0 END) AS null_dates,
        SUM(CASE WHEN `{value_col}` IS NULL THEN 1 ELSE 0 END) AS null_values,
        MIN(`{value_col}`) AS min_value,
        MAX(`{value_col}`) AS max_value,
        AVG(`{value_col}`) AS avg_value
    FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    row = df.iloc[0]

    total_rows = int(row["total_rows"] or 0)
    null_dates = int(row["null_dates"] or 0)
    null_values = int(row["null_values"] or 0)

    null_dates_pct = round(null_dates / total_rows * 100, 2) if total_rows > 0 else None
    null_values_pct = round(null_values / total_rows * 100, 2) if total_rows > 0 else None

    return {
        "total_rows": total_rows,
        "null_dates": null_dates,
        "null_dates_pct": null_dates_pct,
        "null_values": null_values,
        "null_values_pct": null_values_pct,
        "min_value": row["min_value"],
        "max_value": row["max_value"],
        "avg_value": row["avg_value"]
    }


def obter_primeiro_ultimo_valor(table_name, date_col, value_col):
    query_first = f"""
    SELECT
        `{date_col}` AS snapped_at,
        `{value_col}` AS value
    FROM `{table_name}`
    WHERE `{date_col}` IS NOT NULL
      AND `{value_col}` IS NOT NULL
    ORDER BY `{date_col}` ASC
    LIMIT 1;
    """

    query_last = f"""
    SELECT
        `{date_col}` AS snapped_at,
        `{value_col}` AS value
    FROM `{table_name}`
    WHERE `{date_col}` IS NOT NULL
      AND `{value_col}` IS NOT NULL
    ORDER BY `{date_col}` DESC
    LIMIT 1;
    """

    first_df = pd.read_sql(query_first, engine)
    last_df = pd.read_sql(query_last, engine)

    result = {
        "first_valid_date": None,
        "first_valid_value": None,
        "last_valid_date": None,
        "last_valid_value": None
    }

    if not first_df.empty:
        result["first_valid_date"] = first_df["snapped_at"].iloc[0]
        result["first_valid_value"] = first_df["value"].iloc[0]

    if not last_df.empty:
        result["last_valid_date"] = last_df["snapped_at"].iloc[0]
        result["last_valid_value"] = last_df["value"].iloc[0]

    return result


# =========================
# VALIDAR CONFIG INDIVIDUAL
# =========================

def validar_macro_config(macro_key, cfg):
    print("\n" + "=" * 120)
    print(f"A validar macro config: {macro_key} | {cfg.get('display_name')}")
    print("=" * 120)

    table_name = cfg.get("table_name")
    date_col = cfg.get("date_col")
    value_col = cfg.get("value_col")

    result = {
        "macro_key": macro_key,
        "display_name": cfg.get("display_name"),
        "table_name": table_name,
        "date_col": date_col,
        "value_col": value_col,
        "category": cfg.get("category"),
        "region": cfg.get("region"),
        "unit": cfg.get("unit"),
        "table_exists": False,
        "date_col_exists": False,
        "value_col_exists": False,
        "total_rows": None,
        "min_date": None,
        "max_date": None,
        "first_valid_date": None,
        "first_valid_value": None,
        "last_valid_date": None,
        "last_valid_value": None,
        "null_dates": None,
        "null_dates_pct": None,
        "null_values": None,
        "null_values_pct": None,
        "min_value": None,
        "max_value": None,
        "avg_value": None,
        "status": "UNKNOWN",
        "issues": ""
    }

    issues = []

    try:
        if table_name is None or str(table_name).strip() == "":
            issues.append("missing_table_name")
            result["status"] = "ERRORR"
            result["issues"] = ", ".join(issues)
            print("ERROR: missing table_name.")
            return result

        exists = tabela_existe(table_name)
        result["table_exists"] = exists

        if not exists:
            issues.append("table_not_found")
            result["status"] = "ERRORR"
            result["issues"] = ", ".join(issues)
            print(f"ERROR: table does not exist: {table_name}")
            return result

        columns_df = obter_columns(table_name)

        date_exists = coluna_existe(columns_df, date_col)
        value_exists = coluna_existe(columns_df, value_col)

        result["date_col_exists"] = date_exists
        result["value_col_exists"] = value_exists

        if not date_exists:
            issues.append("date_col_not_found")

        if not value_exists:
            issues.append("value_col_not_found")

        if not date_exists or not value_exists:
            result["status"] = "ERRORR"
            result["issues"] = ", ".join(issues)
            print(f"ERROR: missing columns. Actual columns: {columns_df['Field'].tolist()}")
            return result

        total_rows = contar_rows(table_name)
        result["total_rows"] = total_rows

        if total_rows == 0:
            issues.append("empty_table")
            result["status"] = "ERRORR"
            result["issues"] = ", ".join(issues)
            print("ERROR: empty table.")
            return result

        min_date, max_date = obter_min_max_datas(table_name, date_col)

        result["min_date"] = min_date
        result["max_date"] = max_date

        stats = obter_valid_values_stats(
            table_name=table_name,
            date_col=date_col,
            value_col=value_col
        )

        result.update(stats)

        first_last = obter_primeiro_ultimo_valor(
            table_name=table_name,
            date_col=date_col,
            value_col=value_col
        )

        result.update(first_last)

        if result["null_dates_pct"] is not None and result["null_dates_pct"] > 5:
            issues.append("many_null_dates")

        if result["null_values_pct"] is not None and result["null_values_pct"] > 20:
            issues.append("many_null_values")

        if result["first_valid_value"] is None or result["last_valid_value"] is None:
            issues.append("no_valid_values")

        if issues:
            result["status"] = "WARNING"
        else:
            result["status"] = "OK"

        result["issues"] = ", ".join(issues) if issues else "OK"

        print(f"Table: {table_name}")
        print(f"Coluna data: {date_col} | existe: {date_exists}")
        print(f"Coluna valor: {value_col} | existe: {value_exists}")
        print(f"Rows: {total_rows}")
        print(f"Datas: {min_date} -> {max_date}")
        print(f"Nulos datas: {result['null_dates']} ({result['null_dates_pct']}%)")
        print(f"Nulos valores: {result['null_values']} ({result['null_values_pct']}%)")
        print(f"First valid value: {result['first_valid_value']} em {result['first_valid_date']}")
        print(f"Last valid value: {result['last_valid_value']} em {result['last_valid_date']}")
        print(f"Status: {result['status']} | Issues: {result['issues']}")

    except Exception as e:
        result["status"] = "ERRORR"
        result["issues"] = str(e)
        print(f"ERROR inesperado em {macro_key}: {e}")

    return result


# =========================
# VALIDAR GROUPS
# =========================

def validar_grupos_macro():
    print("\n" + "=" * 120)
    print("A validar grupos macro...")
    print("=" * 120)

    group_results = []

    for group_key, group_data in MACRO_GROUPS.items():
        assets = group_data.get("assets", [])

        missing_assets = [
            macro_key for macro_key in assets
            if macro_key not in MACRO_ASSETS
        ]

        group_status = "OK" if not missing_assets else "ERRORR"

        row = {
            "group_key": group_key,
            "group_name": group_data.get("name"),
            "assets_count": len(assets),
            "missing_assets": ", ".join(missing_assets) if missing_assets else "OK",
            "status": group_status
        }

        group_results.append(row)

        print(
            f"{group_key:35s} | "
            f"{group_data.get('name'):45s} | "
            f"assets: {len(assets):2d} | "
            f"status: {group_status}"
        )

        if missing_assets:
            print(f"  Missing: {missing_assets}")

    return pd.DataFrame(group_results)


# =========================
# RUN VALIDATION
# =========================

def executar_validacao():
    print("\nA iniciar validation do macro_config.py...")
    print(f"Base de data: {DB_CONFIG['database']}")
    print(f"Indicadores macro configurados: {len(MACRO_ASSETS)}")
    print(f"Groups macro configurados: {len(MACRO_GROUPS)}")

    results = []

    for macro_key, cfg in MACRO_ASSETS.items():
        result = validar_macro_config(
            macro_key=macro_key,
            cfg=cfg
        )

        results.append(result)

    report_df = pd.DataFrame(results)

    group_report_df = validar_grupos_macro()

    print("\n" + "=" * 120)
    print("SUMMARY FINAL - MACRO CONFIG VALIDATION")
    print("=" * 120)

    cols_to_show = [
        "macro_key",
        "display_name",
        "table_name",
        "date_col",
        "value_col",
        "total_rows",
        "min_date",
        "max_date",
        "null_values_pct",
        "status",
        "issues"
    ]

    existing_cols = [
        col for col in cols_to_show
        if col in report_df.columns
    ]

    print(report_df[existing_cols])

    print("\nSummary de status:")

    status_summary = (
        report_df["status"]
        .value_counts()
        .rename_axis("status")
        .reset_index(name="count")
    )

    print(status_summary)

    print("=" * 120)

    if EXPORT_REPORT:
        report_df.to_csv(
            OUTPUT_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        group_report_df.to_csv(
            "macro_groups_validation_report.csv",
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print("\nReports guardata:")
        print(OUTPUT_FILE)
        print("macro_groups_validation_report.csv")

    print("\nValidation completed.")

    return report_df, group_report_df


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    executar_validacao()

