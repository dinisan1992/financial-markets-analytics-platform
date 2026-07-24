from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_CONFIG, get_sqlalchemy_database_url
from macro_config import EURO_COMPLEX_MACRO


# =========================
# SETTINGS
# =========================

EXPORT_REPORTS = True

OUTPUT_SUMMARY_FILE = "euro_table_profile_summary.csv"
OUTPUT_COLUMNS_FILE = "euro_table_profile_columns.csv"
OUTPUT_SAMPLES_FILE = "euro_table_profile_samples.csv"

# How many real rows to read per table for quick analysis
SAMPLE_LIMIT = 5000

# Quantas rows save como exemplo no ficheiro samples
SAMPLE_ROWS_TO_EXPORT = 5

# How many unique values to save per column
MAX_SAMPLE_VALUES = 20

# To test only one table, set it here.
# Example:
# ONLY_TABLES = ["euro_composite_indicator_stress"]
ONLY_TABLES = []

# Se quiseres saltar tabelas monstruosas, deixa True
SKIP_HUGE_TABLES = True
HUGE_TABLE_THRESHOLD = 2_000_000

# Se quiseres contar rows de todas as tabelas.
# COUNT(*) on huge tables can take a little time, but is usually acceptable.
COUNT_TOTAL_ROWS = True


# =========================
# CONNECTION
# =========================

DB_URL = get_sqlalchemy_database_url()

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)


# =========================
# HELPERS SQL
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


def contar_rows(table_name):
    query = f"""
    SELECT COUNT(*) AS total_rows
    FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return int(df["total_rows"].iloc[0])


def obter_columns(table_name):
    query = f"""
    SHOW COLUMNS FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return df


def obter_sample_df(table_name, limit=SAMPLE_LIMIT):
    query = f"""
    SELECT *
    FROM `{table_name}`
    LIMIT {limit};
    """

    df = pd.read_sql(query, engine)

    return df


# =========================
# COLUMN DETECTION
# =========================

def is_possible_date_col(column_name, column_type):
    name = str(column_name).lower()
    dtype = str(column_type).lower()

    date_keywords = [
        "date",
        "time",
        "period",
        "observation",
        "ref",
        "freq"
    ]

    if any(keyword in name for keyword in date_keywords):
        return True

    if any(dtype_keyword in dtype for dtype_keyword in ["date", "datetime", "timestamp"]):
        return True

    return False


def is_possible_value_col(column_name, column_type):
    name = str(column_name).lower()
    dtype = str(column_type).lower()

    excluded_exact_names = [
        "id",
        "year",
        "month",
        "quarter",
        "time",
        "date",
        "period",
        "freq"
    ]

    if name in excluded_exact_names:
        return False

    value_keywords = [
        "value",
        "obs_value",
        "obsvalue",
        "price",
        "rate",
        "amount",
        "index",
        "number",
        "count",
        "transactions",
        "transaction",
        "volume",
        "balance",
        "stock",
        "flow"
    ]

    if any(keyword in name for keyword in value_keywords):
        return True

    numeric_types = [
        "int",
        "decimal",
        "double",
        "float",
        "numeric",
        "bigint"
    ]

    if any(num_type in dtype for num_type in numeric_types):
        return True

    return False


def is_likely_dimension_col(column_name, column_type, sample_distinct_count, sample_rows):
    name = str(column_name).lower()
    dtype = str(column_type).lower()

    if name in ["id"]:
        return False

    if is_possible_date_col(column_name, column_type):
        return False

    if is_possible_value_col(column_name, column_type):
        return False

    if sample_rows == 0:
        return False

    distinct_ratio = sample_distinct_count / sample_rows

    dimension_keywords = [
        "geo",
        "country",
        "sector",
        "unit",
        "currency",
        "instrument",
        "category",
        "breakdown",
        "counterpart",
        "holder",
        "issuer",
        "maturity",
        "frequency",
        "freq",
        "type",
        "item",
        "indicator",
        "series",
        "title",
        "name",
        "classification",
        "method",
        "measure",
        "status"
    ]

    if any(keyword in name for keyword in dimension_keywords):
        return True

    if any(txt in dtype for txt in ["varchar", "text", "char", "enum"]):
        return True

    if sample_distinct_count <= 500 and distinct_ratio < 0.7:
        return True

    return False


def inferir_data_range_sample(series):
    try:
        converted = pd.to_datetime(series, errors="coerce")
        valid = converted.dropna()

        if valid.empty:
            return None, None

        return valid.min(), valid.max()

    except Exception:
        return None, None


def inferir_numeric_range_sample(series):
    try:
        converted = pd.to_numeric(series, errors="coerce")
        valid = converted.dropna()

        if valid.empty:
            return None, None

        return valid.min(), valid.max()

    except Exception:
        return None, None


# =========================
# ANALYSIS DE UMA TABELA
# =========================

def profile_table(macro_key, table_name, cfg):
    print("\n" + "=" * 140)
    print(f"EURO QUICK PROFILER - {macro_key} | {table_name}")
    print("=" * 140)

    summary_row = {
        "macro_key": macro_key,
        "display_name": cfg.get("display_name"),
        "table_name": table_name,
        "category": cfg.get("category"),
        "region": cfg.get("region"),
        "table_exists": False,
        "total_rows": None,
        "sample_rows": None,
        "columns_count": None,
        "possible_date_cols": None,
        "possible_value_cols": None,
        "likely_dimension_cols": None,
        "status": "UNKNOWN",
        "issues": ""
    }

    column_rows = []
    sample_rows_output = []

    try:
        if not tabela_existe(table_name):
            summary_row["status"] = "ERRORR"
            summary_row["issues"] = "table_not_found"
            print(f"ERROR: table does not exist: {table_name}")
            return summary_row, column_rows, sample_rows_output

        summary_row["table_exists"] = True

        total_rows = None

        if COUNT_TOTAL_ROWS:
            print("A contar rows...")
            total_rows = contar_rows(table_name)
            summary_row["total_rows"] = total_rows
            print(f"Rows totais: {total_rows:,}")

            if SKIP_HUGE_TABLES and total_rows >= HUGE_TABLE_THRESHOLD:
                summary_row["status"] = "SKIPPED"
                summary_row["issues"] = f"huge_table_skipped_{total_rows}_rows"
                print(f"SKIPPED: huge table com {total_rows:,} rows.")
                return summary_row, column_rows, sample_rows_output

        print("A obter columns...")
        columns_df = obter_columns(table_name)
        summary_row["columns_count"] = len(columns_df)

        print(f"Columns: {len(columns_df)}")

        print(f"Reading a quick sample up to {SAMPLE_LIMIT:,} rows...")
        sample_df = obter_sample_df(table_name, limit=SAMPLE_LIMIT)

        summary_row["sample_rows"] = len(sample_df)

        print(f"Amostra lida: {len(sample_df):,} rows")

        if sample_df.empty:
            summary_row["status"] = "WARNING"
            summary_row["issues"] = "empty_sample"
            return summary_row, column_rows, sample_rows_output

        possible_date_cols = []
        possible_value_cols = []
        likely_dimension_cols = []

        sample_rows_count = len(sample_df)

        for idx, col_row in columns_df.iterrows():
            column_name = col_row["Field"]
            column_type = col_row["Type"]

            print(f"[{idx + 1}/{len(columns_df)}] Coluna: {column_name} | {column_type}")

            if column_name not in sample_df.columns:
                continue

            series = sample_df[column_name]

            sample_distinct_count = int(series.nunique(dropna=True))
            sample_null_count = int(series.isna().sum())
            sample_null_pct = round(sample_null_count / sample_rows_count * 100, 2) if sample_rows_count > 0 else None

            sample_values = (
                series
                .dropna()
                .astype(str)
                .drop_duplicates()
                .head(MAX_SAMPLE_VALUES)
                .tolist()
            )

            possible_date = is_possible_date_col(column_name, column_type)
            possible_value = is_possible_value_col(column_name, column_type)

            likely_dimension = is_likely_dimension_col(
                column_name=column_name,
                column_type=column_type,
                sample_distinct_count=sample_distinct_count,
                sample_rows=sample_rows_count
            )

            min_value = None
            max_value = None

            if possible_date:
                min_value, max_value = inferir_data_range_sample(series)

            elif possible_value:
                min_value, max_value = inferir_numeric_range_sample(series)

            if possible_date:
                possible_date_cols.append(column_name)

            if possible_value:
                possible_value_cols.append(column_name)

            if likely_dimension:
                likely_dimension_cols.append(column_name)

            column_rows.append({
                "macro_key": macro_key,
                "table_name": table_name,
                "column_name": column_name,
                "column_type": column_type,
                "sample_rows": sample_rows_count,
                "sample_distinct_count": sample_distinct_count,
                "sample_null_count": sample_null_count,
                "sample_null_pct": sample_null_pct,
                "possible_date_col": possible_date,
                "possible_value_col": possible_value,
                "likely_dimension_col": likely_dimension,
                "sample_min_value": min_value,
                "sample_max_value": max_value,
                "sample_values": " | ".join(sample_values)
            })

        for sample_idx, sample_row in sample_df.head(SAMPLE_ROWS_TO_EXPORT).iterrows():
            sample_rows_output.append({
                "macro_key": macro_key,
                "table_name": table_name,
                "sample_row_number": sample_idx + 1,
                "sample_data": str(sample_row.to_dict())
            })

        summary_row["possible_date_cols"] = ", ".join(possible_date_cols)
        summary_row["possible_value_cols"] = ", ".join(possible_value_cols)
        summary_row["likely_dimension_cols"] = ", ".join(likely_dimension_cols)
        summary_row["status"] = "OK"
        summary_row["issues"] = "OK"

        print("\n" + "-" * 140)
        print("SUMMARY TABELA")
        print("-" * 140)
        print(f"Possible date cols: {possible_date_cols}")
        print(f"Possible value cols: {possible_value_cols}")
        print(f"Likely dimension cols: {likely_dimension_cols}")
        print("-" * 140)

    except Exception as e:
        summary_row["status"] = "ERRORR"
        summary_row["issues"] = str(e)

        print(f"Unexpected error in table {table_name}: {e}")

    return summary_row, column_rows, sample_rows_output


# =========================
# SELECIONAR TABELAS
# =========================

def get_tables_to_profile():
    tables = []

    for macro_key, cfg in EURO_COMPLEX_MACRO.items():
        table_name = cfg.get("table_name")

        if table_name is None:
            continue

        if ONLY_TABLES:
            if table_name not in ONLY_TABLES and macro_key not in ONLY_TABLES:
                continue

        tables.append((macro_key, table_name, cfg))

    return tables


# =========================
# EXPORTAR
# =========================

def export_reports(summary_rows, column_rows, sample_rows):
    summary_df = pd.DataFrame(summary_rows)
    columns_df = pd.DataFrame(column_rows)
    samples_df = pd.DataFrame(sample_rows)

    if EXPORT_REPORTS:
        summary_df.to_csv(
            OUTPUT_SUMMARY_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        columns_df.to_csv(
            OUTPUT_COLUMNS_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        samples_df.to_csv(
            OUTPUT_SAMPLES_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print("\nReports exported:")
        print(OUTPUT_SUMMARY_FILE)
        print(OUTPUT_COLUMNS_FILE)
        print(OUTPUT_SAMPLES_FILE)

    return summary_df, columns_df, samples_df


# =========================
# MAIN
# =========================

def main():
    print("\nA iniciar Euro Quick Table Profiler...")
    print(f"Tables EURO configuradas: {len(EURO_COMPLEX_MACRO)}")
    print(f"SAMPLE_LIMIT: {SAMPLE_LIMIT:,}")
    print(f"SKIP_HUGE_TABLES: {SKIP_HUGE_TABLES}")
    print(f"HUGE_TABLE_THRESHOLD: {HUGE_TABLE_THRESHOLD:,}")

    tables = get_tables_to_profile()

    print(f"Tables a analisar: {len(tables)}")

    if ONLY_TABLES:
        print(f"Filtro ONLY_TABLES asset: {ONLY_TABLES}")

    summary_rows = []
    column_rows = []
    sample_rows = []

    for idx, (macro_key, table_name, cfg) in enumerate(tables, start=1):
        print("\n" + "#" * 140)
        print(f"[{idx}/{len(tables)}] {macro_key} | {table_name}")
        print("#" * 140)

        summary_row, table_column_rows, table_sample_rows = profile_table(
            macro_key=macro_key,
            table_name=table_name,
            cfg=cfg
        )

        summary_rows.append(summary_row)
        column_rows.extend(table_column_rows)
        sample_rows.extend(table_sample_rows)

    summary_df, columns_df, samples_df = export_reports(
        summary_rows=summary_rows,
        column_rows=column_rows,
        sample_rows=sample_rows
    )

    print("\n" + "=" * 140)
    print("EURO QUICK TABLE PROFILER - SUMMARY FINAL")
    print("=" * 140)

    if not summary_df.empty:
        cols_to_show = [
            "macro_key",
            "table_name",
            "total_rows",
            "sample_rows",
            "columns_count",
            "possible_date_cols",
            "possible_value_cols",
            "likely_dimension_cols",
            "status",
            "issues"
        ]

        existing_cols = [
            col for col in cols_to_show
            if col in summary_df.columns
        ]

        print(summary_df[existing_cols])

        print("\nStatus:")
        status_summary = (
            summary_df["status"]
            .value_counts(dropna=False)
            .rename_axis("status")
            .reset_index(name="count")
        )

        print(status_summary)

    print("=" * 140)
    print("\nEuro Quick Table Profiler completed.")


if __name__ == "__main__":
    main()

