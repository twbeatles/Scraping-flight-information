"""User preference persistence and normalization."""

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

from core.airports import AIRPORTS, _extract_airport_code, validate_airport_code
from core.search_params import (
    SEARCH_PARAMS_SCHEMA_VERSION,
    _coerce_bool,
    normalize_search_params,
)
from core.file_io import write_text_atomic


logger = logging.getLogger(__name__)


class PreferenceManager:
    """Manage user preferences, presets, profiles, and history."""

    def __init__(self, filepath: str | None = None):
        if filepath is None:
            if getattr(sys, "frozen", False):
                app_data = os.path.join(
                    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                    "FlightBot",
                )
                os.makedirs(app_data, exist_ok=True)
                self.filepath = os.path.join(app_data, "user_preferences.json")
            else:
                self.filepath = "user_preferences.json"
        else:
            self.filepath = filepath

        self.preferences = self._load()

    def _default_preferences(self) -> Dict[str, Any]:
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

    @staticmethod
    def _has_required_search_fields(params: Dict[str, Any]) -> bool:
        return bool(params.get("origin") and params.get("dest") and params.get("dep"))

    @staticmethod
    def _history_key(params: Dict[str, Any]) -> tuple[Any, ...]:
        return (
            params.get("origin", ""),
            params.get("dest", ""),
            params.get("dep", ""),
            params.get("ret") or "",
            int(params.get("adults", 1) or 1),
            params.get("cabin_class", "ECONOMY"),
            bool(params.get("is_domestic", False)),
        )

    def _normalize_preferences_payload(self, raw: Dict[str, Any] | None) -> Dict[str, Any]:
        default_prefs = self._default_preferences()
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
                if not self._has_required_search_fields(normalized):
                    continue
                key = self._history_key(normalized)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                history_items.append(normalized)
        prefs["search_history"] = history_items[:20]

        advanced_history: List[Dict[str, Any]] = []
        raw_advanced_history = raw_dict.get("advanced_search_history", [])
        if isinstance(raw_advanced_history, list):
            for item in raw_advanced_history:
                normalized_item = self._normalize_advanced_history_item(item)
                if normalized_item:
                    advanced_history.append(normalized_item)
        prefs["advanced_search_history"] = advanced_history[:20]

        last_search = raw_dict.get("last_search", {})
        if isinstance(last_search, dict):
            normalized_last_search = normalize_search_params(last_search)
            prefs["last_search"] = (
                normalized_last_search if self._has_required_search_fields(normalized_last_search) else {}
            )

        profiles = raw_dict.get("saved_profiles", {})
        normalized_profiles: Dict[str, Dict[str, Any]] = {}
        if isinstance(profiles, dict):
            for name, value in profiles.items():
                if not isinstance(value, dict):
                    continue
                normalized = normalize_search_params(value)
                if self._has_required_search_fields(normalized):
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

    def _load(self) -> Dict[str, Any]:
        default_prefs = self._default_preferences()

        if not os.path.exists(self.filepath):
            return default_prefs

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return self._normalize_preferences_payload(json.load(f))
        except Exception as e:
            logger.warning(f"Error loading preferences: {e}")
            return default_prefs

    def _normalize_advanced_history_item(self, item: Any) -> Dict[str, Any]:
        if not isinstance(item, dict):
            return {}

        history_type = str(item.get("type", "") or "").strip()
        if history_type not in {"multi_dest", "date_range"}:
            return {}

        raw_params = item.get("params", {})
        params = normalize_search_params(raw_params if isinstance(raw_params, dict) else {})
        if not self._has_required_search_fields(params):
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

    def save(self):
        try:
            self.preferences = self._normalize_preferences_payload(self.preferences)
            write_text_atomic(
                self.filepath,
                json.dumps(self.preferences, ensure_ascii=False, indent=4),
            )
        except Exception as e:
            logger.warning(f"Error saving preferences: {e}")

    def add_preset(self, code: str, name: str):
        self.preferences["custom_presets"][code] = name
        self.save()

    def remove_preset(self, code: str):
        if code in self.preferences["custom_presets"]:
            del self.preferences["custom_presets"][code]
            self.save()

    def get_all_presets(self) -> Dict[str, str]:
        return {**AIRPORTS, **self.preferences.get("custom_presets", {})}

    def add_history(self, search_info: Dict[str, Any]):
        normalized = normalize_search_params(search_info)
        if not self._has_required_search_fields(normalized):
            return

        history = []
        new_key = self._history_key(normalized)
        for item in self.preferences["search_history"]:
            if self._history_key(item) != new_key:
                history.append(item)
        history.insert(0, normalized)
        self.preferences["search_history"] = history[:20]
        self.save()

    def get_history(self) -> List[Dict[str, Any]]:
        return self.preferences["search_history"]

    def add_advanced_history(self, history_item: Dict[str, Any]):
        normalized = self._normalize_advanced_history_item(history_item)
        if not normalized:
            return

        history = [normalized]
        new_key = (
            normalized.get("type"),
            normalized.get("timestamp"),
            normalized.get("params", {}).get("origin"),
            normalized.get("params", {}).get("dest"),
            normalized.get("params", {}).get("dep"),
        )
        for item in self.preferences.get("advanced_search_history", []):
            item_key = (
                item.get("type"),
                item.get("timestamp"),
                item.get("params", {}).get("origin"),
                item.get("params", {}).get("dest"),
                item.get("params", {}).get("dep"),
            )
            if item_key != new_key:
                history.append(item)
        self.preferences["advanced_search_history"] = history[:20]
        self.save()

    def get_advanced_history(self) -> List[Dict[str, Any]]:
        history = self.preferences.get("advanced_search_history", [])
        return history if isinstance(history, list) else []

    def save_profile(self, name: str, params: Dict[str, Any]):
        normalized = normalize_search_params(params)
        if not self._has_required_search_fields(normalized):
            return
        self.preferences["saved_profiles"][name] = normalized
        self.save()

    def get_profile(self, name: str) -> Dict[str, Any]:
        value = self.preferences["saved_profiles"].get(name, {})
        return normalize_search_params(value) if isinstance(value, dict) else {}

    def delete_profile(self, name: str):
        if name in self.preferences["saved_profiles"]:
            del self.preferences["saved_profiles"][name]
            self.save()

    def get_all_profiles(self) -> Dict[str, Any]:
        profiles = self.preferences.get("saved_profiles", {})
        if not isinstance(profiles, dict):
            return {}
        return {
            str(name): normalize_search_params(value)
            for name, value in profiles.items()
            if isinstance(value, dict)
        }

    def save_last_search(self, data: Dict[str, Any]):
        normalized = normalize_search_params(data)
        self.preferences["last_search"] = (
            normalized if self._has_required_search_fields(normalized) else {}
        )
        self.save()

    def get_last_search(self) -> Dict[str, Any]:
        value = self.preferences.get("last_search", {})
        return normalize_search_params(value) if isinstance(value, dict) else {}

    def set_preferred_time(self, start: int, end: int):
        self.preferences["preferred_times"] = {"departure_start": start, "departure_end": end}
        self.save()

    def get_preferred_time(self) -> Dict[str, int]:
        return self.preferences.get("preferred_times", {"departure_start": 0, "departure_end": 24})

    def set_max_results(self, limit: int):
        self.preferences["max_results"] = limit
        self.save()

    def get_max_results(self) -> int:
        return self.preferences.get("max_results", 1000)

    def get_theme(self) -> str:
        return self.preferences.get("theme", "dark")

    def set_theme(self, theme: str):
        if theme in ("dark", "light"):
            self.preferences["theme"] = theme
            self.save()

    def set_alert_auto_check(self, enabled: bool, interval_min: int):
        safe_interval = max(5, min(int(interval_min), 1440))
        self.preferences["alert_auto_check_enabled"] = bool(enabled)
        self.preferences["alert_auto_check_interval_min"] = safe_interval
        self.save()

    def get_alert_auto_check(self) -> Dict[str, Any]:
        raw_interval = self.preferences.get("alert_auto_check_interval_min", 30)
        try:
            interval_min = int(raw_interval)
        except Exception:
            interval_min = 30
        return {
            "enabled": bool(self.preferences.get("alert_auto_check_enabled", False)),
            "interval_min": max(5, min(interval_min, 1440)),
            "hit_modal_enabled": bool(self.preferences.get("alert_hit_modal_enabled", True)),
        }

    def set_alert_hit_modal_enabled(self, enabled: bool) -> None:
        self.preferences["alert_hit_modal_enabled"] = bool(enabled)
        self.save()

    def get_alert_hit_modal_enabled(self) -> bool:
        return bool(self.preferences.get("alert_hit_modal_enabled", True))

    def export_all_settings(self, filepath: str) -> bool:
        try:
            write_text_atomic(
                filepath,
                json.dumps(self.preferences, ensure_ascii=False, indent=4),
            )
            logger.info(f"Settings exported to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            return False

    def import_settings(self, filepath: str) -> bool:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                imported = json.load(f)

            if not isinstance(imported, dict):
                raise ValueError("Settings payload must be a JSON object")

            merged = dict(self.preferences)
            imported_presets = imported.get("custom_presets")
            if isinstance(imported_presets, dict):
                merged["custom_presets"] = {**self.preferences.get("custom_presets", {}), **imported_presets}

            imported_profiles = imported.get("saved_profiles")
            if isinstance(imported_profiles, dict):
                merged["saved_profiles"] = {**self.preferences.get("saved_profiles", {}), **imported_profiles}

            imported_last_search = imported.get("last_search")
            if isinstance(imported_last_search, dict):
                merged["last_search"] = imported_last_search

            imported_history = imported.get("search_history")
            if isinstance(imported_history, list):
                merged["search_history"] = imported_history + list(self.preferences.get("search_history", []))

            imported_advanced_history = imported.get("advanced_search_history")
            if isinstance(imported_advanced_history, list):
                merged["advanced_search_history"] = imported_advanced_history + list(
                    self.preferences.get("advanced_search_history", [])
                )

            for key, value in imported.items():
                if key in {
                    "custom_presets",
                    "saved_profiles",
                    "last_search",
                    "search_history",
                    "advanced_search_history",
                }:
                    continue
                merged[key] = value

            self.preferences = self._normalize_preferences_payload(merged)
            self.save()
            logger.info(f"Settings imported from: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            return False
