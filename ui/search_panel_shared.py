"""Shared imports and type contracts for the search panel."""

from __future__ import annotations

import sys
import csv
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, cast
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QPushButton, QCheckBox,
    QSpinBox, QComboBox, QDateEdit, QTabWidget, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMenu, QMessageBox, QFileDialog, QApplication, QTextEdit,
    QRadioButton, QButtonGroup, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QDate, QSettings
from PyQt6.QtGui import QColor, QFont, QTextCharFormat

# Try importing openpyxl
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

import config

logger = logging.getLogger(__name__)

from ui.components_primitives import NoWheelSpinBox, NoWheelComboBox, NoWheelDateEdit


class SearchPanelPrefs(Protocol):
    def get_all_presets(self) -> dict[str, str]: ...
    def add_preset(self, code: str, name: str) -> None: ...
    def remove_preset(self, code: str) -> None: ...
    def get_preferred_time(self) -> dict[str, int]: ...
    def set_preferred_time(self, start: int, end: int) -> None: ...
    def get_all_profiles(self) -> dict[str, dict[str, Any]]: ...
    def save_profile(self, name: str, params: dict[str, Any]) -> None: ...
    def get_profile(self, name: str) -> dict[str, Any] | None: ...


if TYPE_CHECKING:
    class SearchPanelType(QFrame):
        prefs: SearchPanelPrefs
        search_requested: Any

        cb_profiles: QComboBox
        cb_origin: QComboBox
        cb_dest: QComboBox
        date_dep: QDateEdit
        date_ret: QDateEdit
        spin_adults: QSpinBox
        cb_cabin_class: QComboBox
        spin_time_start: QSpinBox
        spin_time_end: QSpinBox
        rb_round: QRadioButton
        rb_oneway: QRadioButton
        rb_domestic: QRadioButton
        rb_intl: QRadioButton
        rb_group: QButtonGroup
        flight_type_group: QButtonGroup
        btn_search: QPushButton

        def _init_ui(self) -> None: ...
        def _create_airport_combo(
            self, default_code: str = "ICN", include_presets: bool = False
        ) -> QComboBox: ...
        def _labeled_widget(self, label_text: str, widget: QWidget) -> QWidget: ...
        def _manage_preset(self, combo_widget: QComboBox | None = None) -> None: ...
        def _refresh_combos(self) -> None: ...
        def _toggle_return_date(self) -> None: ...
        def _on_search(self) -> None: ...
        def set_searching(self, searching: bool) -> None: ...
        def _on_flight_type_changed(self) -> None: ...
        def _refresh_profiles(self) -> None: ...
        def _save_current_profile(self) -> None: ...
        def _load_selected_profile(self) -> None: ...
        def _open_settings(self) -> None: ...
        def get_search_params(
            self, *, include_timestamp: bool = False, timestamp: str | None = None
        ) -> dict[str, Any]: ...
        def apply_search_params(self, params: dict[str, Any] | None) -> dict[str, Any]: ...
        def save_settings(self) -> None: ...
        def restore_settings(self) -> None: ...
else:
    class SearchPanelType(QFrame):
        pass


SearchPanelMixinBase = SearchPanelType if TYPE_CHECKING else object
