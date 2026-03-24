"""Dialogs for Flight Bot"""
import sys
import logging
from datetime import datetime, timedelta
from typing import Any, cast
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
    openpyxl = None
    HAS_OPENPYXL = False

import config
from ui.styles import MODERN_THEME
from ui.components_primitives import NoWheelSpinBox, NoWheelComboBox, NoWheelDateEdit
from ui.dialogs_base import _validate_route_and_dates

logger = logging.getLogger(__name__)
class ShortcutsDialog(QDialog):
    """키보드 단축키 도움말 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⌨️ 키보드 단축키")
        self.setMinimumSize(400, 300)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        title = QLabel("키보드 단축키 목록")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4cc9f0;")
        layout.addWidget(title)
        
        shortcuts = [
            ("Ctrl + Enter", "검색 시작"),
            ("F5", "결과 새로고침 (필터 재적용)"),
            ("Escape", "검색 취소 / 다이얼로그 닫기"),
            ("Ctrl + F", "필터 항공사 선택으로 이동"),
            ("더블클릭", "결과 행에서 현재 조건 검색 열기"),
            ("우클릭", "결과 행에서 컨텍스트 메뉴"),
        ]
        
        for key, desc in shortcuts:
            row = QHBoxLayout()
            key_label = QLabel(key)
            key_label.setStyleSheet("""
                background-color: #0f3460;
                color: #4cc9f0;
                padding: 5px 10px;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
                font-weight: bold;
            """)
            key_label.setFixedWidth(120)
            row.addWidget(key_label)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #e6e6e6;")
            row.addWidget(desc_label)
            row.addStretch()
            
            layout.addLayout(row)
        
        layout.addStretch()
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
