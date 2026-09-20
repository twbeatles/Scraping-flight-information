"""Custom airport preset management (SRP: presets only)."""

from typing import Dict

from core.airports import AIRPORTS
from core.preferences.store import PreferenceStoreBase


class PresetsMixin(PreferenceStoreBase):
    def add_preset(self, code: str, name: str):
        self.preferences["custom_presets"][code] = name
        self.save()

    def remove_preset(self, code: str):
        if code in self.preferences["custom_presets"]:
            del self.preferences["custom_presets"][code]
            self.save()

    def get_all_presets(self) -> Dict[str, str]:
        return {**AIRPORTS, **self.preferences.get("custom_presets", {})}
