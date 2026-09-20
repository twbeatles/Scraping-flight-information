"""Shared state contract for preference mixins (SRP support module)."""

from typing import Any, Dict


class PreferenceStoreBase:
    """Minimal state surface every preference mixin operates on.

    `PreferenceManager` provides the concrete attributes; mixins only
    declare the dependency so static analysis stays precise.
    """

    preferences: Dict[str, Any]
    filepath: str

    def save(self) -> None:
        raise NotImplementedError
