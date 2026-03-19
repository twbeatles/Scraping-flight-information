"""Shared search-parameter helpers for SearchPanel/MainWindow flows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from PyQt6.QtCore import QDate

import config


def get_panel_search_params(
    panel: Any,
    *,
    include_timestamp: bool = False,
    timestamp: str | None = None,
) -> dict[str, Any]:
    params = {
        "origin": panel.cb_origin.currentData() or panel.cb_origin.currentText(),
        "dest": panel.cb_dest.currentData() or panel.cb_dest.currentText(),
        "dep": panel.date_dep.date().toString("yyyyMMdd"),
        "ret": panel.date_ret.date().toString("yyyyMMdd") if panel.rb_round.isChecked() else None,
        "adults": panel.spin_adults.value(),
        "cabin_class": panel.cb_cabin_class.currentData() or "ECONOMY",
    }
    if hasattr(panel, "rb_domestic"):
        params["is_domestic"] = bool(panel.rb_domestic.isChecked())
    if include_timestamp:
        params["timestamp"] = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M")
    return config.normalize_search_params(params)


def apply_search_params_to_panel(panel: Any, params: dict[str, Any] | None) -> dict[str, Any]:
    normalized = config.normalize_search_params(params)

    is_domestic = normalized.get("is_domestic", False)
    if hasattr(panel, "rb_domestic") and hasattr(panel, "rb_intl"):
        panel.rb_domestic.setChecked(is_domestic)
        panel.rb_intl.setChecked(not is_domestic)
        if hasattr(panel, "_on_flight_type_changed"):
            panel._on_flight_type_changed()

    origin = normalized.get("origin")
    if origin:
        idx = panel.cb_origin.findData(origin)
        if idx >= 0:
            panel.cb_origin.setCurrentIndex(idx)
        elif panel.cb_origin.isEditable():
            panel.cb_origin.setEditText(origin)

    dest = normalized.get("dest")
    if dest:
        idx = panel.cb_dest.findData(dest)
        if idx >= 0:
            panel.cb_dest.setCurrentIndex(idx)
        elif panel.cb_dest.isEditable():
            panel.cb_dest.setEditText(dest)

    dep = normalized.get("dep")
    if dep:
        dep_date = QDate.fromString(dep, "yyyyMMdd")
        if dep_date.isValid():
            panel.date_dep.setDate(dep_date)

    ret = normalized.get("ret")
    if ret:
        panel.rb_round.setChecked(True)
        if hasattr(panel, "_toggle_return_date"):
            panel._toggle_return_date()
        ret_date = QDate.fromString(ret, "yyyyMMdd")
        if ret_date.isValid():
            panel.date_ret.setDate(ret_date)
    else:
        panel.rb_oneway.setChecked(True)
        if hasattr(panel, "_toggle_return_date"):
            panel._toggle_return_date()

    try:
        panel.spin_adults.setValue(int(normalized.get("adults", 1) or 1))
    except Exception:
        panel.spin_adults.setValue(1)

    cabin = normalized.get("cabin_class")
    if cabin:
        idx = panel.cb_cabin_class.findData(cabin)
        if idx >= 0:
            panel.cb_cabin_class.setCurrentIndex(idx)

    return normalized
