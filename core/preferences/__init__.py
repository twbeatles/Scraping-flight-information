"""User preference persistence and normalization (package facade).

Split (SOLID/SRP) without breaking the public contract:
`from core.preferences import PreferenceManager` keeps working, and the
historical private helpers remain importable from this package.
"""

from core.preferences.defaults import (
    default_preferences,
    has_required_search_fields,
    history_key,
    resolve_filepath,
)
from core.preferences.history import HistoryMixin
from core.preferences.manager import PreferenceManager
from core.preferences.normalize import normalize_advanced_history_item, normalize_preferences_payload
from core.preferences.presets import PresetsMixin
from core.preferences.profiles import ProfilesMixin
from core.preferences.settings import SettingsMixin
from core.preferences.store import PreferenceStoreBase

__all__ = [
    "PreferenceManager",
    "PreferenceStoreBase",
    "PresetsMixin",
    "HistoryMixin",
    "ProfilesMixin",
    "SettingsMixin",
    "default_preferences",
    "normalize_preferences_payload",
    "normalize_advanced_history_item",
    "has_required_search_fields",
    "history_key",
    "resolve_filepath",
]
