from __future__ import annotations

import importlib
import os
from pathlib import Path
import runpy
import sys


DEMO_BUNDLE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = DEMO_BUNDLE_ROOT.parent

DEMO_RELEASE = "0.8.9"
DEMO_RUNTIME_REVISION = "0.8.9.snapshot.1"
_RUNTIME_RELEASE_ENV = "_MFI_DEMO_RUNTIME_RELEASE"
_PATCH_TARGET_MODULES = (
    "app.layout",
    "services.data_access_service",
    "dashboard.correlation_data",
    "services.data_quality_service",
    "services.euro_sync_status_service",
)

for path in (str(DEMO_BUNDLE_ROOT), str(PROJECT_ROOT)):
    if path in sys.path:
        sys.path.remove(path)

sys.path.insert(0, str(DEMO_BUNDLE_ROOT))
sys.path.insert(1, str(PROJECT_ROOT))

if os.environ.get(_RUNTIME_RELEASE_ENV) != DEMO_RUNTIME_REVISION:
    previous_runtime = sys.modules.get("demo.runtime")
    if previous_runtime is not None:
        deactivate = getattr(previous_runtime, "deactivate_demo_mode", None)
        if callable(deactivate):
            deactivate()

    import streamlit as st

    st.cache_data.clear()
    for module_name in _PATCH_TARGET_MODULES:
        module = sys.modules.get(module_name)
        if module is not None:
            importlib.reload(module)
    for module_name in ("demo.runtime", "demo.snapshot_data"):
        sys.modules.pop(module_name, None)
    os.environ[_RUNTIME_RELEASE_ENV] = DEMO_RUNTIME_REVISION

from demo.runtime import activate_demo_mode  # noqa: E402


def main() -> None:
    os.environ["DATA_MODE"] = "demo"
    activate_demo_mode()

    app_path = PROJECT_ROOT / "streamlit_app.py"
    if not app_path.exists():
        raise FileNotFoundError(f"Could not find the main application at: {app_path}")

    runpy.run_path(str(app_path), run_name="__main__")


if __name__ == "__main__":
    main()
