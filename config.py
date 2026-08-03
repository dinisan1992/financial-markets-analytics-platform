import os
from pathlib import Path
from urllib.parse import quote_plus


# =========================
# CAMINHOS DO PROJETO
# =========================

BASE_DIR = Path(__file__).resolve().parent


def _load_local_env_file():
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


_load_local_env_file()


def _env_path(env_name, default_path):
    value = os.getenv(env_name)
    if not value:
        return default_path
    return Path(value).expanduser().resolve()


def _env_bool(env_name, default=False):
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

DATA_DIR = _env_path("PROJECT_DATA_DIR", BASE_DIR / "data")
RAW_DATA_DIR = DATA_DIR / "raw"
CLEAN_DATA_DIR = DATA_DIR / "clean"
SQL_EXPORTS_DIR = DATA_DIR / "sql_exports"

NEW_MARKET_DATA_DIR = _env_path(
    "PROJECT_NEW_MARKET_DATA_DIR",
    BASE_DIR / "new_market_data"
)
NEW_MARKET_RAW_DIR = NEW_MARKET_DATA_DIR / "raw"
NEW_MARKET_CLEAN_DIR = NEW_MARKET_DATA_DIR / "clean"
NEW_MARKET_REPORTS_DIR = NEW_MARKET_DATA_DIR / "reports"

MARKET_CLEAN_DIR = _env_path(
    "PROJECT_MARKET_CLEAN_DIR",
    NEW_MARKET_CLEAN_DIR,
)

DATA_SOURCE_DIR = _env_path("PROJECT_SOURCE_DATA_DIR", DATA_DIR / "raw")
FED_SOURCE_DIR = _env_path("FED_SOURCE_DIR", MARKET_CLEAN_DIR / "eua_fed")
EURO_SOURCE_DIR = _env_path("EURO_SOURCE_DIR", MARKET_CLEAN_DIR / "euro")

DOCS_DIR = BASE_DIR / "docs"
OUTPUTS_DIR = BASE_DIR / "outputs"
ARCHIVE_DIR = BASE_DIR / "archive"
TOOLS_DIR = BASE_DIR / "tools"


# =========================
# CSVs PRINCIPAIS
# =========================

CSV_PATH = MARKET_CLEAN_DIR / "btc_data.csv"


# =========================
# BASE DE DADOS
# =========================

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "btc_data"),
    "port": int(os.getenv("DB_PORT", "3306"))
}


def get_sqlalchemy_database_url():
    user = quote_plus(str(DB_CONFIG["user"]))
    password = quote_plus(str(DB_CONFIG["password"]))
    host = DB_CONFIG["host"]
    port = DB_CONFIG["port"]
    database = DB_CONFIG["database"]

    return (
        f"mysql+mysqlconnector://{user}:{password}"
        f"@{host}:{port}/{database}"
    )


# =========================
# TABELAS
# =========================

BTC_TABLE = "btc_analysis"


# =========================
# EXECUTION MODE
# =========================

DEFAULT_UPDATE_SQL = _env_bool("DEFAULT_UPDATE_SQL", False)


# =========================
# PROJECT VERSION
# =========================

PROJECT_VERSION = "0.5.6"
