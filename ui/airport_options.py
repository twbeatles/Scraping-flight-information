"""Shared airport combo-box helpers."""

from __future__ import annotations

from typing import Any, Iterable

from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QComboBox

import config


def get_airport_options(
    prefs: Any = None,
    *,
    is_domestic: bool = False,
    include_presets: bool = True,
) -> list[tuple[str, str]]:
    """Return ordered airport options for the requested route mode."""

    if is_domestic:
        base_items: Iterable[tuple[str, str]] = config.DOMESTIC_AIRPORTS.items()
        preset_names = {}
        if include_presets and prefs is not None:
            try:
                preset_names = prefs.get_all_presets()
            except Exception:
                preset_names = {}
        return [
            (code, str(preset_names.get(code, name)))
            for code, name in base_items
            if code in config.DOMESTIC_AIRPORT_CODES
        ]

    options: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add_option(code: Any, name: Any) -> None:
        normalized = str(code or "").strip().upper()
        if not config.validate_airport_code(normalized) or normalized in seen:
            return
        seen.add(normalized)
        options.append((normalized, str(name or normalized).strip() or normalized))

    for code, name in config.AIRPORTS.items():
        add_option(code, name)

    if include_presets and prefs is not None:
        try:
            presets = prefs.get_all_presets()
        except Exception:
            presets = {}
        if isinstance(presets, dict):
            for code, name in presets.items():
                add_option(code, name)

    return options


def populate_airport_combo(
    combo: QComboBox,
    prefs: Any = None,
    *,
    is_domestic: bool = False,
    include_presets: bool = True,
    current_code: str | None = None,
    default_code: str | None = None,
) -> str:
    """Populate a combo box and select current/default code when available."""

    selected_code = str(current_code or combo.currentData() or "").strip().upper()
    fallback_code = str(default_code or selected_code or "").strip().upper()
    options = get_airport_options(
        prefs,
        is_domestic=is_domestic,
        include_presets=include_presets,
    )

    with QSignalBlocker(combo):
        combo.clear()
        for code, name in options:
            combo.addItem(f"{code} ({name})", code)

        for code in (selected_code, fallback_code):
            if not code:
                continue
            idx = combo.findData(code)
            if idx >= 0:
                combo.setCurrentIndex(idx)
                return code

        if combo.count() > 0:
            combo.setCurrentIndex(0)
            value = combo.currentData()
            return str(value or "")

    return ""
