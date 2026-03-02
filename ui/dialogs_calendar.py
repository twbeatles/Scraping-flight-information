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

class CalendarViewDialog(QDialog):
    """월별 최저가 캘린더 뷰"""
    date_selected = pyqtSignal(str)  # 선택된 날짜 (yyyyMMdd)
    
    def __init__(self, price_data: dict, parent=None):
        """
        Args:
            price_data: {date_str: (min_price, airline)} 형식
        """
        super().__init__(parent)
        self.price_data = price_data
        self.setWindowTitle("📅 날짜별 최저가 캘린더")
        self.setMinimumSize(700, 550)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 범례
        legend = QLabel("🟢 최저가  🟡 중간  🔴 비쌈  ⬜ 데이터 없음")
        legend.setStyleSheet("font-size: 12px; color: #94a3b8;")
        layout.addWidget(legend)
        
        # 캘린더 위젯
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.setMinimumDate(QDate.currentDate())
        self.calendar.clicked.connect(self._on_date_clicked)
        layout.addWidget(self.calendar)
        
        # 가격 범위 계산
        if self.price_data:
            prices = [p for p, _ in self.price_data.values() if p > 0]
            if prices:
                self.min_price = min(prices)
                self.max_price = max(prices)
                self.price_range = self.max_price - self.min_price if self.max_price > self.min_price else 1
            else:
                self.min_price = self.max_price = self.price_range = 0
        else:
            self.min_price = self.max_price = self.price_range = 0
        
        # 날짜별 색상 적용
        self._apply_price_colors()
        
        # 선택된 날짜 정보
        self.lbl_info = QLabel("날짜를 클릭하면 해당 날짜로 검색합니다")
        self.lbl_info.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.lbl_info)
        
        # 버튼
        btn_layout = QHBoxLayout()
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.close)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
    
    def _apply_price_colors(self):
        """날짜별 가격에 따른 색상 적용"""
        for date_str, (price, airline) in self.price_data.items():
            if price <= 0:
                continue
            
            # 날짜 파싱
            try:
                qdate = QDate.fromString(date_str, "yyyyMMdd")
                if not qdate.isValid():
                    continue
            except Exception as e:
                logger.debug(f"Date parsing error: {e}")
                continue
            
            # 가격 기반 색상 결정
            if self.price_range > 0:
                ratio = (price - self.min_price) / self.price_range
            else:
                ratio = 0
            
            if ratio < 0.3:
                color = QColor("#22c55e")  # 녹색 - 저렴
            elif ratio < 0.6:
                color = QColor("#f59e0b")  # 주황색 - 중간
            else:
                color = QColor("#ef4444")  # 빨간색 - 비쌈
            
            # 캘린더 날짜에 포맷 적용
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            fmt.setForeground(QColor("white"))
            fmt.setToolTip(f"{price:,}원 ({airline})")
            self.calendar.setDateTextFormat(qdate, fmt)
    
    def _on_date_clicked(self, qdate):
        date_str = qdate.toString("yyyyMMdd")
        if date_str in self.price_data:
            price, airline = self.price_data[date_str]
            self.lbl_info.setText(f"📅 {qdate.toString('yyyy-MM-dd')}: {price:,}원 ({airline})")
        else:
            self.lbl_info.setText(f"📅 {qdate.toString('yyyy-MM-dd')}: 데이터 없음")
        
        # 시그널 발생
        self.date_selected.emit(date_str)


# --- Combination Selector Dialog ---
