from pathlib import Path
import sys

PROJECT_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import subprocess
import time
import os

from asset_config import get_existing_script_names, get_missing_script_names


# =========================
# SETTINGS
# =========================

SCRIPT_DIR = Path(__file__).resolve().parent

ASSET_SCRIPTS = get_existing_script_names()
MISSING_CONFIGURED_SCRIPTS = get_missing_script_names()

STOP_ON_ERRORR = False


# =========================
# EXECUTAR SCRIPT
# =========================
def resolve_script_path(script_name):
    script_path = Path(script_name)

    if script_path.is_absolute():
        return script_path

    if len(script_path.parts) > 1:
        return PROJECT_ROOT / script_path

    return SCRIPT_DIR / script_path


def executar_script(script_name):
    script_path = resolve_script_path(script_name)

    if not script_path.exists():
        return {
            "script": script_name,
            "status": "missing",
            "duration": 0,
            "returncode": None,
            "error": f"File not found: {script_path}"
        }

    print("\n" + "=" * 70)
    print(f"Running: {script_name}")
    print("=" * 70)

    start_time = time.time()

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )

        duration = round(time.time() - start_time, 2)

        if result.stdout:
            print(result.stdout)

        if result.stderr:
            print("WARNINGS / STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print(f"OK: {script_name} completed successfully em {duration}s.")

            return {
                "script": script_name,
                "status": "success",
                "duration": duration,
                "returncode": result.returncode,
                "error": None
            }

        else:
            print(f"ERROR: {script_name} finished with code {result.returncode}.")

            return {
                "script": script_name,
                "status": "error",
                "duration": duration,
                "returncode": result.returncode,
                "error": result.stderr
            }

    except Exception as e:
        duration = round(time.time() - start_time, 2)

        print(f"Unexpected error while running {script_name}: {e}")

        return {
            "script": script_name,
            "status": "exception",
            "duration": duration,
            "returncode": None,
            "error": str(e)
        }


# =========================
# SUMMARY FINAL
# =========================
def mostrar_summary(resultados):
    print("\n" + "=" * 70)
    print("SUMMARY FINAL")
    print("=" * 70)

    total = len(resultados)
    success = sum(1 for r in resultados if r["status"] == "success")
    errors = sum(1 for r in resultados if r["status"] in ["error", "exception"])
    missing = sum(1 for r in resultados if r["status"] == "missing")

    print(f"Total scripts: {total}")
    print(f"Success: {success}")
    print(f"Errors: {errors}")
    print(f"Em falta: {missing}")

    print("\nDetalhe:")

    for r in resultados:
        print(
            f"{r['script']} | "
            f"status={r['status']} | "
            f"tempo={r['duration']}s"
        )

    print("=" * 70)


# =========================
# MAIN FUNCTION
# =========================
def main():
    print("\nA iniciar execution de todos os assets...")
    print(f"Pasta base: {PROJECT_ROOT}")
    print(f"Pasta dos scripts: {SCRIPT_DIR}")
    print(f"Executable scripts found: {len(ASSET_SCRIPTS)}")
    print(f"Configured scripts still missing: {len(MISSING_CONFIGURED_SCRIPTS)}")

    if MISSING_CONFIGURED_SCRIPTS:
        print("\nAssets sem script de update dedicado:")

        for asset_key, script_name in MISSING_CONFIGURED_SCRIPTS:
            print(f"- {asset_key}: {script_name}")

    resultados = []

    for script in ASSET_SCRIPTS:
        resultado = executar_script(script)
        resultados.append(resultado)

        if STOP_ON_ERRORR and resultado["status"] != "success":
            print("\nSTOP_ON_ERRORR=True -> execution interrompida.")
            break

    mostrar_summary(resultados)

    print("\nExecution global completed.")


# =========================
# EXECUTION
# =========================
if __name__ == "__main__":
    main()

