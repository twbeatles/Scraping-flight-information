"""Dialogs for Flight Bot"""
import sys
import logging
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QCalendarWidget, QGroupBox, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QDateEdit, QSpinBox, QCheckBox, QScrollArea, QGridLayout,
    QWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QTabWidget, QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QDate, QSettings
from PyQt6.QtGui import QColor, QFont, QTextCharFormat, QAction

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

import config
from ui.styles import MODERN_THEME
from ui.components_primitives import NoWheelSpinBox, NoWheelComboBox, NoWheelDateEdit

logger = logging.getLogger(__name__)

from ui.dialogs_base import _validate_route_and_dates, MAX_MULTI_DESTINATIONS, MAX_DATE_RANGE_DAYS
class MultiDestDialog(QDialog):
    """다중 목적지 선택 다이얼로그"""
    search_requested = pyqtSignal(str, list, str, str, int, str)  # origin, dests, dep, ret, adults, cabin_class
    
    def __init__(self, parent=None, prefs=None):
        super().__init__(parent)
        self.prefs = prefs
        self.setWindowTitle("🌍 다중 목적지 검색")
        self.setMinimumSize(500, 500)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Instructions
        layout.addWidget(QLabel("여러 목적지를 선택하여 한 번에 비교 검색합니다."))
        
        # Origin
        origin_layout = QHBoxLayout()
        origin_layout.addWidget(QLabel("출발지:"))
        self.cb_origin = QComboBox()
        for code, name in config.AIRPORTS.items():
            self.cb_origin.addItem(f"{code} ({name})", code)
        self.cb_origin.setCurrentIndex(0)
        self.cb_origin.currentIndexChanged.connect(self._on_origin_changed)
        origin_layout.addWidget(self.cb_origin)
        layout.addLayout(origin_layout)
        
        # Destination Checkboxes
        layout.addWidget(QLabel("도착지 선택 (다중 선택 가능):"))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        dest_widget = QWidget()
        dest_layout = QGridLayout(dest_widget)
        
        self.dest_checkboxes = {}
        all_presets = self.prefs.get_all_presets() if self.prefs else config.AIRPORTS
        
        row, col = 0, 0
        for code, name in all_presets.items():
            cb = QCheckBox(f"{code} ({name})")
            cb.setProperty("code", code)
            self.dest_checkboxes[code] = cb
            dest_layout.addWidget(cb, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
        
        scroll.setWidget(dest_widget)
        layout.addWidget(scroll, 1)
        
        # Select All / None
        btn_layout = QHBoxLayout()
        btn_all = QPushButton("모두 선택")
        btn_all.clicked.connect(lambda: self._toggle_all(True))
        btn_none = QPushButton("모두 해제")
        btn_none.clicked.connect(lambda: self._toggle_all(False))
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        layout.addLayout(btn_layout)
        
        # Dates
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("가는 날:"))
        self.date_dep = QDateEdit()
        self.date_dep.setCalendarPopup(True)
        self.date_dep.setDate(QDate.currentDate().addDays(7))
        date_layout.addWidget(self.date_dep)
        
        date_layout.addWidget(QLabel("오는 날:"))
        self.date_ret = QDateEdit()
        self.date_ret.setCalendarPopup(True)
        self.date_ret.setDate(QDate.currentDate().addDays(10))
        date_layout.addWidget(self.date_ret)
        layout.addLayout(date_layout)
        
        # Adults
        adult_layout = QHBoxLayout()
        adult_layout.addWidget(QLabel("성인:"))
        self.spin_adults = QSpinBox()
        self.spin_adults.setRange(1, 9)
        adult_layout.addWidget(self.spin_adults)
        adult_layout.addWidget(QLabel("좌석:"))
        self.cb_cabin_class = QComboBox()
        self.cb_cabin_class.addItem("💺 이코노미", "ECONOMY")
        self.cb_cabin_class.addItem("💼 비즈니스", "BUSINESS")
        self.cb_cabin_class.addItem("👑 일등석", "FIRST")
        adult_layout.addWidget(self.cb_cabin_class)
        adult_layout.addStretch()
        layout.addLayout(adult_layout)
        
        # Action Buttons (Cancel left, Action right - UX standard)
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        btn_cancel = QPushButton("❌ 취소")
        btn_cancel.setObjectName("secondary_btn")
        btn_cancel.clicked.connect(self.reject)
        action_layout.addWidget(btn_cancel)
        
        btn_search = QPushButton("🔍 다중 검색 시작")
        btn_search.clicked.connect(self._on_search)
        action_layout.addWidget(btn_search)
        
        layout.addLayout(action_layout)
        self._on_origin_changed()
    
    def _toggle_all(self, checked):
        for cb in self.dest_checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(checked)

    def _on_origin_changed(self):
        """출발지를 목적지 선택 목록에서 자동 제외."""
        origin = self.cb_origin.currentData()
        for code, cb in self.dest_checkboxes.items():
            is_origin = (code == origin)
            if is_origin:
                cb.setChecked(False)
            cb.setEnabled(not is_origin)
    
    def _on_search(self):
        selected = [code for code, cb in self.dest_checkboxes.items() if cb.isEnabled() and cb.isChecked()]
        
        if len(selected) < 2:
            QMessageBox.warning(self, "선택 오류", "최소 2개 이상의 목적지를 선택하세요.")
            return

        if len(selected) > MAX_MULTI_DESTINATIONS:
            QMessageBox.warning(
                self,
                "선택 오류",
                f"최대 {MAX_MULTI_DESTINATIONS}개 목적지만 선택할 수 있습니다."
            )
            return
        
        origin = self.cb_origin.currentData()
        dep_date = self.date_dep.date()
        ret_date = self.date_ret.date()

        if origin in selected:
            QMessageBox.warning(self, "선택 오류", "출발지는 도착지 목록에 포함할 수 없습니다.")
            return

        if not _validate_route_and_dates(self, origin, selected[0], dep_date, ret_date):
            return

        dep = dep_date.toString("yyyyMMdd")
        ret = ret_date.toString("yyyyMMdd")
        adults = self.spin_adults.value()
        cabin_class = self.cb_cabin_class.currentData() or "ECONOMY"
        
        self.search_requested.emit(origin, selected, dep, ret, adults, cabin_class)
        self.accept()
