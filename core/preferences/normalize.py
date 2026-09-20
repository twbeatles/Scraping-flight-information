"""Preference payload normalization (SRP: validation/normalization only)."""

from datetime import datetime
from typing import Any, Dict, List

from core.airports import _extract_airport_code, validate_airport_code
from core.search_params import SEARCH_PARAMS_SCHEMA_VERSION, _coerce_bool, normalize_search_params

from core.preferences.defaults import default_preferences, has_required_search_fields, history_key


def normalize_preferences_payload(raw: Dict[str, Any] | None) -> Dict[str, Any]:
    default_prefs = default_preferences()
    prefs = dict(default_prefs)
    raw_dict = raw if isinstance(raw, dict) else {}

    for key, value in raw_dict.items():
        if key not in prefs:
            prefs[key] = value

    custom_presets = raw_dict.get("custom_presets", {})
    normalized_presets: Dict[str, str] = {}
    if isinstance(custom_presets, dict):
        for code, name in custom_presets.items():
            normalized_code = _extract_airport_code(code)
            if validate_airport_code(normalized_code):
                normalized_presets[normalized_code] = str(name or normalized_code).strip()
    prefs["custom_presets"] = normalized_presets

    history_items: List[Dict[str, Any]] = []
    raw_history = raw_dict.get("search_history", [])
    if isinstance(raw_history, list):
        seen_keys: set[tuple[Any, ...]] = set()
        for item in raw_history:
            if not isinstance(item, dict):
                continue
            normalized = normalize_search_params(item)
            if not has_required_search_fields(normalized):
                continue
            key = history_key(normalized)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            history_items.append(normalized)
    prefs["search_history"] = history_items[:20]

    advanced_history: List[Dict[str, Any]] = []
    raw_advanced_history = raw_dict.get("advanced_search_history", [])
    if isinstance(raw_advanced_history, list):
        for item in raw_advanced_history:
            normalized_item = normalize_advanced_history_item(item)
            if normalized_item:
                advanced_history.append(normalized_item)
    prefs["advanced_search_history"] = advanced_history[:20]

    last_search = raw_dict.get("last_search", {})
    if isinstance(last_search, dict):
        normalized_last_search = normalize_search_params(last_search)
        prefs["last_search"] = (
            normalized_last_search if has_required_search_fields(normalized_last_search) else {}
        )

    profiles = raw_dict.get("saved_profiles", {})
    normalized_profiles: Dict[str, Dict[str, Any]] = {}
    if isinstance(profiles, dict):
        for name, value in profiles.items():
            if not isinstance(value, dict):
                continue
            normalized = normalize_search_params(value)
            if has_required_search_fields(normalized):
                normalized_profiles[str(name)] = normalized
    prefs["saved_profiles"] = normalized_profiles

    preferred_times = raw_dict.get("preferred_times", {})
    if isinstance(preferred_times, dict):
        try:
            start = int(preferred_times.get("departure_start", 0))
        except Exception:
            start = 0
        try:
            end = int(preferred_times.get("departure_end", 24))
        except Exception:
            end = 24
        prefs["preferred_times"] = {
            "departure_start": max(0, min(start, 23)),
            "departure_end": max(1, min(end, 24)),
        }

    theme = str(raw_dict.get("theme", default_prefs["theme"]) or default_prefs["theme"]).lower()
    prefs["theme"] = theme if theme in {"dark", "light"} else default_prefs["theme"]

    try:
        max_results = int(raw_dict.get("max_results", default_prefs["max_results"]) or default_prefs["max_results"])
    except Exception:
        max_results = default_prefs["max_results"]
    prefs["max_results"] = max(50, min(max_results, 2000))

    prefs["alert_auto_check_enabled"] = _coerce_bool(
        raw_dict.get("alert_auto_check_enabled", default_prefs["alert_auto_check_enabled"]),
        default_prefs["alert_auto_check_enabled"],
    )
    try:
        interval_min = int(
            raw_dict.get("alert_auto_check_interval_min", default_prefs["alert_auto_check_interval_min"])
            or default_prefs["alert_auto_check_interval_min"]
        )
    except Exception:
        interval_min = default_prefs["alert_auto_check_interval_min"]
    prefs["alert_auto_check_interval_min"] = max(5, min(interval_min, 1440))
    prefs["alert_hit_modal_enabled"] = _coerce_bool(
        raw_dict.get("alert_hit_modal_enabled", default_prefs["alert_hit_modal_enabled"]),
        default_prefs["alert_hit_modal_enabled"],
    )
    prefs["schema_version"] = SEARCH_PARAMS_SCHEMA_VERSION
    return prefs


def normalize_advanced_history_item(item: Any) -> Dict[str, Any]:
    if not isinstance(item, dict):
        return {}

    history_type = str(item.get("type", "") or "").strip()
    if history_type not in {"multi_dest", "date_range"}:
        return {}

    raw_params = item.get("params", {})
    params = normalize_search_params(raw_params if isinstance(raw_params, dict) else {})
    if not has_required_search_fields(params):
        return {}

    raw_summary = item.get("summary", [])
    summary: List[Dict[str, Any]] = []
    if isinstance(raw_summary, list):
        for row in raw_summary:
            if not isinstance(row, dict):
                continue
            normalized_row: Dict[str, Any] = {}
            for key, value in row.items():
                if key in {"min_price", "result_count"}:
                    try:
                        normalized_row[key] = int(value or 0)
                    except Exception:
                        normalized_row[key] = 0
                else:
                    normalized_row[str(key)] = str(value or "")
            summary.append(normalized_row)

    if not summary:
        return {}

    timestamp = str(item.get("timestamp", "") or datetime.now().strftime("%Y-%m-%d %H:%M"))
    title = str(item.get("title", "") or ("다중 목적지" if history_type == "multi_dest" else "날짜 범위"))
    return {
        "type": history_type,
        "timestamp": timestamp,
        "title": title,
        "params": params,
        "summary": summary,
    }
