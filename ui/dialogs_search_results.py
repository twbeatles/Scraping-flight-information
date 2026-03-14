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
        summary_label = QLabel("목적지별 최저가 비교:")
        summary_label.setObjectName("section_title")
        layout.addWidget(summary_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["목적지", "최저가", "항공사", "출발시간", "결과 수"])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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
        
        summary_label = QLabel("날짜별 최저가:")
        summary_label.setObjectName("section_title")
        layout.addWidget(summary_label)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["날짜", "요일", "최저가", "항공사"])
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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
