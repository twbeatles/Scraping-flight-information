"""Dialogs for Flight Bot"""
import sys
import logging
from datetime import datetime, timedelta
from typing import Optional
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

logger = logging.getLogger(__name__)

MAX_MULTI_DESTINATIONS = 5
MAX_DATE_RANGE_DAYS = 30

def _validate_route_and_dates(parent, origin: str, dest: str, dep_date: QDate, ret_date: Optional[QDate] = None) -> bool:
    """공통 노선/날짜 검증"""
    if origin == dest:
        QMessageBox.warning(parent, "입력 오류", "출발지와 도착지가 같습니다.")
        return False

    today = QDate.currentDate()
    if dep_date < today:
        QMessageBox.warning(parent, "날짜 오류", "출발일이 오늘보다 이전입니다.")
        return False

    if ret_date is not None and ret_date < dep_date:
        QMessageBox.warning(parent, "날짜 오류", "귀국일이 출발일보다 이전입니다.")
        return False

    return True

# --- Calendar View Dialog ---
