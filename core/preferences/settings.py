"""UI/behavioral settings and settings backup (SRP: scalar settings only)."""

import json
import logging
from typing import Any, Dict

from core.file_io import write_text_atomic
from core.preferences.normalize import normalize_preferences_payload
from core.preferences.store import PreferenceStoreBase


logger = logging.getLogger(__name__)


class SettingsMixin(PreferenceStoreBase):
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

            self.preferences = normalize_preferences_payload(merged)
            self.save()
            logger.info(f"Settings imported from: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            return False
