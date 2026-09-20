"""Default preference values and path resolution (SRP: defaults only)."""

import os
import sys
from typing import Any, Dict

from core.search_params import SEARCH_PARAMS_SCHEMA_VERSION


def default_preferences() -> Dict[str, Any]:
    return {
        "schema_version": SEARCH_PARAMS_SCHEMA_VERSION,
        "custom_presets": {},
        "search_history": [],
        "last_search": {},
        "preferred_times": {
            "departure_start": 0,
            "departure_end": 24,
        },
        "saved_profiles": {},
        "advanced_search_history": [],
        "theme": "dark",
        "alert_auto_check_enabled": False,
        "alert_auto_check_interval_min": 30,
        "alert_hit_modal_enabled": True,
        "max_results": 1000,
    }


def resolve_filepath(filepath: str | None) -> str:
    if filepath is not None:
        return filepath
    if getattr(sys, "frozen", False):
        app_data = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "FlightBot",
        )
        os.makedirs(app_data, exist_ok=True)
        return os.path.join(app_data, "user_preferences.json")
    return "user_preferences.json"


def has_required_search_fields(params: Dict[str, Any]) -> bool:
    return bool(params.get("origin") and params.get("dest") and params.get("dep"))


def history_key(params: Dict[str, Any]) -> tuple[Any, ...]:
    return (
        params.get("origin", ""),
        params.get("dest", ""),
        params.get("dep", ""),
        params.get("ret") or "",
        int(params.get("adults", 1) or 1),
        params.get("cabin_class", "ECONOMY"),
        bool(params.get("is_domestic", False)),
    )
