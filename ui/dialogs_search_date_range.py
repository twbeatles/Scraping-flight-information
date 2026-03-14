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
class DateRangeDialog(QDialog):
    """날짜 범위 검색 다이얼로그"""
    search_requested = pyqtSignal(str, str, list, int, int, str)  # origin, dest, dates, return_offset, adults, cabin_class
    
    def __init__(self, parent=None, prefs=None):
        super().__init__(parent)
        self.prefs = prefs
        self.setWindowTitle("📅 날짜 범위 검색")
        self.setMinimumSize(450, 400)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("날짜 범위를 지정하여 가장 저렴한 날짜를 찾습니다."))
        
        # Origin & Dest
        route_layout = QHBoxLayout()
        route_layout.addWidget(QLabel("출발지:"))
        self.cb_origin = QComboBox()
        for code, name in config.AIRPORTS.items():
            self.cb_origin.addItem(f"{code} ({name})", code)
        route_layout.addWidget(self.cb_origin)
        
        route_layout.addWidget(QLabel("→"))
        
        route_layout.addWidget(QLabel("도착지:"))
        self.cb_dest = QComboBox()
        all_presets = self.prefs.get_all_presets() if self.prefs else config.AIRPORTS
        for code, name in all_presets.items():
            self.cb_dest.addItem(f"{code} ({name})", code)
        self.cb_dest.setCurrentIndex(1)  # 두 번째 항목
        route_layout.addWidget(self.cb_dest)
        layout.addLayout(route_layout)
        
        # Date Range
        layout.addWidget(QLabel("검색 날짜 범위:"))
        date_layout = QHBoxLayout()
        
        date_layout.addWidget(QLabel("시작:"))
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addDays(7))
        date_layout.addWidget(self.date_start)
        
        date_layout.addWidget(QLabel("종료:"))
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate().addDays(14))
        date_layout.addWidget(self.date_end)
        layout.addLayout(date_layout)
        
        # Trip Duration
        dur_layout = QHBoxLayout()
        dur_layout.addWidget(QLabel("여행 기간:"))
        self.spin_duration = QSpinBox()
        self.spin_duration.setRange(0, 30)
        self.spin_duration.setValue(3)
        self.spin_duration.setSuffix("박")
        dur_layout.addWidget(self.spin_duration)
        dur_layout.addWidget(QLabel("(0 = 편도)"))
        dur_layout.addStretch()
        layout.addLayout(dur_layout)
        
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
        
        # Note
        note = QLabel(f"⚠️ 날짜 범위가 넓을수록 검색 시간이 오래 걸립니다. (최대 {MAX_DATE_RANGE_DAYS}일)")
        note.setStyleSheet("color: #f0ad4e; font-size: 12px;")
        layout.addWidget(note)
        
        layout.addStretch()
        
        # Actions
        action_layout = QHBoxLayout()
        btn_search = QPushButton("🔍 날짜 검색 시작")
        btn_search.clicked.connect(self._on_search)
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        action_layout.addWidget(btn_search)
        action_layout.addWidget(btn_cancel)
        layout.addLayout(action_layout)
    
    def _on_search(self):
        start = self.date_start.date()
        end = self.date_end.date()
        today = QDate.currentDate()
        origin = self.cb_origin.currentData()
        dest = self.cb_dest.currentData()
        duration = self.spin_duration.value()
        adults = self.spin_adults.value()
        cabin_class = self.cb_cabin_class.currentData() or "ECONOMY"
        
        if origin == dest:
            QMessageBox.warning(self, "입력 오류", "출발지와 도착지가 같습니다.")
            return

        if start < today:
            QMessageBox.warning(self, "날짜 오류", "시작 날짜가 오늘보다 이전입니다.")
            return

        if end < start:
            QMessageBox.warning(self, "날짜 오류", "종료 날짜는 시작 날짜와 같거나 이후여야 합니다.")
            return

        if duration > 0:
            max_return = end.addDays(duration)
            if max_return < today:
                QMessageBox.warning(self, "날짜 오류", "여행 기간을 포함한 귀국일이 오늘보다 이전입니다.")
                return

        # Generate date list (start == end 허용)
        dates = []
        current = start
        while current <= end:
            dates.append(current.toString("yyyyMMdd"))
            current = current.addDays(1)

        if len(dates) > MAX_DATE_RANGE_DAYS:
            QMessageBox.warning(
                self,
                "날짜 범위 초과",
                f"날짜 범위 검색은 최대 {MAX_DATE_RANGE_DAYS}일까지 가능합니다."
            )
            return

        if len(dates) > 14:
            reply = QMessageBox.question(
                self, "확인",
                f"{len(dates)}일을 검색합니다. 시간이 오래 걸릴 수 있습니다.\\n계속하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.search_requested.emit(origin, dest, dates, duration, adults, cabin_class)
        self.accept()
