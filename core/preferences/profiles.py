"""Saved search profiles and last-search state (SRP: profiles only)."""

from typing import Any, Dict

from core.search_params import normalize_search_params
from core.preferences.defaults import has_required_search_fields
from core.preferences.store import PreferenceStoreBase


class ProfilesMixin(PreferenceStoreBase):
    def save_profile(self, name: str, params: Dict[str, Any]):
        normalized = normalize_search_params(params)
        if not has_required_search_fields(normalized):
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
            normalized if has_required_search_fields(normalized) else {}
        )
        self.save()

    def get_last_search(self) -> Dict[str, Any]:
        value = self.preferences.get("last_search", {})
        return normalize_search_params(value) if isinstance(value, dict) else {}
