"""Search history management (SRP: simple + advanced history only)."""

from typing import Any, Dict, List

from core.search_params import normalize_search_params
from core.preferences.defaults import has_required_search_fields, history_key
from core.preferences.normalize import normalize_advanced_history_item
from core.preferences.store import PreferenceStoreBase


class HistoryMixin(PreferenceStoreBase):
    def add_history(self, search_info: Dict[str, Any]):
        normalized = normalize_search_params(search_info)
        if not has_required_search_fields(normalized):
            return

        history = []
        new_key = history_key(normalized)
        for item in self.preferences["search_history"]:
            if history_key(item) != new_key:
                history.append(item)
        history.insert(0, normalized)
        self.preferences["search_history"] = history[:20]
        self.save()

    def get_history(self) -> List[Dict[str, Any]]:
        return self.preferences["search_history"]

    def add_advanced_history(self, history_item: Dict[str, Any]):
        normalized = normalize_advanced_history_item(history_item)
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
