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

OUTPUT_FILE = "macro_sql_inventory_report.csv"

# Palavras-chave para tentar identificar tabelas macro/Fed/UE
MACRO_TABLE_KEYWORDS = [
    "fed",
    "federal",
    "funds",
    "m2",
    "m1",
    "assets",
    "reserve",
    "bank",
    "credit",
    "loans",
    "leases",
    "deposits",
    "securities",
    "delinquency",
    "charge",
    "euro",
    "eu",
    "ecb",
    "mfi",
    "retail",
    "interest",
    "consumer",
    "prices",
    "inflation",
    "hicp",
    "stress",
    "systemic",
    "financial",
    "conditions",
    "government",
    "finance",
    "national",
    "accounts",
    "payments",
    "fraud",
    "transfers",
    "debits",
    "atm",
    "pos",
    "card"
]

DATE_COLUMN_CANDIDATES = [
    "snapped_at",
    "date",
    "DATE",
    "observation_date",
    "event_date",
    "period",
    "time",
    "datetime",
    "created_at"
]

VALUE_COLUMN_CANDIDATES = [
    "price",
    "value",
    "VALUE",
    "observation_value",
    "amount",
    "rate",
    "index",
    "level",
    "close",
    "adj_close",
    "total",
    "total_assets"
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
# LISTAR TABELAS
# =========================

def listar_tabelas():
    query = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = :database
    ORDER BY table_name;
    """

    with engine.begin() as conn:
        result = conn.execute(
            text(query),
            {"database": DB_CONFIG["database"]}
        ).fetchall()

    tables = [row[0] for row in result]

    return tables


def filtrar_tabelas_macro(tables):
    macro_tables = []

    for table in tables:
        table_lower = table.lower()

        if any(keyword in table_lower for keyword in MACRO_TABLE_KEYWORDS):
            macro_tables.append(table)

    return macro_tables


# =========================
# COLUNAS
# =========================

def obter_columns(table_name):
    query = f"""
    SHOW COLUMNS FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return df


def detectar_coluna_data(columns):
    columns_list = columns["Field"].tolist()
    lower_map = {
        col.lower(): col
        for col in columns_list
    }

    for candidate in DATE_COLUMN_CANDIDATES:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    # fallback: procurar nomes que contenham date/time
    for col in columns_list:
        col_lower = col.lower()

        if "date" in col_lower or "time" in col_lower or "period" in col_lower:
            return col

    return None


def detectar_coluna_valor(columns, date_col=None):
    columns_list = columns["Field"].tolist()

    lower_map = {
        col.lower(): col
        for col in columns_list
    }

    for candidate in VALUE_COLUMN_CANDIDATES:
        if candidate.lower() in lower_map:
            return lower_map[candidate.lower()]

    # fallback: use the first numeric column that is not a date
    numeric_types = [
        "int",
        "decimal",
        "float",
        "double",
        "bigint",
        "smallint",
        "mediumint"
    ]

    for _, row in columns.iterrows():
        col = row["Field"]
        col_type = str(row["Type"]).lower()

        if date_col is not None and col == date_col:
            continue

        if any(t in col_type for t in numeric_types):
            return col

    return None


# =========================
# TABLE STATISTICS
# =========================

def contar_rows(table_name):
    query = f"""
    SELECT COUNT(*) AS total_rows
    FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return int(df["total_rows"].iloc[0])


def obter_datas_min_max(table_name, date_col):
    query = f"""
    SELECT
        MIN(`{date_col}`) AS min_date,
        MAX(`{date_col}`) AS max_date
    FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    return df["min_date"].iloc[0], df["max_date"].iloc[0]


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

    first_date = None
    first_value = None
    last_date = None
    last_value = None

    if not first_df.empty:
        first_date = first_df["snapped_at"].iloc[0]
        first_value = first_df["value"].iloc[0]

    if not last_df.empty:
        last_date = last_df["snapped_at"].iloc[0]
        last_value = last_df["value"].iloc[0]

    return first_date, first_value, last_date, last_value


def calcular_nulos(table_name, value_col):
    query = f"""
    SELECT
        COUNT(*) AS total_rows,
        SUM(CASE WHEN `{value_col}` IS NULL THEN 1 ELSE 0 END) AS null_values
    FROM `{table_name}`;
    """

    df = pd.read_sql(query, engine)

    total_rows = int(df["total_rows"].iloc[0])
    null_values = int(df["null_values"].iloc[0] or 0)

    null_pct = (
        null_values / total_rows * 100
        if total_rows > 0
        else 0
    )

    return null_values, round(null_pct, 2)


def obter_amostra(table_name, limit=3):
    query = f"""
    SELECT *
    FROM `{table_name}`
    LIMIT {limit};
    """

    try:
        df = pd.read_sql(query, engine)

        if df.empty:
            return ""

        return df.to_dict(orient="records")

    except Exception as e:
        return f"Error ao obter amostra: {e}"


# =========================
# CLASSIFICAR TABELA
# =========================

def classificar_tabela(table_name):
    name = table_name.lower()

    if any(x in name for x in ["fed", "federal", "m2", "reserve", "deposits", "loans", "bank_credit", "assets"]):
        return "fed_us_macro"

    if any(x in name for x in ["euro", "eu", "ecb", "mfi", "retail", "consumer_prices"]):
        return "euro_macro"

    if any(x in name for x in ["stress", "financial_conditions", "ted", "delinquency", "charge"]):
        return "financial_stress_credit"

    if any(x in name for x in ["payments", "fraud", "card", "atm", "pos", "transfers", "debits"]):
        return "payments_fraud"

    return "macro_other"


# =========================
# INSPECIONAR TABELA
# =========================

def inspecionar_tabela(table_name):
    print("\n" + "=" * 120)
    print(f"Inspecting table: {table_name}")
    print("=" * 120)

    result = {
        "table_name": table_name,
        "macro_category_guess": None,
        "total_rows": None,
        "columns_count": None,
        "columns": None,
        "date_col_guess": None,
        "value_col_guess": None,
        "min_date": None,
        "max_date": None,
        "first_valid_date": None,
        "first_valid_value": None,
        "last_valid_date": None,
        "last_valid_value": None,
        "null_values": None,
        "null_pct": None,
        "sample": None,
        "status": "OK",
        "error": None
    }

    try:
        columns_df = obter_columns(table_name)
        columns_list = columns_df["Field"].tolist()

        date_col = detectar_coluna_data(columns_df)
        value_col = detectar_coluna_valor(columns_df, date_col=date_col)

        total_rows = contar_rows(table_name)

        result["macro_category_guess"] = classificar_tabela(table_name)
        result["total_rows"] = total_rows
        result["columns_count"] = len(columns_list)
        result["columns"] = ", ".join(columns_list)
        result["date_col_guess"] = date_col
        result["value_col_guess"] = value_col

        if date_col is not None:
            min_date, max_date = obter_datas_min_max(table_name, date_col)

            result["min_date"] = min_date
            result["max_date"] = max_date

        if date_col is not None and value_col is not None:
            (
                first_valid_date,
                first_valid_value,
                last_valid_date,
                last_valid_value
            ) = obter_primeiro_ultimo_valor(
                table_name=table_name,
                date_col=date_col,
                value_col=value_col
            )

            null_values, null_pct = calcular_nulos(
                table_name=table_name,
                value_col=value_col
            )

            result["first_valid_date"] = first_valid_date
            result["first_valid_value"] = first_valid_value
            result["last_valid_date"] = last_valid_date
            result["last_valid_value"] = last_valid_value
            result["null_values"] = null_values
            result["null_pct"] = null_pct

        result["sample"] = str(obter_amostra(table_name, limit=2))

        print(f"Categoria likely: {result['macro_category_guess']}")
        print(f"Rows: {result['total_rows']}")
        print(f"Columns: {result['columns']}")
        print(f"Coluna data likely: {date_col}")
        print(f"Coluna valor likely: {value_col}")
        print(f"Minimum date: {result['min_date']}")
        print(f"Maximum date: {result['max_date']}")
        print(f"First valid value: {result['first_valid_value']}")
        print(f"Last valid value: {result['last_valid_value']}")
        print(f"Nulos na coluna valor: {result['null_values']} ({result['null_pct']}%)")

    except Exception as e:
        result["status"] = "ERRORR"
        result["error"] = str(e)

        print(f"ERROR ao inspecionar {table_name}: {e}")

    return result


# =========================
# RUN INVENTORY
# =========================

def executar_inventory():
    print("\nStarting macro SQL inventory...")
    print(f"Base de data: {DB_CONFIG['database']}")

    all_tables = listar_tabelas()

    print(f"\nTotal de tabelas encontradas: {len(all_tables)}")

    macro_tables = filtrar_tabelas_macro(all_tables)

    print(f"Likely macro/EU/Fed tables: {len(macro_tables)}")

    print("\nTables macro detetadas:")
    for table in macro_tables:
        print(f"- {table}")

    resultados = []

    for table in macro_tables:
        resultado = inspecionar_tabela(table)
        resultados.append(resultado)

    report_df = pd.DataFrame(resultados)

    print("\n" + "=" * 120)
    print("SUMMARY FINAL - MACRO SQL INVENTORY")
    print("=" * 120)

    cols_to_show = [
        "table_name",
        "macro_category_guess",
        "total_rows",
        "date_col_guess",
        "value_col_guess",
        "min_date",
        "max_date",
        "first_valid_value",
        "last_valid_value",
        "null_pct",
        "status",
        "error"
    ]

    existing_cols = [
        col for col in cols_to_show
        if col in report_df.columns
    ]

    print(report_df[existing_cols])
    print("=" * 120)

    if EXPORT_REPORT:
        report_df.to_csv(
            OUTPUT_FILE,
            index=False,
            sep=";",
            encoding="utf-8-sig"
        )

        print(f"\nReport saved to: {OUTPUT_FILE}")

    print("\nInventory completed.")

    return report_df


# =========================
# MAIN
# =========================

if __name__ == "__main__":
    executar_inventory()
