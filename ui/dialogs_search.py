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

class MultiDestResultDialog(QDialog):
    """다중 목적지 검색 결과 비교 다이얼로그"""
    
    def __init__(self, results: dict, parent=None):
        super().__init__(parent)
        self.results = results  # {dest: [FlightResult]}
        self.setWindowTitle("🌍 다중 목적지 비교 결과")
        self.setMinimumSize(700, 500)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Summary Table
        layout.addWidget(QLabel("목적지별 최저가 비교:", objectName="section_title"))
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["목적지", "최저가", "항공사", "출발시간", "결과 수"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        
        # Sort by lowest price
        sorted_results = sorted(
            self.results.items(), 
            key=lambda x: min(r.price for r in x[1]) if x[1] else float('inf')
        )
        
        self.table.setRowCount(len(sorted_results))
        
        for i, (dest, flights) in enumerate(sorted_results):
            dest_name = config.AIRPORTS.get(dest, dest)
            self.table.setItem(i, 0, QTableWidgetItem(f"{dest} ({dest_name})"))
            
            if flights:
                best = min(flights, key=lambda x: x.price)
                
                price_item = QTableWidgetItem(f"{best.price:,}원")
                price_item.setForeground(QColor("#4cc9f0"))
                self.table.setItem(i, 1, price_item)
                self.table.setItem(i, 2, QTableWidgetItem(best.airline))
                self.table.setItem(i, 3, QTableWidgetItem(best.departure_time))
                self.table.setItem(i, 4, QTableWidgetItem(str(len(flights))))
            else:
                self.table.setItem(i, 1, QTableWidgetItem("N/A"))
                self.table.setItem(i, 2, QTableWidgetItem("-"))
                self.table.setItem(i, 3, QTableWidgetItem("-"))
                self.table.setItem(i, 4, QTableWidgetItem("0"))
        
        layout.addWidget(self.table)
        
        # Best recommendation
        if sorted_results and sorted_results[0][1]:
            best_dest = sorted_results[0][0]
            best_price = min(r.price for r in sorted_results[0][1])
            rec_label = QLabel(f"💡 추천: {best_dest} ({config.AIRPORTS.get(best_dest, '')}) - {best_price:,}원")
            rec_label.setStyleSheet("font-size: 16px; color: #4cc9f0; font-weight: bold; padding: 10px;")
            layout.addWidget(rec_label)
        
        # Close button
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

class DateRangeResultDialog(QDialog):
    """날짜 범위 검색 결과 다이얼로그"""
    
    def __init__(self, results: dict, parent=None):
        super().__init__(parent)
        self.results = results  # {date: (price, airline)}
        self.setWindowTitle("📅 날짜별 최저가 결과")
        self.setMinimumSize(600, 500)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("날짜별 최저가:", objectName="section_title"))
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["날짜", "요일", "최저가", "항공사"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        
        sorted_dates = sorted(self.results.items(), key=lambda x: x[0])
        self.table.setRowCount(len(sorted_dates))
        
        min_price = min((p for p, a in self.results.values() if p > 0), default=0)
        
        weekdays = ["월", "화", "수", "목", "금", "토", "일"]
        
        for i, (date, (price, airline)) in enumerate(sorted_dates):
            # Format date
            try:
                dt = datetime.strptime(date, "%Y%m%d")
                date_str = dt.strftime("%Y-%m-%d")
                weekday = weekdays[dt.weekday()]
            except:
                date_str = date
                weekday = "-"
            
            self.table.setItem(i, 0, QTableWidgetItem(date_str))
            self.table.setItem(i, 1, QTableWidgetItem(weekday))
            
            if price > 0:
                price_item = QTableWidgetItem(f"{price:,}원")
                if price == min_price:
                    price_item.setForeground(QColor("#00ff00"))
                    price_item.setFont(QFont("Pretendard", 10, QFont.Weight.Bold))
                else:
                    price_item.setForeground(QColor("#4cc9f0"))
                self.table.setItem(i, 2, price_item)
                self.table.setItem(i, 3, QTableWidgetItem(airline))
            else:
                self.table.setItem(i, 2, QTableWidgetItem("N/A"))
                self.table.setItem(i, 3, QTableWidgetItem("-"))
        
        layout.addWidget(self.table)
        
        # Best date
        valid_results = [(d, p, a) for d, (p, a) in self.results.items() if p > 0]
        if valid_results:
            best = min(valid_results, key=lambda x: x[1])
            try:
                best_dt = datetime.strptime(best[0], "%Y%m%d")
                best_str = best_dt.strftime("%Y-%m-%d (%a)")
            except Exception as e:
                logger.debug(f"Date format error: {e}")
                best_str = best[0]
            rec_label = QLabel(f"💡 최저가 날짜: {best_str} - {best[1]:,}원 ({best[2]})")
            rec_label.setStyleSheet("font-size: 16px; color: #00ff00; font-weight: bold; padding: 10px;")
            layout.addWidget(rec_label)
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
