"""PreferenceManager composition root (SRP: lifecycle + delegation only)."""

import json
import logging
import os
from typing import Any, Dict

from core.file_io import write_text_atomic
from core.preferences.defaults import (
    default_preferences,
    has_required_search_fields,
    history_key,
    resolve_filepath,
)
from core.preferences.history import HistoryMixin
from core.preferences.normalize import normalize_advanced_history_item, normalize_preferences_payload
from core.preferences.presets import PresetsMixin
from core.preferences.profiles import ProfilesMixin
from core.preferences.settings import SettingsMixin


logger = logging.getLogger(__name__)


class PreferenceManager(PresetsMixin, HistoryMixin, ProfilesMixin, SettingsMixin):
    """Manage user preferences, presets, profiles, and history."""

    preferences: Dict[str, Any]
    filepath: str

    def __init__(self, filepath: str | None = None):
        self.filepath = resolve_filepath(filepath)
        self.preferences = self._load()

    def _default_preferences(self) -> Dict[str, Any]:
        return default_preferences()

    @staticmethod
    def _has_required_search_fields(params: Dict[str, Any]) -> bool:
        return has_required_search_fields(params)

    @staticmethod
    def _history_key(params: Dict[str, Any]) -> tuple[Any, ...]:
        return history_key(params)

    def _normalize_preferences_payload(self, raw: Dict[str, Any] | None) -> Dict[str, Any]:
        return normalize_preferences_payload(raw)

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
        return normalize_advanced_history_item(item)

    def save(self):
        try:
            self.preferences = self._normalize_preferences_payload(self.preferences)
            write_text_atomic(
                self.filepath,
                json.dumps(self.preferences, ensure_ascii=False, indent=4),
            )
        except Exception as e:
            logger.warning(f"Error saving preferences: {e}")
