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

class CombinationSelectorDialog(QDialog):
    """가는편/오는편 개별 선택 다이얼로그"""
    combination_selected = pyqtSignal(object, object)  # outbound_flight, return_flight
    
    def __init__(self, outbound_flights: list, return_flights: list, parent=None):
        super().__init__(parent)
        self.outbound_flights = outbound_flights
        self.return_flights = return_flights
        self.selected_outbound = None
        self.selected_return = None
        
        self.setWindowTitle("✈️ 가는편/오는편 조합 선택")
        self.setMinimumSize(1000, 600)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 상단 설명
        info = QLabel("가는편과 오는편을 각각 선택하여 원하는 조합을 만들 수 있습니다.")
        info.setStyleSheet("font-size: 13px; color: #94a3b8;")
        layout.addWidget(info)
        
        # 메인 컨텐츠 (좌: 가는편, 우: 오는편)
        content_layout = QHBoxLayout()
        
        # 가는편 리스트
        outbound_group = QGroupBox("✈️ 가는편 선택")
        outbound_layout = QVBoxLayout(outbound_group)
        
        self.list_outbound = QListWidget()
        self.list_outbound.setAlternatingRowColors(True)
        for i, flight in enumerate(self.outbound_flights):
            item_text = f"{flight.airline} | {flight.departure_time} → {flight.arrival_time} | {flight.price:,}원"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.list_outbound.addItem(item)
        self.list_outbound.currentRowChanged.connect(self._on_outbound_selected)
        outbound_layout.addWidget(self.list_outbound)
        
        content_layout.addWidget(outbound_group)
        
        # 오는편 리스트
        return_group = QGroupBox("🔙 오는편 선택")
        return_layout = QVBoxLayout(return_group)
        
        self.list_return = QListWidget()
        self.list_return.setAlternatingRowColors(True)
        for i, flight in enumerate(self.return_flights):
            item_text = f"{flight.airline} | {flight.departure_time} → {flight.arrival_time} | {flight.price:,}원"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.list_return.addItem(item)
        self.list_return.currentRowChanged.connect(self._on_return_selected)
        return_layout.addWidget(self.list_return)
        
        content_layout.addWidget(return_group)
        
        layout.addLayout(content_layout)
        
        # 선택된 조합 요약
        summary_frame = QFrame()
        summary_frame.setStyleSheet("background-color: #16213e; border-radius: 8px; padding: 15px;")
        summary_layout = QVBoxLayout(summary_frame)
        
        self.lbl_summary = QLabel("가는편과 오는편을 선택하세요")
        self.lbl_summary.setStyleSheet("font-size: 16px; font-weight: bold;")
        summary_layout.addWidget(self.lbl_summary)
        
        self.lbl_total = QLabel("")
        self.lbl_total.setStyleSheet("font-size: 24px; font-weight: bold; color: #22c55e;")
        summary_layout.addWidget(self.lbl_total)
        
        layout.addWidget(summary_frame)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        btn_confirm = QPushButton("✅ 이 조합으로 선택")
        btn_confirm.setEnabled(False)
        btn_confirm.clicked.connect(self._on_confirm)
        self.btn_confirm = btn_confirm
        
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.close)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_confirm)
        btn_layout.addWidget(btn_cancel)
        
        layout.addLayout(btn_layout)
    
    def _on_outbound_selected(self, row):
        if 0 <= row < len(self.outbound_flights):
            self.selected_outbound = self.outbound_flights[row]
            self._update_summary()
    
    def _on_return_selected(self, row):
        if 0 <= row < len(self.return_flights):
            self.selected_return = self.return_flights[row]
            self._update_summary()
    
    def _update_summary(self):
        if self.selected_outbound and self.selected_return:
            out = self.selected_outbound
            ret = self.selected_return
            
            total = out.price + ret.price
            
            self.lbl_summary.setText(
                f"가는편: {out.airline} {out.departure_time}→{out.arrival_time} ({out.price:,}원)\\n"
                f"오는편: {ret.airline} {ret.departure_time}→{ret.arrival_time} ({ret.price:,}원)"
            )
            self.lbl_total.setText(f"총 {total:,}원")
            self.btn_confirm.setEnabled(True)
        elif self.selected_outbound:
            self.lbl_summary.setText(f"가는편 선택됨: {self.selected_outbound.airline} - 오는편을 선택하세요")
            self.lbl_total.setText("")
            self.btn_confirm.setEnabled(False)
        elif self.selected_return:
            self.lbl_summary.setText(f"오는편 선택됨: {self.selected_return.airline} - 가는편을 선택하세요")
            self.lbl_total.setText("")
            self.btn_confirm.setEnabled(False)
    
    def _on_confirm(self):
        if self.selected_outbound and self.selected_return:
            self.combination_selected.emit(self.selected_outbound, self.selected_return)
            self.accept()

# --- Dialogs ---
