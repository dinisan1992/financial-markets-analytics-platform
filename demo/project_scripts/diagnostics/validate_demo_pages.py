from __future__ import annotations

from pathlib import Path
import sys

from streamlit.testing.v1 import AppTest


DEMO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = DEMO_ROOT.parent
for path in (str(DEMO_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from app.navigation import PAGES  # noqa: E402


def main() -> int:
    failures = []
    for page in PAGES:
        app = AppTest.from_file(
            str(DEMO_ROOT / "streamlit_demo.py"),
            default_timeout=180,
        ).run()
        app.sidebar.radio[0].set_value(page).run(timeout=180)
        errors = [str(exception.value) for exception in app.exception]
        if errors:
            failures.append((page, errors))
            print(f"{page}: FAILED | {' | '.join(errors)}", flush=True)
        else:
            print(f"{page}: OK", flush=True)

    print(
        f"Demo pages: {len(PAGES)} | "
        f"success: {len(PAGES) - len(failures)} | failures: {len(failures)}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
