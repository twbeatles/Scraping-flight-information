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

class NoWheelSpinBox(QSpinBox):
    """스크롤 휠에 반응하지 않는 SpinBox"""
    def wheelEvent(self, e):
        if e is not None:
            e.ignore()

class NoWheelComboBox(QComboBox):
    """스크롤 휠에 반응하지 않는 ComboBox"""
    def wheelEvent(self, e):
        if e is not None:
            e.ignore()

class NoWheelDateEdit(QDateEdit):
    """스크롤 휠에 반응하지 않는 DateEdit"""
    def wheelEvent(self, e):
        if e is not None:
            e.ignore()

class NoWheelTabWidget(QTabWidget):
    """스크롤 휠에 반응하지 않는 TabWidget"""
    def wheelEvent(self, a0):
        if a0 is not None:
            a0.ignore()
