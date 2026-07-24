import subprocess
import sys
from pathlib import Path


# =========================
# SETTINGS
# =========================

BASE_DIR = Path(__file__).resolve().parent
PYTHON_EXECUTABLE = sys.executable


# =========================
# SCRIPT MENU
# =========================

MENU_OPTIONS = {
    "1": {
        "title": "Run all core asset scripts",
        "script": "project_scripts/assets/run_all_assets.py",
        "description": "Validates the main asset scripts."
    },

    "2": {
        "title": "Asset chart selector",
        "script": "project_scripts/analysis/asset_chart_selector.py",
        "description": "Opens an individual chart for one asset."
    },

    "3": {
        "title": "Performance group selector",
        "script": "project_scripts/analysis/performance_group_selector.py",
        "description": "Compares normalized performance by asset group."
    },

    "4": {
        "title": "Correlation matrix selector",
        "script": "project_scripts/analysis/correlation_matrix_selector.py",
        "description": "Generates a correlation matrix between assets."
    },

    "5": {
        "title": "Rolling correlation selector",
        "script": "project_scripts/analysis/rolling_correlation_selector.py",
        "description": "Analyses rolling correlations between asset pairs."
    },

    "6": {
        "title": "Market regime selector",
        "script": "project_scripts/analysis/market_regime_selector.py",
        "description": "Classifies market regimes."
    },

    "7": {
        "title": "Event overlay selector",
        "script": "project_scripts/analysis/event_overlay_selector.py",
        "description": "Overlays historical events on market charts."
    },

    "8": {
        "title": "Macro market overlay selector",
        "script": "project_scripts/analysis/macro_market_overlay_selector.py",
        "description": "Compares market assets with existing macro proxies."
    },

    "9": {
        "title": "FED macro selector",
        "script": "project_scripts/analysis/macro_macro_market_selector.py",
        "description": "Explores FED macro vs market pairs."
    },

    "10": {
        "title": "FED liquidity market analysis",
        "script": "project_scripts/analysis/macro_liquidity_market_analysis.py",
        "description": "Analyses FED liquidity vs markets."
    },

    "11": {
        "title": "FED rates analysis",
        "script": "project_scripts/analysis/macro_rates_inflation_analysis.py",
        "description": "Analyses the Fed Funds Rate vs markets."
    },

    "12": {
        "title": "FED credit stress analysis",
        "script": "project_scripts/analysis/macro_credit_stress_analysis.py",
        "description": "Analyses FED credit/stress vs markets."
    },

    "13": {
        "title": "EURO market analysis",
        "script": "project_scripts/analysis/euro_market_analysis.py",
        "description": "Analyses filtered EURO series vs markets."
    },

    "14": {
        "title": "Validate FED macro config",
        "script": "project_scripts/analysis/macro_config_validator.py",
        "description": "Validates the FED indicator configuration."
    },

    "15": {
        "title": "Validate EURO series",
        "script": "project_scripts/analysis/euro_series_validator.py",
        "description": "Validates EURO series, groups and market pairs."
    },

    "16": {
        "title": "Data quality selector",
        "script": "project_scripts/analysis/asset_data_quality_selector.py",
        "description": "Analyses data quality by asset."
    },

    "17": {
        "title": "Validate asset data quality",
        "script": "project_scripts/analysis/validate_asset_data_quality.py",
        "description": "Generates a general data quality report."
    },

    "18": {
        "title": "Macro summary report",
        "script": "project_scripts/analysis/macro_summary_report.py",
        "description": "Generates a FED macro indicator summary."
    },

    "19": {
        "title": "EURO series config status",
        "script": "euro_series_config.py",
        "description": "Shows EURO configuration status."
    },

    "20": {
        "title": "Macro config status",
        "script": "macro_config.py",
        "description": "Shows FED macro configuration status."
    }
}


# =========================
# HELPERS
# =========================

def clear_screen():
    print("\n" * 3)


def print_header():
    print("=" * 100)
    print("MACRO-FINANCIAL RISK & MARKET BEHAVIOUR ANALYTICS PLATFORM")
    print("=" * 100)
    print("Analysis Launcher")
    print("=" * 100)


def print_menu():
    print_header()

    print("\nChoose an option:\n")

    for key, option in MENU_OPTIONS.items():
        print(f"{key:>2} - {option['title']}")
        print(f"     {option['description']}")

    print("\n 0 - Exit")
    print("=" * 100)


def script_exists(script_name):
    script_path = BASE_DIR / script_name
    return script_path.exists()


def run_script(script_name):
    script_path = BASE_DIR / script_name

    if not script_path.exists():
        print("\nERROR")
        print("=" * 100)
        print(f"The file does not exist: {script_name}")
        print(f"Expected path: {script_path}")
        print("=" * 100)
        return

    print("\n" + "=" * 100)
    print(f"Running: {script_name}")
    print("=" * 100)

    try:
        result = subprocess.run(
            [PYTHON_EXECUTABLE, str(script_path)],
            cwd=BASE_DIR
        )

        print("\n" + "=" * 100)

        if result.returncode == 0:
            print(f"Completed successfully: {script_name}")
        else:
            print(f"The script finished with error code: {result.returncode}")
            print(f"Script: {script_name}")

        print("=" * 100)

    except KeyboardInterrupt:
        print("\nExecution interrupted by the user.")

    except Exception as e:
        print("\nUnexpected error while running script:")
        print(e)


def pause():
    input("\nPress ENTER to return to the menu...")


def show_project_status():
    status_file = BASE_DIR / "PROJECT_STATUS.md"

    print("\n" + "=" * 100)
    print("PROJECT STATUS")
    print("=" * 100)

    if not status_file.exists():
        print("PROJECT_STATUS.md not found.")
        print("=" * 100)
        return

    try:
        content = status_file.read_text(encoding="utf-8")

        # Show only a short version to avoid flooding the terminal
        lines = content.splitlines()
        max_lines = 80

        for line in lines[:max_lines]:
            print(line)

        if len(lines) > max_lines:
            print("\n... content truncated in launcher ...")
            print("Open PROJECT_STATUS.md to see everything.")

    except Exception as e:
        print(f"Error reading PROJECT_STATUS.md: {e}")

    print("=" * 100)


def show_git_status():
    print("\n" + "=" * 100)
    print("GIT STATUS")
    print("=" * 100)

    try:
        subprocess.run(
            ["git", "status"],
            cwd=BASE_DIR
        )

    except Exception as e:
        print("Unable to run git status.")
        print(e)

    print("=" * 100)


# =========================
# MAIN LOOP
# =========================

def main():
    while True:
        clear_screen()
        print_menu()

        print("\nExtra:")
        print(" s - View PROJECT_STATUS.md")
        print(" g - View git status")

        choice = input("\nOption: ").strip().lower()

        if choice == "0":
            print("\nExiting launcher.")
            break

        if choice == "s":
            show_project_status()
            pause()
            continue

        if choice == "g":
            show_git_status()
            pause()
            continue

        if choice not in MENU_OPTIONS:
            print("\nInvalid option.")
            pause()
            continue

        option = MENU_OPTIONS[choice]
        script_name = option["script"]

        run_script(script_name)
        pause()


if __name__ == "__main__":
    main()

