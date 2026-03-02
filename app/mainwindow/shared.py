"""Shared imports/constants for MainWindow mixins."""

import sys
import os
import time
import webbrowser
import json
import logging
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QDateEdit,
    QSpinBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QProgressBar,
    QFrame,
    QRadioButton,
    QButtonGroup,
    QAbstractItemView,
    QSizePolicy,
    QTabWidget,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QFileDialog,
    QLineEdit,
    QGroupBox,
    QGridLayout,
    QCheckBox,
    QSlider,
    QMenu,
    QCalendarWidget,
    QScrollArea,
    QToolButton,
    QInputDialog,
)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal, QSize, pyqtSlot, QTimer, QSettings
from PyQt6.QtGui import QFont, QColor, QIcon, QPalette, QShortcut, QKeySequence, QAction, QTextCharFormat

os.environ["QT_LOGGING_RULES"] = "qt.qpa.css.warning=false"

from scraper_v2 import FlightSearcher, FlightResult
import config
import scraper_config
from database import FlightDatabase

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from ui.styles import DARK_THEME, LIGHT_THEME
from ui.components import (
    NoWheelSpinBox,
    NoWheelComboBox,
    NoWheelDateEdit,
    NoWheelTabWidget,
    FilterPanel,
    ResultTable,
    LogViewer,
    SearchPanel,
)
from ui.workers import SearchWorker, MultiSearchWorker, DateRangeWorker, AlertAutoCheckWorker
from ui.dialogs import (
    CalendarViewDialog,
    CombinationSelectorDialog,
    MultiDestDialog,
    MultiDestResultDialog,
    DateRangeDialog,
    DateRangeResultDialog,
    ShortcutsDialog,
    PriceAlertDialog,
    SettingsDialog,
)

logger = logging.getLogger(__name__)
MODERN_THEME = DARK_THEME
MAX_PRICE_FILTER = 99_990_000
