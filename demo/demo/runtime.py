from __future__ import annotations

import os
import sys
import types
from typing import Any

import pandas as pd

from demo.data import (
    build_demo_multi_asset_price_frame,
    demo_table_columns,
    demo_table_exists,
    load_demo_asset_data,
    load_demo_events,
    load_demo_events_from_table,
    load_demo_macro_pair,
)


_ACTIVE = False
_PATCHES: list[tuple[Any, str, Any]] = []
_STUBBED_MODULES: dict[str, Any] = {}


def _patch(module, name: str, replacement) -> None:
    _PATCHES.append((module, name, getattr(module, name)))
    setattr(module, name, replacement)


def _install_database_loader_stubs() -> None:
    """Install lightweight demo substitutes before the main app imports SQL loaders.

    The normal `macro_data_loader.py` and `euro_data_loader.py` import
    SQLAlchemy at module import time. A public demo should not require a SQL
    dependency merely to start, so the demo entrypoint installs modules with
    only the names the Streamlit application imports.
    """
    from asset_config import ASSETS

    for module_name in ("macro_data_loader", "euro_data_loader"):
        if module_name not in _STUBBED_MODULES:
            _STUBBED_MODULES[module_name] = sys.modules.get(module_name)

    macro_stub = types.ModuleType("macro_data_loader")

    def get_engine():
        return None

    def alinhar_macro_com_market(
        macro_key,
        market_asset,
        engine=None,
        start_date=None,
        end_date=None,
        how="outer",
        forward_fill=True,
        **kwargs,
    ):
        return load_demo_macro_pair(
            assets_config=ASSETS,
            macro_key=macro_key,
            market_asset=market_asset,
            start_date=start_date,
            end_date=end_date,
        )

    macro_stub.get_engine = get_engine
    macro_stub.alinhar_macro_com_market = alinhar_macro_com_market
    sys.modules["macro_data_loader"] = macro_stub

    euro_stub = types.ModuleType("euro_data_loader")

    def alinhar_euro_com_market(
        euro_series_key,
        market_asset,
        engine=None,
        start_date=None,
        end_date=None,
        how="outer",
        forward_fill=True,
        **kwargs,
    ):
        return load_demo_macro_pair(
            assets_config=ASSETS,
            macro_key=euro_series_key,
            market_asset=market_asset,
            start_date=start_date,
            end_date=end_date,
        )

    euro_stub.alinhar_euro_com_market = alinhar_euro_com_market
    sys.modules["euro_data_loader"] = euro_stub


def activate_demo_mode() -> None:
    """Patch the read-only data boundaries used by the Streamlit application.

    This function is called before `streamlit_app.py` is executed. It deliberately
    avoids importing the normal SQL-backed macro/euro loader modules.
    """
    global _ACTIVE
    if _ACTIVE:
        return

    os.environ["DATA_MODE"] = "demo"

    # Critical: install these before importing anything that may cause the main
    # app to resolve macro_data_loader/euro_data_loader.
    _install_database_loader_stubs()

    import streamlit as st

    from app import layout
    from asset_config import ASSETS
    from dashboard import correlation_data
    from services import data_access_service
    from services import data_quality_service
    from services import euro_sync_status_service

    original_setup_page = layout.setup_page

    def demo_setup_page(*args, **kwargs):
        result = original_setup_page(*args, **kwargs)
        st.info(
            "Demo Mode — deterministic synthetic data for portfolio demonstration only. "
            "No MySQL connection, private CSV, credential or live market feed is used. "
            "Displayed prices, returns, regimes and event reactions are illustrative."
        )
        return result

    def get_table_columns(engine, table_name):
        return demo_table_columns(table_name, ASSETS)

    def table_exists(engine, table_name):
        return demo_table_exists(table_name, ASSETS)

    def load_events_from_table(
        engine,
        table_name,
        start_date=None,
        end_date=None,
        table_exists_func=None,
        get_table_columns_func=None,
    ):
        return load_demo_events_from_table(
            table_name=table_name,
            start_date=start_date,
            end_date=end_date,
        )

    def load_asset_data(
        engine,
        assets_config,
        asset_key,
        start_date=None,
        end_date=None,
        get_table_columns_func=None,
    ):
        return load_demo_asset_data(
            assets_config=assets_config,
            asset_key=asset_key,
            start_date=start_date,
            end_date=end_date,
        )

    def load_fed_macro_pair(
        engine,
        align_macro_func,
        macro_key,
        market_asset,
        start_date,
        end_date,
    ):
        return load_demo_macro_pair(
            assets_config=ASSETS,
            macro_key=macro_key,
            market_asset=market_asset,
            start_date=start_date,
            end_date=end_date,
        )

    def load_euro_macro_pair(
        engine,
        align_euro_func,
        euro_series_key,
        market_asset,
        start_date,
        end_date,
    ):
        return load_demo_macro_pair(
            assets_config=ASSETS,
            macro_key=euro_series_key,
            market_asset=market_asset,
            start_date=start_date,
            end_date=end_date,
        )

    def build_multi_asset_price_frame(
        engine,
        selected_assets,
        assets_config,
        start_date=None,
        end_date=None,
        forward_fill=False,
        return_load_report=False,
    ):
        return build_demo_multi_asset_price_frame(
            assets_config=assets_config,
            selected_assets=selected_assets,
            start_date=start_date,
            end_date=end_date,
            forward_fill=forward_fill,
            return_load_report=return_load_report,
        )

    def run_asset_audit(engine, assets_config, as_of=None):
        rows = []
        frame_map = {}

        for asset_key, asset_cfg in assets_config.items():
            frame = load_demo_asset_data(assets_config, asset_key)
            coverage = frame[["snapped_at", "price"]].copy()
            frame_map[asset_key] = coverage

            demo_cfg = dict(asset_cfg)
            demo_cfg.update(
                {
                    "table_name": f"demo::{asset_key}",
                    "source_type": "deterministic_demo",
                    "source_provider": "Synthetic Demo Generator",
                    "source_identifier": asset_key,
                    "source_identity_status": "demo",
                    "source_reference": "",
                    "script_name": "",
                }
            )
            rows.append(
                data_quality_service.audit_asset_frame(
                    asset_key=asset_key,
                    asset_cfg=demo_cfg,
                    frame=frame,
                    as_of=as_of,
                )
            )

        return pd.DataFrame(rows), frame_map

    def audit_event_coverage(engine, asset_frames):
        events = load_demo_events()
        if events.empty:
            return pd.DataFrame()

        rows = []
        for _, event in events.iterrows():
            event_date = pd.to_datetime(event["event_date"], errors="coerce")
            covered = 0
            for frame in asset_frames.values():
                dates = (
                    pd.to_datetime(frame["snapped_at"], errors="coerce")
                    .dropna()
                    .sort_values()
                )
                future = dates[dates >= event_date]
                if not future.empty and int((future.iloc[0] - event_date).days) <= 7:
                    covered += 1

            rows.append(
                {
                    "event_date": event_date.date() if pd.notna(event_date) else None,
                    "event_title": event.get("event_title"),
                    "event_source": event.get("event_source_table"),
                    "date_precision": event.get("date_precision", "exact"),
                    "assets_with_7d_coverage": covered,
                    "assets_total": len(asset_frames),
                    "coverage_pct": (
                        round(covered / len(asset_frames) * 100, 2)
                        if asset_frames
                        else 0.0
                    ),
                    "daily_event_study_eligible": (
                        event.get("date_precision", "exact") == "exact"
                    ),
                }
            )
        return pd.DataFrame(rows)

    def load_latest_euro_sync_status(report_root=None, as_of=None):
        # Database synchronization is intentionally unavailable in demo mode.
        return pd.DataFrame(columns=euro_sync_status_service.STATUS_COLUMNS)

    _patch(layout, "setup_page", demo_setup_page)
    _patch(data_access_service, "get_table_columns", get_table_columns)
    _patch(data_access_service, "table_exists", table_exists)
    _patch(data_access_service, "load_events_from_table", load_events_from_table)
    _patch(data_access_service, "load_asset_data", load_asset_data)
    _patch(data_access_service, "load_fed_macro_pair", load_fed_macro_pair)
    _patch(data_access_service, "load_euro_macro_pair", load_euro_macro_pair)
    _patch(correlation_data, "build_multi_asset_price_frame", build_multi_asset_price_frame)
    _patch(data_quality_service, "run_asset_audit", run_asset_audit)
    _patch(data_quality_service, "audit_event_coverage", audit_event_coverage)
    _patch(
        euro_sync_status_service,
        "load_latest_euro_sync_status",
        load_latest_euro_sync_status,
    )

    _ACTIVE = True


def deactivate_demo_mode() -> None:
    """Restore monkey-patched project functions and original loader modules."""
    global _ACTIVE

    while _PATCHES:
        module, name, original = _PATCHES.pop()
        setattr(module, name, original)

    for module_name, original in list(_STUBBED_MODULES.items()):
        if original is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = original
    _STUBBED_MODULES.clear()

    _ACTIVE = False


def demo_mode_active() -> bool:
    return _ACTIVE
