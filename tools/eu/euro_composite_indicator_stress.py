from pathlib import Path
import sys


PROJECT_ROOT = next(
    parent
    for parent in Path(__file__).resolve().parents
    if (parent / "config.py").exists()
)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.macro_import_service import run_import_cli


if __name__ == "__main__":
    raise SystemExit(run_import_cli("EURO_COMPOSITE_SYSTEMIC_STRESS"))
