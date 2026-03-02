"""
Custom UI Components for Flight Bot
"""
import sys
import csv
import logging
from datetime import datetime
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

class LogViewer(QTextEdit):
    """실시간 로그 뷰어"""
    def __init__(self):
        super().__init__()
        self.setObjectName("log_view")
        self.setReadOnly(True)
        self.setPlaceholderText("검색 로그가 여기에 표시됩니다...")
    
    @pyqtSlot(str)
    def append_log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.append(f"[{timestamp}] {msg}")
        self.moveCursor(self.textCursor().MoveOperation.End)
