from __future__ import annotations

import os
from pathlib import Path
import runpy
import sys


# This file lives in:
#   <project_root>/demo/streamlit_demo.py
#
# The complete demo bundle can therefore be deleted by removing only
# <project_root>/demo/.
DEMO_BUNDLE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DEMO_BUNDLE_ROOT.parent

# Make the bundled inner package (<project_root>/demo/demo/) available as
# `demo`, while also exposing the normal project modules such as asset_config,
# app, app_pages, dashboard and services.
for path in (str(DEMO_BUNDLE_ROOT), str(PROJECT_ROOT)):
    if path in sys.path:
        sys.path.remove(path)

sys.path.insert(0, str(DEMO_BUNDLE_ROOT))
sys.path.insert(1, str(PROJECT_ROOT))

from demo.runtime import activate_demo_mode  # noqa: E402


def main() -> None:
    """Launch the normal application against the deterministic demo backend."""
    os.environ["DATA_MODE"] = "demo"
    activate_demo_mode()

    app_path = PROJECT_ROOT / "streamlit_app.py"
    if not app_path.exists():
        raise FileNotFoundError(
            f"Could not find the main application at: {app_path}"
        )

    runpy.run_path(str(app_path), run_name="__main__")


if __name__ == "__main__":
    main()
