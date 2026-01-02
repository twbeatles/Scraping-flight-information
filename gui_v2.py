"""
Flight Comparison Bot V2.3 - Modern GUI
Modular, card-based interface with dark theme and Playwright integration.
Enhanced with multi-destination search, date range search, airline filters,
favorites, price history, and improved UI/UX.
"""

import sys
import os

# Qt CSS 경고 억제 (Unknown property content 등)
os.environ["QT_LOGGING_RULES"] = "qt.qpa.css.warning=false"

import webbrowser
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QDateEdit, QSpinBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QProgressBar, QFrame, QRadioButton, QButtonGroup, QAbstractItemView,
    QSizePolicy, QTabWidget, QTextEdit, QListWidget, QListWidgetItem,
    QDialog, QFileDialog, QLineEdit, QGroupBox, QGridLayout,
    QCheckBox, QSlider, QMenu, QCalendarWidget, QScrollArea,
    QToolButton, QInputDialog
)
from PyQt6.QtCore import QDate, Qt, QThread, pyqtSignal, QSize, pyqtSlot, QTimer, QSettings
from PyQt6.QtGui import QFont, QColor, QIcon, QPalette, QShortcut, QKeySequence, QAction

from scraper_v2 import FlightSearcher, FlightResult
import config
from database import FlightDatabase

# Try importing openpyxl
try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# matplotlib 제거 (차트 미사용)
HAS_MATPLOTLIB = False
# --- Styling ---
DARK_THEME = """
/* ===== Base Application ===== */
QMainWindow, QWidget {
    background-color: #1a1a2e;
    color: #e6e6e6;
    font-family: 'Pretendard', 'Malgun Gothic', 'Segoe UI', sans-serif;
    font-size: 14px;
}

/* ===== Typography ===== */
QLabel#title {
    font-size: 26px;
    font-weight: bold;
    color: #4cc9f0;
    margin-bottom: 5px;
}
QLabel#subtitle {
    font-size: 13px;
    color: #94a3b8;
    margin-bottom: 15px;
}
QLabel#section_title {
    font-size: 15px;
    font-weight: bold;
    color: #e2e8f0;
    margin-top: 10px;
    margin-bottom: 8px;
    padding-left: 5px;
    border-left: 3px solid #4cc9f0;
}
QLabel#field_label {
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 3px;
}

/* ===== Cards (Container Panels) ===== */
QFrame#card {
    background-color: #16213e;
    border: 1px solid #30475e;
    border-radius: 12px;
    padding: 20px;
}
QFrame#card:hover {
    border: 1px solid #4cc9f080;
}

/* ===== Input Fields ===== */
QComboBox, QDateEdit, QSpinBox, QLineEdit {
    background-color: #0f3460;
    border: 1px solid #30475e;
    border-radius: 8px;
    padding: 10px 14px;
    color: white;
    selection-background-color: #4cc9f0;
    min-height: 22px;
}
QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QLineEdit:hover {
    border: 1px solid #4cc9f0;
}
QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QLineEdit:focus {
    border: 2px solid #4cc9f0;
    background-color: #0f3460;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
    background: transparent;
}
QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid #4cc9f0;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #30475e;
    selection-background-color: #4361ee;
    color: white;
    padding: 5px;
}

/* ===== Checkboxes ===== */
QCheckBox {
    spacing: 8px;
    color: #e6e6e6;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #30475e;
    background-color: #0f3460;
}
QCheckBox::indicator:hover {
    border: 2px solid #4cc9f0;
}
QCheckBox::indicator:checked {
    background-color: #4cc9f0;
    border: 2px solid #4cc9f0;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMxYTFhMmUiIHN0cm9rZS13aWR0aD0iMyIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSIyMCA2IDkgMTcgNCAxMiI+PC9wb2x5bGluZT48L3N2Zz4=);
}

/* ===== Radio Buttons ===== */
QRadioButton {
    spacing: 8px;
    color: #e6e6e6;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #30475e;
    background-color: #0f3460;
}
QRadioButton::indicator:hover {
    border: 2px solid #4cc9f0;
}
QRadioButton::indicator:checked {
    background-color: #4cc9f0;
    border: 2px solid #4cc9f0;
}
QRadioButton::indicator:checked::after {
    content: "";
    width: 8px;
    height: 8px;
    border-radius: 4px;
    background: #1a1a2e;
}

/* ===== Buttons ===== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #4361ee, stop:1 #7c3aed);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
    min-height: 20px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #5b7cfa, stop:1 #8b5cf6);
    /* 글로우 효과 - border로 구현 */
    border: 2px solid #a78bfa;
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #3b54d4, stop:1 #6d28d9);
    padding-top: 12px;
    padding-bottom: 8px;
}
QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}

/* Tool Buttons (Secondary) */
QPushButton#tool_btn {
    background-color: #30475e;
    color: #e2e8f0;
    padding: 8px 14px;
    border-radius: 6px;
}
QPushButton#tool_btn:hover {
    background-color: #4cc9f0;
    color: #1a1a2e;
}

/* Filter/Toggle Buttons */
QPushButton#filter_btn {
    background-color: transparent;
    border: 1px solid #30475e;
    color: #94a3b8;
    border-radius: 6px;
}
QPushButton#filter_btn:checked, QPushButton#filter_btn:hover {
    background-color: #4cc9f015;
    border: 1px solid #4cc9f0;
    color: #4cc9f0;
}

/* Manual Extract Button (Attention) */
QPushButton#manual_btn {
    background-color: #f72585;
    font-size: 15px;
    padding: 12px 20px;
}
QPushButton#manual_btn:hover {
    background-color: #ff3d9a;
}

/* ===== Table ===== */
QTableWidget {
    background-color: #16213e;
    border: 1px solid #30475e;
    border-radius: 8px;
    gridline-color: #30475e;
    selection-background-color: #4361ee40;
    selection-color: white;
    alternate-background-color: #1a1a2e;
}
QTableWidget::item {
    padding: 8px 6px;
    border-bottom: 1px solid #30475e20;
}
QTableWidget::item:selected {
    background-color: #4361ee40;
}
QTableWidget::item:hover {
    background-color: #4cc9f010;
}
QHeaderView::section {
    background-color: #0f3460;
    color: #94a3b8;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid #4cc9f0;
    font-weight: bold;
    font-size: 12px;
}

/* ===== Scrollbars ===== */
QScrollBar:vertical {
    border: none;
    background: #0f3460;
    width: 12px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #4cc9f0;
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #7dd3fc;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #0f3460;
    height: 12px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #4cc9f0;
    border-radius: 6px;
    min-width: 30px;
}

/* ===== Tab Widget ===== */
QTabWidget::pane {
    border: 1px solid #30475e;
    background: #16213e;
    border-radius: 0 8px 8px 8px;
    padding: 5px;
}
QTabBar::tab {
    background: #0f3460;
    color: #94a3b8;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #16213e;
    color: #4cc9f0;
    border-bottom: 3px solid #4cc9f0;
}
QTabBar::tab:hover:!selected {
    background: #1e3a5f;
    color: #e2e8f0;
}

/* ===== Log View ===== */
QTextEdit#log_view {
    background-color: #0a0a12;
    color: #a8b4c2;
    border: 1px solid #30475e;
    border-radius: 8px;
    font-family: 'Consolas', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    padding: 10px;
    selection-background-color: #4361ee;
}

/* ===== Progress Bar ===== */
QProgressBar {
    background: #16213e;
    border-radius: 8px;
    text-align: center;
    color: white;
    border: 1px solid #30475e;
    height: 28px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #4cc9f0);
    border-radius: 7px;
}

/* ===== Tooltips ===== */
QToolTip {
    background-color: #0f3460;
    color: #e6e6e6;
    border: 1px solid #4cc9f0;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}

/* ===== List Widget ===== */
QListWidget {
    background-color: #16213e;
    border: 1px solid #30475e;
    border-radius: 8px;
    padding: 5px;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background-color: #4361ee40;
    color: #4cc9f0;
}
QListWidget::item:hover {
    background-color: #30475e50;
}

/* ===== Message Boxes ===== */
QMessageBox {
    background-color: #1a1a2e;
}
QMessageBox QLabel {
    color: #e6e6e6;
}

/* ===== Status Bar ===== */
QStatusBar {
    background-color: #0f3460;
    color: #94a3b8;
    border-top: 1px solid #30475e;
    padding: 5px;
}
"""

# 라이트 테마
LIGHT_THEME = """
/* ===== Base Application ===== */
QMainWindow, QWidget {
    background-color: #f8fafc;
    color: #1e293b;
    font-family: 'Pretendard', 'Malgun Gothic', 'Segoe UI', sans-serif;
    font-size: 14px;
}

/* ===== Typography ===== */
QLabel#title {
    font-size: 26px;
    font-weight: bold;
    color: #3b82f6;
    margin-bottom: 5px;
}
QLabel#subtitle {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 15px;
}
QLabel#section_title {
    font-size: 15px;
    font-weight: bold;
    color: #1e293b;
    margin-top: 10px;
    margin-bottom: 8px;
    padding-left: 5px;
    border-left: 3px solid #3b82f6;
}
QLabel#field_label {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 3px;
}

/* ===== Cards (Container Panels) ===== */
QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px;
}
QFrame#card:hover {
    border: 1px solid #3b82f680;
}

/* ===== Input Fields ===== */
QComboBox, QDateEdit, QSpinBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px 14px;
    color: #1e293b;
    selection-background-color: #3b82f6;
    min-height: 22px;
}
QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QLineEdit:hover {
    border: 1px solid #3b82f6;
}
QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QLineEdit:focus {
    border: 2px solid #3b82f6;
    background-color: #ffffff;
}
QComboBox::drop-down {
    border: none;
    width: 30px;
    background: transparent;
}
QComboBox::down-arrow {
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid #3b82f6;
    margin-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    selection-background-color: #3b82f6;
    color: #1e293b;
    padding: 5px;
}

/* ===== Checkboxes ===== */
QCheckBox {
    spacing: 8px;
    color: #1e293b;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QCheckBox::indicator:hover {
    border: 2px solid #3b82f6;
}
QCheckBox::indicator:checked {
    background-color: #3b82f6;
    border: 2px solid #3b82f6;
}

/* ===== Radio Buttons ===== */
QRadioButton {
    spacing: 8px;
    color: #1e293b;
}
QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #cbd5e1;
    background-color: #ffffff;
}
QRadioButton::indicator:hover {
    border: 2px solid #3b82f6;
}
QRadioButton::indicator:checked {
    background-color: #3b82f6;
    border: 2px solid #3b82f6;
}

/* ===== Buttons ===== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #3b82f6, stop:1 #8b5cf6);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
    min-height: 20px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #2563eb, stop:1 #7c3aed);
    border: 2px solid #a78bfa;
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #1d4ed8, stop:1 #6d28d9);
}
QPushButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
}

/* Tool Buttons (Secondary) */
QPushButton#tool_btn {
    background-color: #e2e8f0;
    color: #1e293b;
    padding: 8px 14px;
    border-radius: 6px;
}
QPushButton#tool_btn:hover {
    background-color: #3b82f6;
    color: white;
}

/* ===== Table ===== */
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #3b82f640;
    selection-color: #1e293b;
    alternate-background-color: #f8fafc;
}
QTableWidget::item {
    padding: 8px 6px;
    border-bottom: 1px solid #f1f5f9;
}
QTableWidget::item:selected {
    background-color: #3b82f640;
}
QTableWidget::item:hover {
    background-color: #e0f2fe;
}
QHeaderView::section {
    background-color: #f1f5f9;
    color: #64748b;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid #3b82f6;
    font-weight: bold;
    font-size: 12px;
}

/* ===== Scrollbars ===== */
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 12px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #3b82f6;
    border-radius: 6px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #2563eb;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    border: none;
    background: #f1f5f9;
    height: 12px;
    border-radius: 6px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #3b82f6;
    border-radius: 6px;
    min-width: 30px;
}

/* ===== Tab Widget ===== */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    background: #ffffff;
    border-radius: 0 8px 8px 8px;
    padding: 5px;
}
QTabBar::tab {
    background: #f1f5f9;
    color: #64748b;
    padding: 10px 24px;
    margin-right: 2px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 500;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #3b82f6;
    border-bottom: 3px solid #3b82f6;
}
QTabBar::tab:hover:!selected {
    background: #e0f2fe;
    color: #1e293b;
}

/* ===== Log View ===== */
QTextEdit#log_view {
    background-color: #f8fafc;
    color: #475569;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    font-family: 'Consolas', 'JetBrains Mono', 'Courier New', monospace;
    font-size: 12px;
    padding: 10px;
    selection-background-color: #3b82f6;
}

/* ===== Progress Bar ===== */
QProgressBar {
    background: #f1f5f9;
    border-radius: 8px;
    text-align: center;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    height: 28px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #06b6d4);
    border-radius: 7px;
}

/* ===== Tooltips ===== */
QToolTip {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}

/* ===== List Widget ===== */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 5px;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background-color: #3b82f640;
    color: #3b82f6;
}
QListWidget::item:hover {
    background-color: #e0f2fe;
}

/* ===== Message Boxes ===== */
QMessageBox {
    background-color: #ffffff;
}
QMessageBox QLabel {
    color: #1e293b;
}

/* ===== Status Bar ===== */
QStatusBar {
    background-color: #f1f5f9;
    color: #64748b;
    border-top: 1px solid #e2e8f0;
    padding: 5px;
}
"""

# 기본 테마 (호환성)
MODERN_THEME = DARK_THEME

# --- Custom Widgets (Scroll Wheel Disabled) ---
# 마우스 휠로 값이 변경되는 것을 방지하는 커스텀 위젯들

class NoWheelSpinBox(QSpinBox):
    """스크롤 휠에 반응하지 않는 SpinBox"""
    def wheelEvent(self, event):
        event.ignore()  # 휠 이벤트 무시, 부모 스크롤에 전달

class NoWheelComboBox(QComboBox):
    """스크롤 휠에 반응하지 않는 ComboBox"""
    def wheelEvent(self, event):
        event.ignore()

class NoWheelDateEdit(QDateEdit):
    """스크롤 휠에 반응하지 않는 DateEdit"""
    def wheelEvent(self, event):
        event.ignore()

# --- Workers ---
class SearchWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    manual_mode_signal = pyqtSignal(object)  # active_searcher

    def __init__(self, origin, destination, date, return_date, adults):
        super().__init__()
        self.origin = origin
        self.destination = destination
        self.date = date
        self.return_date = return_date
        self.adults = adults
        self.searcher = FlightSearcher()

    def run(self):
        try:
            results = self.searcher.search(
                self.origin, self.destination, self.date, 
                self.return_date, self.adults,
                progress_callback=lambda msg: self.progress.emit(msg)
            )
            
            if not results and self.searcher.is_manual_mode():
                self.manual_mode_signal.emit(self.searcher)
            else:
                self.finished.emit(results)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class MultiSearchWorker(QThread):
    """다중 목적지 순차 검색 Worker"""
    progress = pyqtSignal(str)
    single_finished = pyqtSignal(str, list)  # dest, results
    all_finished = pyqtSignal(dict)  # {dest: [results]}
    error = pyqtSignal(str)
    
    def __init__(self, origin, destinations, date, return_date, adults):
        super().__init__()
        self.origin = origin
        self.destinations = destinations  # list of destination codes
        self.date = date
        self.return_date = return_date
        self.adults = adults
    
    def run(self):
        all_results = {}
        total = len(self.destinations)
        
        for i, dest in enumerate(self.destinations, 1):
            try:
                self.progress.emit(f"🔍 [{i}/{total}] {dest} 검색 중...")
                searcher = FlightSearcher()
                results = searcher.search(
                    self.origin, dest, self.date, self.return_date, self.adults,
                    progress_callback=lambda msg: self.progress.emit(f"[{dest}] {msg}")
                )
                all_results[dest] = results
                self.single_finished.emit(dest, results)
                searcher.close()
            except Exception as e:
                self.progress.emit(f"⚠️ {dest} 검색 실패: {e}")
                all_results[dest] = []
        
        self.all_finished.emit(all_results)


class DateRangeWorker(QThread):
    """날짜 범위 검색 Worker"""
    progress = pyqtSignal(str)
    date_result = pyqtSignal(str, int, str)  # date, min_price, airline
    all_finished = pyqtSignal(dict)  # {date: (price, airline)}
    error = pyqtSignal(str)
    
    def __init__(self, origin, dest, dates, return_offset, adults):
        super().__init__()
        self.origin = origin
        self.dest = dest
        self.dates = dates  # list of date strings
        self.return_offset = return_offset  # days after departure for return
        self.adults = adults
    
    def run(self):
        all_results = {}
        total = len(self.dates)
        
        # 최대 검색 횟수 제한 (무한 루프 방지)
        MAX_SEARCHES = 30
        if total > MAX_SEARCHES:
            self.progress.emit(f"⚠️ 최대 {MAX_SEARCHES}개 날짜만 검색합니다.")
            self.dates = self.dates[:MAX_SEARCHES]
            total = MAX_SEARCHES
        
        for i, date in enumerate(self.dates, 1):
            try:
                self.progress.emit(f"📅 [{i}/{total}] {date} 검색 중...")
                
                # Calculate return date
                from datetime import datetime, timedelta
                dep_dt = datetime.strptime(date, "%Y%m%d")
                ret_date = (dep_dt + timedelta(days=self.return_offset)).strftime("%Y%m%d") if self.return_offset else None
                
                searcher = FlightSearcher()
                
                try:
                    results = searcher.search(
                        self.origin, self.dest, date, ret_date, self.adults,
                        progress_callback=lambda msg: self.progress.emit(msg)
                    )
                    
                    # 수동 모드 전환 시 건너뛰기
                    if searcher.is_manual_mode():
                        self.progress.emit(f"⏭️ {date} - 수동 모드 전환됨, 건너뜁니다")
                        all_results[date] = (0, "수동모드")
                        searcher.close()
                        continue
                    
                    if results:
                        min_price = min(r.price for r in results)
                        min_airline = next(r.airline for r in results if r.price == min_price)
                        all_results[date] = (min_price, min_airline)
                        self.date_result.emit(date, min_price, min_airline)
                        self.progress.emit(f"✅ {date}: {min_price:,}원 ({min_airline})")
                    else:
                        all_results[date] = (0, "N/A")
                        self.progress.emit(f"⚠️ {date}: 결과 없음")
                finally:
                    # 항상 브라우저 닫기
                    try:
                        searcher.close()
                    except:
                        pass
                    
            except Exception as e:
                self.progress.emit(f"⚠️ {date} 검색 실패: {e}")
                all_results[date] = (0, "Error")
        
        self.progress.emit(f"🏁 검색 완료! 총 {len(all_results)}개 날짜 분석됨")
        self.all_finished.emit(all_results)



# --- Dialogs ---

class MultiDestDialog(QDialog):
    """다중 목적지 선택 다이얼로그"""
    search_requested = pyqtSignal(str, list, str, str, int)  # origin, dests, dep, ret, adults
    
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
        adult_layout.addStretch()
        layout.addLayout(adult_layout)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        btn_search = QPushButton("🔍 다중 검색 시작")
        btn_search.clicked.connect(self._on_search)
        btn_cancel = QPushButton("취소")
        btn_cancel.clicked.connect(self.reject)
        action_layout.addWidget(btn_search)
        action_layout.addWidget(btn_cancel)
        layout.addLayout(action_layout)
    
    def _toggle_all(self, checked):
        for cb in self.dest_checkboxes.values():
            cb.setChecked(checked)
    
    def _on_search(self):
        selected = [code for code, cb in self.dest_checkboxes.items() if cb.isChecked()]
        
        if len(selected) < 2:
            QMessageBox.warning(self, "선택 오류", "최소 2개 이상의 목적지를 선택하세요.")
            return
        
        origin = self.cb_origin.currentData()
        dep = self.date_dep.date().toString("yyyyMMdd")
        ret = self.date_ret.date().toString("yyyyMMdd")
        adults = self.spin_adults.value()
        
        self.search_requested.emit(origin, selected, dep, ret, adults)
        self.accept()


class DateRangeDialog(QDialog):
    """날짜 범위 검색 다이얼로그"""
    search_requested = pyqtSignal(str, str, list, int, int)  # origin, dest, dates, return_offset, adults
    
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
        adult_layout.addStretch()
        layout.addLayout(adult_layout)
        
        # Note
        note = QLabel("⚠️ 날짜 범위가 넓을수록 검색 시간이 오래 걸립니다.")
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
        
        if start >= end:
            QMessageBox.warning(self, "날짜 오류", "종료 날짜는 시작 날짜 이후여야 합니다.")
            return
        
        # Generate date list
        dates = []
        current = start
        while current <= end:
            dates.append(current.toString("yyyyMMdd"))
            current = current.addDays(1)
        
        if len(dates) > 14:
            reply = QMessageBox.question(
                self, "확인", 
                f"{len(dates)}일을 검색합니다. 시간이 오래 걸릴 수 있습니다.\n계속하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        origin = self.cb_origin.currentData()
        dest = self.cb_dest.currentData()
        duration = self.spin_duration.value()
        adults = self.spin_adults.value()
        
        self.search_requested.emit(origin, dest, dates, duration, adults)
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
        
        # Chart (if matplotlib available)
        if HAS_MATPLOTLIB and any(p > 0 for p, a in self.results.values()):
            layout.addWidget(self._create_chart())
        
        # Best date
        valid_results = [(d, p, a) for d, (p, a) in self.results.items() if p > 0]
        if valid_results:
            best = min(valid_results, key=lambda x: x[1])
            try:
                best_dt = datetime.strptime(best[0], "%Y%m%d")
                best_str = best_dt.strftime("%Y-%m-%d (%a)")
            except:
                best_str = best[0]
            rec_label = QLabel(f"💡 최저가 날짜: {best_str} - {best[1]:,}원 ({best[2]})")
            rec_label.setStyleSheet("font-size: 16px; color: #00ff00; font-weight: bold; padding: 10px;")
            layout.addWidget(rec_label)
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
    
    def _create_chart(self):
        """가격 추이 차트 생성"""
        fig = Figure(figsize=(8, 3), facecolor='#1a1a2e')
        canvas = FigureCanvas(fig)
        ax = fig.add_subplot(111)
        
        ax.set_facecolor('#16213e')
        
        sorted_data = sorted(self.results.items())
        dates = [d for d, (p, a) in sorted_data if p > 0]
        prices = [p for d, (p, a) in sorted_data if p > 0]
        
        if dates and prices:
            # Format x labels
            x_labels = []
            for d in dates:
                try:
                    dt = datetime.strptime(d, "%Y%m%d")
                    x_labels.append(dt.strftime("%m/%d"))
                except:
                    x_labels.append(d[-4:])
            
            ax.plot(range(len(prices)), prices, color='#4cc9f0', linewidth=2, marker='o')
            ax.fill_between(range(len(prices)), prices, alpha=0.3, color='#4cc9f0')
            
            ax.set_xticks(range(len(x_labels)))
            ax.set_xticklabels(x_labels, rotation=45, fontsize=8, color='white')
            ax.tick_params(colors='white')
            
            ax.set_ylabel('가격 (원)', color='white')
            ax.yaxis.label.set_color('white')
            
            for spine in ax.spines.values():
                spine.set_color('#30475e')
        
        fig.tight_layout()
        return canvas


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
            ("더블클릭", "결과 행에서 예약 페이지 열기"),
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


class SettingsDialog(QDialog):
    def __init__(self, parent=None, prefs=None):
        super().__init__(parent)
        self.prefs = prefs
        self.setWindowTitle("설정 (Settings)")
        self.setMinimumSize(500, 400)
        self.setStyleSheet(MODERN_THEME)
        self._init_ui()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        tabs = QTabWidget()
        tabs.addTab(self._create_general_tab(), "일반")
        tabs.addTab(self._create_dest_tab(), "목적지 관리")
        tabs.addTab(self._create_data_tab(), "데이터 관리")
        
        layout.addWidget(tabs)
        
        btn_close = QPushButton("닫기")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
        
    def _create_general_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Preferred Time
        grp_time = QGroupBox("기본 선호 시간대")
        gt_layout = QHBoxLayout(grp_time)
        
        self.spin_start = QSpinBox()
        self.spin_start.setRange(0, 23)
        self.spin_end = QSpinBox()
        self.spin_end.setRange(1, 24)
        
        pt = self.prefs.get_preferred_time()
        self.spin_start.setValue(pt.get("departure_start", 0))
        self.spin_end.setValue(pt.get("departure_end", 24))
        
        btn_save_time = QPushButton("저장")
        btn_save_time.setFixedSize(60, 30)
        btn_save_time.clicked.connect(self._save_time_pref)
        
        gt_layout.addWidget(QLabel("출발:"))
        gt_layout.addWidget(self.spin_start)
        gt_layout.addWidget(QLabel("~"))
        gt_layout.addWidget(self.spin_end)
        gt_layout.addWidget(QLabel("시"))
        gt_layout.addWidget(btn_save_time)
        
        layout.addWidget(grp_time)
        layout.addStretch()
        return widget

    def _save_time_pref(self):
        self.prefs.set_preferred_time(self.spin_start.value(), self.spin_end.value())
        QMessageBox.information(self, "저장", "시간 설정이 저장되었습니다.")

    def _create_dest_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("사용자 정의 프리셋 목록:"))
        self.list_presets = QListWidget()
        self._refresh_presets()
        layout.addWidget(self.list_presets)
        
        btn_del = QPushButton("선택 삭제")
        btn_del.clicked.connect(self._delete_preset)
        layout.addWidget(btn_del)
        
        return widget
        
    def _refresh_presets(self):
        self.list_presets.clear()
        presets = self.prefs.get_all_presets()
        for code, name in presets.items():
            if code not in config.AIRPORTS: # Only show custom ones
                self.list_presets.addItem(f"{code} - {name}")

    def _delete_preset(self):
        item = self.list_presets.currentItem()
        if item:
            code = item.text().split(' - ')[0]
            self.prefs.remove_preset(code)
            self._refresh_presets()

    def _create_data_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        grp_excel = QGroupBox("엑셀 (Excel)")
        gl = QVBoxLayout(grp_excel)
        
        btn_import = QPushButton("📂 검색 조건 가져오기 (Import)")
        btn_import.clicked.connect(self._import_excel)
        
        label_info = QLabel("엑셀 파일 양식: Origin, Dest, DepDate(YYYYMMDD), RetDate, Adults")
        label_info.setStyleSheet("font-size: 11px; color: #aaa;")
        
        btn_export = QPushButton("💾 검색 결과 내보내기 (Export)")
        btn_export.clicked.connect(self._export_excel)
        
        gl.addWidget(btn_import)
        gl.addWidget(btn_export)
        gl.addWidget(label_info)
        
        layout.addWidget(grp_excel)
        layout.addStretch()
        return widget

    def _import_excel(self):
        if not HAS_OPENPYXL:
            QMessageBox.critical(self, "오류", "openpyxl 라이브러리가 설치되지 않았습니다.\npip install openpyxl")
            return
            
        fname, _ = QFileDialog.getOpenFileName(self, "엑셀 파일 열기", "", "Excel Files (*.xlsx)")
        if not fname: return
        
        try:
            wb = openpyxl.load_workbook(fname)
            ws = wb.active
            # Assume Row 2: Origin, Dest, DepDate, RetDate, Adults
            origin = ws['A2'].value
            dest = ws['B2'].value
            dep = str(ws['C2'].value)
            ret = str(ws['D2'].value) if ws['D2'].value else None
            adults = ws['E2'].value
            
            if origin and dest:
                params = {
                    "origin": origin, "dest": dest, 
                    "dep": dep, "ret": ret, "adults": int(adults) if adults else 1
                }
                self.prefs.save_profile("엑셀 가져옴", params)
                QMessageBox.information(self, "완료", "'엑셀 가져옴' 프로필로 저장되었습니다.\n검색 패널에서 불러오세요.")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"엑셀 읽기 실패: {e}")

    def _export_excel(self):
        if not HAS_OPENPYXL:
            QMessageBox.critical(self, "오류", "openpyxl 라이브러리가 설치되지 않았습니다.\npip install openpyxl")
            return
            
        # Get results from MainWindow (parent)
        main_win = self.parent()
        if not main_win or not hasattr(main_win, 'all_results') or not main_win.all_results:
            QMessageBox.warning(self, "오류", "내보낼 검색 결과가 없습니다.")
            return

        fname, _ = QFileDialog.getSaveFileName(self, "엑셀로 저장", "flight_results.xlsx", "Excel Files (*.xlsx)")
        if not fname: return
        
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "검색결과"
            
            # Header
            headers = ["항공사", "가격", "출발", "도착", "경유", "복귀 출발", "복귀 도착", "복귀 경유", "출처"]
            ws.append(headers)
            
            for f in main_win.all_results:
                row = [
                    f.airline, f.price, 
                    f.departure_time, f.arrival_time, f.stops,
                    getattr(f, 'return_departure_time', '-'), 
                    getattr(f, 'return_arrival_time', '-'), 
                    getattr(f, 'return_stops', '-'),
                    f.source
                ]
                ws.append(row)
                
            wb.save(fname)
            QMessageBox.information(self, "완료", "엑셀 파일로 저장되었습니다.")
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"엑셀 저장 실패: {e}")

# --- Components ---

class SearchPanel(QFrame):
    search_requested = pyqtSignal(str, str, str, str, int)  # origin, dest, dep, ret, adults

    def __init__(self, prefs):
        super().__init__()
        self.prefs = prefs
        self.setObjectName("card")
        self._init_ui()

    def _init_ui(self):
        # Use GridLayout for better alignment
        layout = QGridLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Row 0: Header & Controls ---
        head_layout = QHBoxLayout()
        
        # Trip Type
        self.rb_round = QRadioButton("왕복")
        self.rb_oneway = QRadioButton("편도")
        self.rb_round.setChecked(True)
        self.rb_group = QButtonGroup()
        self.rb_group.addButton(self.rb_round)
        self.rb_group.addButton(self.rb_oneway)
        self.rb_group.buttonClicked.connect(self._toggle_return_date)
        
        head_layout.addWidget(QLabel("여정:"))
        head_layout.addWidget(self.rb_round)
        head_layout.addWidget(self.rb_oneway)
        
        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #30475e; margin: 0 10px;")
        head_layout.addWidget(sep)
        
        # Flight Type (Domestic/International)
        self.rb_domestic = QRadioButton("🇰🇷 국내선")
        self.rb_intl = QRadioButton("✈️ 국제선")
        self.rb_intl.setChecked(True)  # 기본값: 국제선
        self.flight_type_group = QButtonGroup()
        self.flight_type_group.addButton(self.rb_domestic)
        self.flight_type_group.addButton(self.rb_intl)
        self.flight_type_group.buttonClicked.connect(self._on_flight_type_changed)
        
        head_layout.addWidget(QLabel("노선:"))
        head_layout.addWidget(self.rb_domestic)
        head_layout.addWidget(self.rb_intl)
        
        head_layout.addStretch()

        
        # Profile Controls (Aligned Right)
        self.cb_profiles = NoWheelComboBox()
        self.cb_profiles.setPlaceholderText("프로필 선택")
        self.cb_profiles.setMinimumWidth(150)
        self.cb_profiles.currentIndexChanged.connect(self._load_selected_profile)
        self._refresh_profiles()
        
        btn_save_profile = QPushButton("💾 저장")
        btn_save_profile.setToolTip("현재 검색 조건 프로필로 저장")
        btn_save_profile.setObjectName("tool_btn")
        btn_save_profile.clicked.connect(self._save_current_profile)
        
        btn_settings = QPushButton("⚙️ 설정")
        btn_settings.setToolTip("설정 메뉴 열기")
        btn_settings.setObjectName("tool_btn")
        btn_settings.clicked.connect(self._open_settings)
        
        head_layout.addWidget(self.cb_profiles)
        head_layout.addWidget(btn_save_profile)
        head_layout.addWidget(btn_settings)
        
        layout.addLayout(head_layout, 0, 0, 1, 3)
        
        # --- Row 1: Origin & Destination ---
        # Origin
        self.cb_origin = self._create_airport_combo()
        layout.addWidget(self._labeled_widget("출발지 (Origin)", self.cb_origin), 1, 0)
        
        # Arrow
        arrow_lbl = QLabel("✈️")
        arrow_lbl.setStyleSheet("font-size: 18px; color: #4cc9f0;")
        arrow_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(arrow_lbl, 1, 1)
        
        # Destination
        self.cb_dest = self._create_airport_combo("NRT", include_presets=True)
        btn_preset = QPushButton("➕")
        btn_preset.setToolTip("현재 도착지를 프리셋에 추가/삭제")
        btn_preset.setObjectName("tool_btn")
        btn_preset.setFixedWidth(40)
        btn_preset.clicked.connect(self._manage_preset)
        
        dest_layout = QHBoxLayout()
        dest_layout.setContentsMargins(0,0,0,0)
        dest_layout.setSpacing(5)
        dest_layout.addWidget(self.cb_dest)
        dest_layout.addWidget(btn_preset)
        dest_container = QWidget()
        dest_container.setLayout(dest_layout)
        
        layout.addWidget(self._labeled_widget("도착지 (Destination)", dest_container), 1, 2)
        
        # --- Row 2: Dates ---
        self.date_dep = NoWheelDateEdit()
        self.date_dep.setCalendarPopup(True)
        self.date_dep.setDisplayFormat("yyyy-MM-dd")
        self.date_dep.setDate(QDate.currentDate().addDays(7))
        layout.addWidget(self._labeled_widget("가는 날 (Departure)", self.date_dep), 2, 0)
        
        self.date_ret = NoWheelDateEdit()
        self.date_ret.setCalendarPopup(True)
        self.date_ret.setDisplayFormat("yyyy-MM-dd")
        self.date_ret.setDate(QDate.currentDate().addDays(10))
        layout.addWidget(self._labeled_widget("오는 날 (Return)", self.date_ret), 2, 2)

        # --- Row 3: Passengers & Time ---
        # Passengers
        self.spin_adults = NoWheelSpinBox()
        self.spin_adults.setRange(1, 9)
        self.spin_adults.setSuffix("명")
        layout.addWidget(self._labeled_widget("성인 (Adults)", self.spin_adults), 3, 0)
        
        # Time Range
        time_layout = QHBoxLayout()
        self.spin_time_start = NoWheelSpinBox()
        self.spin_time_start.setRange(0, 23)
        self.spin_time_start.setSuffix("시")
        
        self.spin_time_end = NoWheelSpinBox()
        self.spin_time_end.setRange(1, 24)
        self.spin_time_end.setValue(24)
        self.spin_time_end.setSuffix("시")
        
        time_layout.addWidget(self.spin_time_start)
        time_layout.addWidget(QLabel("~"))
        time_layout.addWidget(self.spin_time_end)
        time_container = QWidget()
        time_container.setLayout(time_layout)
        
        layout.addWidget(self._labeled_widget("선호 출발 시간 (Departure Time)", time_container), 3, 2)

        # --- Row 4: Search Button ---
        self.btn_search = QPushButton("🔍 최저가 항공권 검색하기")
        self.btn_search.setFixedHeight(50)
        self.btn_search.setToolTip("Ctrl+Enter로도 검색할 수 있습니다")
        self.btn_search.setStyleSheet("""
            QPushButton { 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4361ee, stop:1 #4cc9f0);
                font-size: 16px; border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background: #3b82f6; }
        """)
        self.btn_search.clicked.connect(self._on_search)
        layout.addWidget(self.btn_search, 4, 0, 1, 3) 
        
        # Load previous preferred time if any
        pt = self.prefs.get_preferred_time()
        self.spin_time_start.setValue(pt.get("departure_start", 0))
        self.spin_time_end.setValue(pt.get("departure_end", 24))

        # Column stretch
        layout.setColumnStretch(0, 10)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 10)
        layout.setColumnMinimumWidth(1, 30)

    def _create_airport_combo(self, default_code="ICN", include_presets=False):
        cb = QComboBox()
        cb.setEditable(True) 
        
        # Standard Airports
        for code, name in config.AIRPORTS.items():
            cb.addItem(f"{code} ({name})", code)
            
        # Custom Presets
        if include_presets:
            try:
                presets = self.prefs.get_all_presets()
                cb.clear()
                for code, name in presets.items():
                     cb.addItem(f"{code} ({name})", code)
            except:
                pass

        index = cb.findData(default_code)
        if index >= 0:
            cb.setCurrentIndex(index)
        return cb

    def _labeled_widget(self, label_text, widget):
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        vbox.addWidget(lbl)
        vbox.addWidget(widget)
        return container

    def _manage_preset(self):
        current_text = self.cb_dest.currentText()
        from PyQt6.QtWidgets import QInputDialog, QMenu
        
        menu = QMenu(self)
        add_action = menu.addAction("현재 입력값을 프리셋에 추가")
        del_action = menu.addAction("선택된 프리셋 삭제")
        
        action = menu.exec(self.cb_dest.mapToGlobal(self.cb_dest.rect().bottomRight()))
        
        if action == add_action:
            code = self.cb_dest.currentData() or self.cb_dest.currentText().split(' ')[0]
            code, ok = QInputDialog.getText(self, "프리셋 추가", "도시/공항 코드 (예: DAD):", text=code)
            if ok and code:
                name, ok2 = QInputDialog.getText(self, "프리셋 추가", f"{code}의 도시명:")
                if ok2:
                    self.prefs.add_preset(code.upper(), name)
                    self._refresh_dest_combo()
                    
        elif action == del_action:
            code = self.cb_dest.currentData()
            if code in config.AIRPORTS:
                QMessageBox.warning(self, "삭제 불가", "기본 공항은 삭제할 수 없습니다.")
            else:
                self.prefs.remove_preset(code)
                self._refresh_dest_combo()

    def _refresh_dest_combo(self):
        current = self.cb_dest.currentData()
        self.cb_dest.clear()
        
        # 1. Standard Airports
        for code, name in config.AIRPORTS.items():
            self.cb_dest.addItem(f"{code} ({name})", code)
            
        # 2. Custom Presets (Only if not already added)
        presets = self.prefs.get_all_presets()
        for code, name in presets.items():
            if code not in config.AIRPORTS:
                self.cb_dest.addItem(f"{code} ({name})", code)

        idx = self.cb_dest.findData(current)
        if idx >= 0: self.cb_dest.setCurrentIndex(idx)

    def _toggle_return_date(self):
        is_round = self.rb_round.isChecked()
        self.date_ret.setEnabled(is_round)
        if not is_round:
            self.date_ret.setStyleSheet("color: #555; background-color: #222;")
        else:
            self.date_ret.setStyleSheet("")

    def _on_search(self):
        # Save time preference
        self.prefs.set_preferred_time(self.spin_time_start.value(), self.spin_time_end.value())
        
        origin_code = self.cb_origin.currentData() or self.cb_origin.currentText().split(' ')[0].strip()
        dest_code = self.cb_dest.currentData() or self.cb_dest.currentText().split(' ')[0].strip()
        
        dep_date = self.date_dep.date()
        ret_date = self.date_ret.date() if self.rb_round.isChecked() else None
        
        dep = dep_date.toString("yyyyMMdd")
        ret = ret_date.toString("yyyyMMdd") if ret_date else None
        adults = self.spin_adults.value()
        
        # 입력 유효성 검사
        if not origin_code or not dest_code:
            QMessageBox.warning(self, "입력 오류", "출발지와 도착지를 선택하세요.")
            return
        
        if origin_code == dest_code:
            QMessageBox.warning(self, "입력 오류", "출발지와 도착지가 같습니다.")
            return
        
        # 날짜 유효성 검사
        today = QDate.currentDate()
        if dep_date < today:
            QMessageBox.warning(self, "날짜 오류", "출발일이 오늘보다 이전입니다.")
            return
        
        if ret_date and ret_date < dep_date:
            QMessageBox.warning(self, "날짜 오류", "귀국일이 출발일보다 이전입니다.")
            return

        self.search_requested.emit(origin_code, dest_code, dep, ret, adults)


    def set_searching(self, searching):
        self.btn_search.setText("⏳ 검색 중..." if searching else "🔍 최저가 검색 시작")
        self.btn_search.setEnabled(not searching)
        self.cb_origin.setEnabled(not searching)
        self.cb_dest.setEnabled(not searching)
    
    def _on_flight_type_changed(self):
        """국내선/국제선 전환시 공항 목록 업데이트"""
        is_domestic = self.rb_domestic.isChecked()
        
        # 현재 선택 기억
        current_origin = self.cb_origin.currentData()
        current_dest = self.cb_dest.currentData()
        
        # 공항 목록 초기화
        self.cb_origin.clear()
        self.cb_dest.clear()
        
        if is_domestic:
            # 국내선: 한국 공항만
            domestic_airports = {
                "GMP": "김포",
                "CJU": "제주",
                "PUS": "부산 김해",
                "TAE": "대구",
                "ICN": "인천"
            }
            for code, name in domestic_airports.items():
                self.cb_origin.addItem(f"{code} ({name})", code)
                self.cb_dest.addItem(f"{code} ({name})", code)
            
            # 기본값 설정 (김포-제주)
            self.cb_origin.setCurrentIndex(self.cb_origin.findData("GMP"))
            self.cb_dest.setCurrentIndex(self.cb_dest.findData("CJU"))
        else:
            # 국제선: 전체 공항
            for code, name in config.AIRPORTS.items():
                self.cb_origin.addItem(f"{code} ({name})", code)
                self.cb_dest.addItem(f"{code} ({name})", code)
            
            # 커스텀 프리셋도 도착지에 추가
            try:
                presets = self.prefs.get_all_presets()
                for code, name in presets.items():
                    if code not in config.AIRPORTS:
                        self.cb_dest.addItem(f"{code} ({name})", code)
            except:
                pass
            
            # 기본값 설정 (인천-도쿄 나리타)
            self.cb_origin.setCurrentIndex(self.cb_origin.findData("ICN"))
            self.cb_dest.setCurrentIndex(self.cb_dest.findData("NRT"))
        
        # 이전 선택 복원 시도
        if current_origin:
            idx = self.cb_origin.findData(current_origin)
            if idx >= 0:
                self.cb_origin.setCurrentIndex(idx)
        if current_dest:
            idx = self.cb_dest.findData(current_dest)
            if idx >= 0:
                self.cb_dest.setCurrentIndex(idx)

        
    def _refresh_profiles(self):
        self.cb_profiles.blockSignals(True)
        self.cb_profiles.clear()
        self.cb_profiles.addItem("- 프로필 선택 -", None)
        profiles = self.prefs.get_all_profiles()
        for name in profiles.keys():
            self.cb_profiles.addItem(name, name)
        self.cb_profiles.blockSignals(False)

    def _save_current_profile(self):
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "프로필 저장", "프로필 이름 (예: 제주 가족여행):")
        if ok and name:
            params = {
                "origin": self.cb_origin.currentData() or self.cb_origin.currentText(),
                "dest": self.cb_dest.currentData() or self.cb_dest.currentText(),
                "dep": self.date_dep.date().toString("yyyyMMdd"),
                "ret": self.date_ret.date().toString("yyyyMMdd") if self.rb_round.isChecked() else None,
                "adults": self.spin_adults.value()
            }
            self.prefs.save_profile(name, params)
            self._refresh_profiles()
            QMessageBox.information(self, "저장 완료", f"'{name}' 프로필이 저장되었습니다.")

    def _load_selected_profile(self):
        name = self.cb_profiles.currentData()
        if not name: return
        
        data = self.prefs.get_profile(name)
        if not data: return
        
        # Same logic as history restore
        try:
            # Origin
            idx_o = self.cb_origin.findData(data['origin'])
            if idx_o >= 0: self.cb_origin.setCurrentIndex(idx_o)
            
            # Dest
            idx_d = self.cb_dest.findData(data['dest'])
            if idx_d >= 0: self.cb_dest.setCurrentIndex(idx_d)
            
            # Date
            qt_date = QDate.fromString(data['dep'], "yyyyMMdd")
            self.date_dep.setDate(qt_date)
            
            if data['ret']:
                self.rb_round.setChecked(True)
                self.date_ret.setEnabled(True)
                self.date_ret.setDate(QDate.fromString(data['ret'], "yyyyMMdd"))
            else:
                self.rb_oneway.setChecked(True)
                self._toggle_return_date()
                
            self.spin_adults.setValue(data['adults'])
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"프로필 로드 중 오류: {e}")

    def _open_settings(self):
        dlg = SettingsDialog(self, self.prefs)
        dlg.exec()
        # Refresh UI after settings close (presets might have changed)
        self._refresh_dest_combo()
        self._refresh_profiles()
    
    def save_settings(self):
        """입력값을 QSettings에 저장 (프로그램 종료 시 호출)"""
        settings = QSettings("FlightBot", "FlightComparisonBot")
        settings.setValue("origin", self.cb_origin.currentText())
        settings.setValue("dest", self.cb_dest.currentText())
        settings.setValue("dep_date", self.date_dep.date().toString("yyyyMMdd"))
        if hasattr(self, 'date_ret') and self.date_ret.isEnabled():
            settings.setValue("ret_date", self.date_ret.date().toString("yyyyMMdd"))
        settings.setValue("adults", self.spin_adults.value())
        settings.setValue("is_roundtrip", self.rb_round.isChecked())
        if hasattr(self, 'rb_domestic'):
            settings.setValue("is_domestic", self.rb_domestic.isChecked())
    
    def restore_settings(self):
        """저장된 입력값 복원 (프로그램 시작 시 호출)"""
        settings = QSettings("FlightBot", "FlightComparisonBot")
        
        # Origin
        origin = settings.value("origin", "")
        if origin:
            idx = self.cb_origin.findText(origin, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self.cb_origin.setCurrentIndex(idx)
        
        # Destination
        dest = settings.value("dest", "")
        if dest:
            idx = self.cb_dest.findText(dest, Qt.MatchFlag.MatchContains)
            if idx >= 0:
                self.cb_dest.setCurrentIndex(idx)
        
        # Dates
        dep_date = settings.value("dep_date", "")
        if dep_date:
            qdate = QDate.fromString(dep_date, "yyyyMMdd")
            if qdate.isValid() and qdate >= QDate.currentDate():
                self.date_dep.setDate(qdate)
        
        ret_date = settings.value("ret_date", "")
        if ret_date and hasattr(self, 'date_ret'):
            qdate = QDate.fromString(ret_date, "yyyyMMdd")
            if qdate.isValid() and qdate >= QDate.currentDate():
                self.date_ret.setDate(qdate)
        
        # Adults
        adults = settings.value("adults", 1, type=int)
        self.spin_adults.setValue(adults)
        
        # Trip type
        is_roundtrip = settings.value("is_roundtrip", True, type=bool)
        self.rb_round.setChecked(is_roundtrip)
        self.rb_oneway.setChecked(not is_roundtrip)
        
        # Domestic/International
        is_domestic = settings.value("is_domestic", False, type=bool)
        if hasattr(self, 'rb_domestic') and hasattr(self, 'rb_intl'):
            self.rb_domestic.setChecked(is_domestic)
            self.rb_intl.setChecked(not is_domestic)
            self._on_flight_type_changed()


class FilterPanel(QFrame):
    filter_changed = pyqtSignal(dict)  # {direct_only, include_layover, airline_category, max_stops}

    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        
        layout.addWidget(QLabel("필터:"))
        
        # Direct flights only
        self.chk_direct = QCheckBox("직항만")
        self.chk_direct.setToolTip("경유 없이 직항 노선만 표시합니다")
        self.chk_direct.stateChanged.connect(self._emit_filter)
        layout.addWidget(self.chk_direct)
        
        # Include layovers
        self.chk_layover = QCheckBox("경유 포함")
        self.chk_layover.setToolTip("경유 노선도 함께 표시합니다")
        self.chk_layover.setChecked(True)
        self.chk_layover.stateChanged.connect(self._emit_filter)
        layout.addWidget(self.chk_layover)
        
        layout.addWidget(self._create_separator())
        
        # Airline Category Filter
        layout.addWidget(QLabel("항공사:"))
        self.cb_airline_category = NoWheelComboBox()
        self.cb_airline_category.setToolTip("LCC: 저비용항공사 (제주항공, 진에어 등)\nFSC: 일반항공사 (대한항공, 아시아나)")
        self.cb_airline_category.addItem("전체", "ALL")
        self.cb_airline_category.addItem("🏷️ LCC (저비용)", "LCC")
        self.cb_airline_category.addItem("✈️ FSC (일반)", "FSC")
        self.cb_airline_category.setMinimumWidth(130)
        self.cb_airline_category.currentIndexChanged.connect(self._emit_filter)
        layout.addWidget(self.cb_airline_category)
        
        layout.addWidget(self._create_separator())
        
        # Styles for better visibility
        label_style = "font-weight: bold; color: #e0e0e0; font-size: 13px;"
        spin_style = """
            QSpinBox {
                min-width: 70px;
                min-height: 28px;
                font-size: 13px;
                padding: 2px;
                font-weight: bold;
            }
        """
        self.setStyleSheet(spin_style)

        # Time Filter (Outbound)
        lbl_out = QLabel("가는편:")
        lbl_out.setStyleSheet(label_style)
        layout.addWidget(lbl_out)
        
        self.spin_start_time = NoWheelSpinBox()
        self.spin_start_time.setRange(0, 23)
        self.spin_start_time.setSuffix("시")
        self.spin_start_time.valueChanged.connect(self._on_time_changed)
        
        layout.addWidget(self.spin_start_time)
        layout.addWidget(QLabel("~"))
        
        self.spin_end_time = NoWheelSpinBox()
        self.spin_end_time.setRange(1, 24)
        self.spin_end_time.setValue(24)
        self.spin_end_time.setSuffix("시")
        self.spin_end_time.valueChanged.connect(self._on_time_changed)
        layout.addWidget(self.spin_end_time)
        
        layout.addWidget(self._create_separator())
        
        # Time Filter (Inbound)
        lbl_in = QLabel("오는편:")
        lbl_in.setStyleSheet(label_style)
        layout.addWidget(lbl_in)
        
        self.spin_ret_start = NoWheelSpinBox()
        self.spin_ret_start.setRange(0, 23)
        self.spin_ret_start.setSuffix("시")
        self.spin_ret_start.valueChanged.connect(self._on_time_changed)
        layout.addWidget(self.spin_ret_start)
        
        layout.addWidget(QLabel("~"))
        
        self.spin_ret_end = NoWheelSpinBox()
        self.spin_ret_end.setRange(1, 24)
        self.spin_ret_end.setValue(24)
        self.spin_ret_end.setSuffix("시")
        self.spin_ret_end.valueChanged.connect(self._on_time_changed)
        layout.addWidget(self.spin_ret_end)
        
        layout.addWidget(self._create_separator())
        
        # Max Stops Filter
        layout.addWidget(QLabel("경유:"))
        self.spin_max_stops = NoWheelSpinBox()
        self.spin_max_stops.setRange(0, 5)
        self.spin_max_stops.setValue(3)
        self.spin_max_stops.setSuffix("회")
        self.spin_max_stops.setFixedWidth(50)
        self.spin_max_stops.setToolTip("허용할 최대 경유 횟수")
        self.spin_max_stops.valueChanged.connect(self._emit_filter)
        layout.addWidget(self.spin_max_stops)
        
        layout.addStretch()
        
        # Reset Button
        btn_reset = QPushButton("↺")
        btn_reset.setToolTip("필터 초기화")
        btn_reset.setObjectName("tool_btn")
        btn_reset.setFixedWidth(30)
        btn_reset.clicked.connect(self._reset_filters)
        layout.addWidget(btn_reset)
    
    def _create_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: #30475e;")
        return sep
    
    def _on_time_changed(self):
        """시간 변경 시 유효성 검사 후 시그널 발생"""
        # 가는편
        start = self.spin_start_time.value()
        end = self.spin_end_time.value()
        if start >= end:
            if self.sender() == self.spin_start_time:
                self.spin_end_time.setValue(start + 1)
            else:
                self.spin_start_time.setValue(end - 1)
        
        # 오는편
        r_start = self.spin_ret_start.value()
        r_end = self.spin_ret_end.value()
        if r_start >= r_end:
            if self.sender() == self.spin_ret_start:
                self.spin_ret_end.setValue(r_start + 1)
            else:
                self.spin_ret_start.setValue(r_end - 1)
                
        self._emit_filter()

    def _emit_filter(self):
        filters = self.get_current_filters()
        self.filter_changed.emit(filters)

    def _reset_filters(self):
        self.chk_direct.setChecked(False)
        self.chk_layover.setChecked(True)
        self.cb_airline_category.setCurrentIndex(0)  # ALL
        self.spin_max_stops.setValue(3)
        self.spin_start_time.setValue(0)
        self.spin_end_time.setValue(24)
        self.spin_ret_start.setValue(0)
        self.spin_ret_end.setValue(24)

    def get_current_filters(self):
        return {
            "direct_only": self.chk_direct.isChecked(),
            "include_layover": self.chk_layover.isChecked(),
            "airline_category": self.cb_airline_category.currentData(),
            "max_stops": self.spin_max_stops.value(),
            "start_time": self.spin_start_time.value(),
            "end_time": self.spin_end_time.value(),
            "ret_start_time": self.spin_ret_start.value(),
            "ret_end_time": self.spin_ret_end.value()
        }


class ResultTable(QTableWidget):
    favorite_requested = pyqtSignal(int)  # row index
    
    def __init__(self):
        super().__init__()
        self.results_data = []  # Store flight results for access
        
        self.setColumnCount(9)
        self.setHorizontalHeaderLabels([
            "항공사", "가격", "가는편 출발", "가는편 도착", "경유",
            "오는편 출발", "오는편 도착", "경유", "출처"
        ])
        # 열 너비 조절 가능하도록 Interactive 모드 + 기본 너비 설정
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.horizontalHeader().setStretchLastSection(True)
        # 기본 열 너비 설정
        self.setColumnWidth(0, 100)  # 항공사
        self.setColumnWidth(1, 180)  # 가격 (분리 표시용 넓게)
        self.setColumnWidth(2, 80)   # 가는편 출발
        self.setColumnWidth(3, 80)   # 가는편 도착
        self.setColumnWidth(4, 70)   # 경유
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        
        # Enable context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def update_data(self, results):
        # 대량 업데이트 최적화
        self.setUpdatesEnabled(False)
        self.setSortingEnabled(False)
        self.results_data = results
        self.setRowCount(len(results))
        
        # Calculate price range for color coding
        if results:
            min_price = min(r.price for r in results)
            max_price = max(r.price for r in results)
            price_range = max_price - min_price if max_price > min_price else 1
        
        for i, flight in enumerate(results):
            # Store flight object in first column's data
            airline_item = QTableWidgetItem(flight.airline)
            airline_item.setData(Qt.ItemDataRole.UserRole + 1, i)
            self.setItem(i, 0, airline_item)
            
            # Price (Color-coded: green=cheap, red=expensive)
            # 국내선: 가는편/오는편 가격 분리 표시
            if hasattr(flight, 'outbound_price') and flight.outbound_price > 0:
                price_text = f"{flight.price:,}원 ({flight.outbound_price:,}+{flight.return_price:,})"
            else:
                price_text = f"{flight.price:,}원"
            
            price_item = QTableWidgetItem(price_text)
            price_item.setData(Qt.ItemDataRole.UserRole, flight.price)
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # Color coding based on price position
            ratio = (flight.price - min_price) / price_range if price_range else 0
            if ratio < 0.2:
                price_color = "#22c55e"  # Green - cheapest
            elif ratio < 0.5:
                price_color = "#4cc9f0"  # Cyan - good
            elif ratio < 0.8:
                price_color = "#f59e0b"  # Orange - moderate
            else:
                price_color = "#ef4444"  # Red - expensive
            
            price_item.setForeground(QColor(price_color))
            price_item.setFont(QFont("Pretendard", 11, QFont.Weight.Bold))
            self.setItem(i, 1, price_item)
            
            # Outbound
            self._set_time_item(i, 2, flight.departure_time)
            self._set_time_item(i, 3, flight.arrival_time)
            
            # Stops - highlight direct flights
            stops_item = QTableWidgetItem("✈️ 직항" if not flight.stops else f"{flight.stops}회 경유")
            if not flight.stops:
                stops_item.setForeground(QColor("#22c55e"))
            else:
                stops_item.setForeground(QColor("#94a3b8"))
            self.setItem(i, 4, stops_item)
            
            # Inbound
            if hasattr(flight, 'is_round_trip') and flight.is_round_trip:
                self._set_time_item(i, 5, flight.return_departure_time)
                self._set_time_item(i, 6, flight.return_arrival_time)
                ret_stops = QTableWidgetItem("✈️ 직항" if not flight.return_stops else f"{flight.return_stops}회 경유")
                if not flight.return_stops:
                    ret_stops.setForeground(QColor("#22c55e"))
                self.setItem(i, 7, ret_stops)
            else:
                self.setItem(i, 5, QTableWidgetItem("-"))
                self.setItem(i, 6, QTableWidgetItem("-"))
                self.setItem(i, 7, QTableWidgetItem("-"))
                
            # Source
            self.setItem(i, 8, QTableWidgetItem(flight.source))
            
            # Set row height
            self.setRowHeight(i, 45)
            
            # 최저가 행 배경색 강조
            if flight.price == min_price:
                highlight_color = QColor("#22c55e20")  # 녹색 반투명
                for col in range(self.columnCount()):
                    item = self.item(i, col)
                    if item:
                        item.setBackground(highlight_color)
            
        self.setSortingEnabled(True)
        self.setUpdatesEnabled(True)  # 렌더링 다시 활성화


    def _set_time_item(self, row, col, text):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setItem(row, col, item)
    
    def _show_context_menu(self, pos):
        row = self.rowAt(pos.y())
        if row < 0:
            return
        
        menu = QMenu(self)
        
        # Add to favorites
        action_fav = menu.addAction("⭐ 즐겨찾기 추가")
        action_fav.triggered.connect(lambda: self.favorite_requested.emit(row))
        
        menu.addSeparator()
        
        # Copy info
        action_copy = menu.addAction("📋 정보 복사")
        action_copy.triggered.connect(lambda: self._copy_row_info(row))
        
        menu.addSeparator()
        
        # Export options (전체 결과)
        action_excel = menu.addAction("📊 Excel로 내보내기")
        action_excel.triggered.connect(self.export_to_excel)
        
        action_csv = menu.addAction("📥 CSV로 내보내기")
        action_csv.triggered.connect(self.export_to_csv)
        
        menu.exec(self.mapToGlobal(pos))
    
    def _copy_row_info(self, row):
        if row >= len(self.results_data):
            return
        flight = self.results_data[row]
        info = f"{flight.airline} | {flight.price:,}원 | {flight.departure_time}→{flight.arrival_time}"
        QApplication.clipboard().setText(info)
    
    def export_to_excel(self):
        """검색 결과를 Excel 파일로 내보내기"""
        if not self.results_data:
            QMessageBox.warning(self, "경고", "내보낼 데이터가 없습니다.")
            return
        
        if not HAS_OPENPYXL:
            QMessageBox.warning(self, "경고", "openpyxl이 설치되지 않았습니다.\npip install openpyxl")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Excel로 저장", 
            f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel Files (*.xlsx)"
        )
        
        if not filename:
            return
        
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "검색 결과"
            
            # 헤더
            headers = ["항공사", "가격", "가는편 출발", "가는편 도착", "경유",
                       "오는편 출발", "오는편 도착", "경유", "출처", "가는편 가격", "오는편 가격"]
            ws.append(headers)
            
            # 데이터
            for flight in self.results_data:
                row = [
                    flight.airline,
                    flight.price,
                    flight.departure_time,
                    flight.arrival_time,
                    flight.stops,
                    getattr(flight, 'return_departure_time', ''),
                    getattr(flight, 'return_arrival_time', ''),
                    getattr(flight, 'return_stops', 0),
                    flight.source,
                    getattr(flight, 'outbound_price', 0),
                    getattr(flight, 'return_price', 0)
                ]
                ws.append(row)
            
            # 열 너비 자동 조절
            for col in ws.columns:
                max_length = max(len(str(cell.value or '')) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = max_length + 2
            
            wb.save(filename)
            QMessageBox.information(self, "완료", f"Excel 파일이 저장되었습니다:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")
    
    def export_to_csv(self):
        """검색 결과를 CSV 파일로 내보내기"""
        if not self.results_data:
            QMessageBox.warning(self, "경고", "내보낼 데이터가 없습니다.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장",
            f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        try:
            import csv
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                writer.writerow(["항공사", "가격", "가는편출발", "가는편도착", "경유",
                                "오는편출발", "오는편도착", "경유", "출처"])
                for flight in self.results_data:
                    writer.writerow([
                        flight.airline, flight.price,
                        flight.departure_time, flight.arrival_time, flight.stops,
                        getattr(flight, 'return_departure_time', ''),
                        getattr(flight, 'return_arrival_time', ''),
                        getattr(flight, 'return_stops', 0),
                        flight.source
                    ])
            QMessageBox.information(self, "완료", f"CSV 파일이 저장되었습니다:\n{filename}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")
    
    def get_flight_at_row(self, row):
        """Get flight data for the given visual row"""
        if 0 <= row < len(self.results_data):
            # Account for sorting - get original index from item data
            item = self.item(row, 0)
            if item:
                orig_idx = item.data(Qt.ItemDataRole.UserRole + 1)
                if orig_idx is not None and 0 <= orig_idx < len(self.results_data):
                    return self.results_data[orig_idx]
        return None


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


# --- Main Window ---

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("✈️ Flight Bot v2.4 - Pro")
        self.setMinimumSize(1280, 900)
        
        # 테마 초기화
        self.is_dark_theme = True
        # 설정에서 테마 로드 (나중에 구현 가능, 현재는 기본 다크)
        self.setStyleSheet(DARK_THEME)
        
        self.worker = None
        self.multi_worker = None
        self.date_worker = None
        self.active_searcher = None
        self.results = []
        self.all_results = []
        self.current_search_params = {}
        
        self.prefs = config.PreferenceManager()
        self.db = FlightDatabase()
        
        self._init_ui()
        if hasattr(self, 'search_panel'):
            self.search_panel.restore_settings()
        self._setup_shortcuts()

    def _init_ui(self):
        # 전체 UI 스크롤 가능하도록 설정
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; background: #1a1a2e; }")
        
        # 스크롤 내부 컨테이너
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 1. Header
        header = QWidget()
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(0, 0, 0, 10)
        
        v_title = QVBoxLayout()
        title = QLabel("✈️ 항공권 최저가 검색기")
        title.setObjectName("title")
        subtitle = QLabel("Playwright 엔진 기반 실시간 항공권 비교 분석 v2.3")
        subtitle.setObjectName("subtitle")
        v_title.addWidget(title)
        v_title.addWidget(subtitle)
        
        h_layout.addLayout(v_title)
        h_layout.addStretch()
        
        # Advanced Search Buttons
        btn_multi = QPushButton("🌍 다중 목적지")
        btn_multi.setToolTip("여러 목적지를 한 번에 비교 검색")
        btn_multi.clicked.connect(self._open_multi_dest_search)
        h_layout.addWidget(btn_multi)
        
        btn_date = QPushButton("📅 날짜 범위")
        btn_date.setToolTip("날짜 범위에서 최저가 찾기")
        btn_date.clicked.connect(self._open_date_range_search)
        h_layout.addWidget(btn_date)
        
        btn_shortcuts = QPushButton("⌨️ 단축키")
        btn_shortcuts.setToolTip("키보드 단축키 보기")
        btn_shortcuts.clicked.connect(self._show_shortcuts)
        h_layout.addWidget(btn_shortcuts)
        
        # 테마 전환 버튼
        self.btn_theme = QPushButton("🌙 다크")
        self.btn_theme.setToolTip("라이트/다크 테마 전환")
        self.btn_theme.clicked.connect(self._toggle_theme)
        h_layout.addWidget(self.btn_theme)
        
        btn_main_settings = QPushButton("⚙️ 설정")
        btn_main_settings.setFixedSize(80, 40)
        btn_main_settings.clicked.connect(self._open_main_settings)
        h_layout.addWidget(btn_main_settings)
        
        main_layout.addWidget(header)
        
        # 2. Search Panel (접기/펼치기)
        toggle_container = QWidget()
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        
        self.btn_toggle_search = QPushButton("▼ 검색 설정")
        self.btn_toggle_search.setStyleSheet("""
            QPushButton { 
                background: transparent; 
                color: #4cc9f0; 
                font-weight: bold; 
                text-align: left; 
                padding: 5px;
                border: none;
            }
            QPushButton:hover { color: #7dd3fc; }
        """)
        self.btn_toggle_search.setCheckable(True)
        self.btn_toggle_search.setChecked(True)
        self.btn_toggle_search.clicked.connect(self._toggle_search_panel)
        toggle_layout.addWidget(self.btn_toggle_search)
        toggle_layout.addStretch()
        main_layout.addWidget(toggle_container)
        
        self.search_panel = SearchPanel(self.prefs)
        self.search_panel.search_requested.connect(self._start_search)
        main_layout.addWidget(self.search_panel)
        
        # 3. Filter & Progress
        main_layout.addWidget(QLabel("필터 및 상태", objectName="section_title"))
        filter_container = QWidget()
        f_layout = QHBoxLayout(filter_container)
        f_layout.setContentsMargins(0, 5, 0, 5)
        
        self.filter_panel = FilterPanel()
        self.filter_panel.filter_changed.connect(self._apply_filter)
        f_layout.addWidget(self.filter_panel, 2)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("준비됨")
        self.progress_bar.setMinimumHeight(30)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background: #16213e; border-radius: 6px; text-align: center; color: white; border: 1px solid #30475e; }
            QProgressBar::chunk { background: #4cc9f0; border-radius: 6px; }
        """)
        f_layout.addWidget(self.progress_bar, 3)
        main_layout.addWidget(filter_container)
        
        # 4. Content Area (Tabs) with Export Buttons
        result_header = QWidget()
        rh_layout = QHBoxLayout(result_header)
        rh_layout.setContentsMargins(0, 0, 0, 0)
        rh_layout.addWidget(QLabel("검색 결과", objectName="section_title"))
        rh_layout.addStretch()
        
        # Export buttons
        btn_export_csv = QPushButton("📥 CSV 저장")
        btn_export_csv.setObjectName("tool_btn")
        btn_export_csv.setToolTip("검색 결과를 CSV 파일로 저장")
        btn_export_csv.clicked.connect(self._export_to_csv)
        rh_layout.addWidget(btn_export_csv)
        
        btn_copy = QPushButton("📋 복사")
        btn_copy.setObjectName("tool_btn")
        btn_copy.setToolTip("검색 결과를 클립보드에 복사")
        btn_copy.clicked.connect(self._copy_results_to_clipboard)
        rh_layout.addWidget(btn_copy)
        
        main_layout.addWidget(result_header)

        self.tabs = QTabWidget()
        self.tabs.setMinimumHeight(400)
        
        # Tab 1: Results
        self.table = ResultTable()
        self.table.favorite_requested.connect(self._add_to_favorites)
        self.table.cellDoubleClicked.connect(self._on_table_double_click)
        self.tabs.addTab(self.table, "🔍 검색 결과")
        
        # Tab 2: Favorites
        self.favorites_tab = self._create_favorites_tab()
        self.tabs.addTab(self.favorites_tab, "⭐ 즐겨찾기")
        
        # Tab 3: Logs
        self.log_viewer = LogViewer()
        self.tabs.addTab(self.log_viewer, "📋 로그")
        
        # Tab 4: History
        self.history_list = self.create_history_tab()
        self.tabs.addTab(self.history_list, "📜 검색 기록")
        
        main_layout.addWidget(self.tabs, 1)
        
        # 5. Manual Mode Actions
        self.manual_frame = QFrame()
        self.manual_frame.setObjectName("card")
        self.manual_frame.setVisible(False)
        m_layout = QHBoxLayout(self.manual_frame)
        m_layout.addWidget(QLabel("🖐️ <b>수동 모드 활성화됨</b> - 브라우저에서 결과를 확인하세요"))
        
        btn_extract = QPushButton("데이터 추출하기")
        btn_extract.setObjectName("manual_btn")
        btn_extract.clicked.connect(self._manual_extract)
        m_layout.addStretch()
        m_layout.addWidget(btn_extract)
        
        main_layout.addWidget(self.manual_frame)
        
        # 스크롤 영역에 컨테이너 설정
        scroll.setWidget(container)
        self.setCentralWidget(scroll)
        
        # Status Bar
        self.statusBar().showMessage("준비 완료 | Ctrl+Enter: 검색, F5: 새로고침, Esc: 취소")

    def _toggle_search_panel(self):
        """검색 패널 접기/펼치기 토글"""
        is_visible = self.search_panel.isVisible()
        self.search_panel.setVisible(not is_visible)
        self.btn_toggle_search.setText("▶ 검색 설정" if is_visible else "▼ 검색 설정")

    def _setup_shortcuts(self):
        """키보드 단축키 설정"""
        # Ctrl+Enter: Start search
        shortcut_search = QShortcut(QKeySequence("Ctrl+Return"), self)
        shortcut_search.activated.connect(self.search_panel._on_search)
        
        # F5: Refresh (reapply filter)
        shortcut_refresh = QShortcut(QKeySequence("F5"), self)
        shortcut_refresh.activated.connect(self._apply_filter)
        
        # Escape: Cancel / Close dialogs
        shortcut_esc = QShortcut(QKeySequence("Escape"), self)
        shortcut_esc.activated.connect(self._on_escape)
        
        # Ctrl+F: Focus on filter
        shortcut_filter = QShortcut(QKeySequence("Ctrl+F"), self)
        shortcut_filter.activated.connect(lambda: self.filter_panel.cb_airline_category.setFocus())

    def _on_escape(self):
        """Escape 키 처리"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "검색 취소", "현재 검색을 취소하시겠습니까?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.terminate()
                self.search_panel.set_searching(False)
                self.log_viewer.append_log("사용자가 검색을 취소했습니다.")

    def _on_table_double_click(self, row, col):
        """테이블 더블클릭 - 예약 페이지 열기"""
        flight = self.table.get_flight_at_row(row)
        if flight:
            # Construct Interpark search URL
            origin = self.current_search_params.get('origin', 'ICN')
            dest = self.current_search_params.get('dest', 'NRT')
            dep = self.current_search_params.get('dep', '')
            ret = self.current_search_params.get('ret', '')
            
            origin_city = config.CITY_CODES_MAP.get(origin, origin)
            dest_city = config.CITY_CODES_MAP.get(dest, dest)
            
            if ret:
                url = f"https://travel.interpark.com/air/search/c:{origin_city}-c:{dest_city}-{dep}/c:{dest_city}-c:{origin_city}-{ret}"
            else:
                url = f"https://travel.interpark.com/air/search/c:{origin_city}-c:{dest_city}-{dep}"
            
            webbrowser.open(url)
            self.log_viewer.append_log(f"브라우저에서 예약 페이지 열기: {flight.airline}")

    # --- Favorites Tab ---
    def _create_favorites_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("저장된 즐겨찾기 목록"))
        toolbar.addStretch()
        
        btn_refresh = QPushButton("🔄 새로고침")
        btn_refresh.clicked.connect(self._refresh_favorites)
        toolbar.addWidget(btn_refresh)
        
        btn_delete = QPushButton("🗑️ 선택 삭제")
        btn_delete.clicked.connect(self._delete_selected_favorite)
        toolbar.addWidget(btn_delete)
        
        layout.addLayout(toolbar)
        
        # Table
        self.fav_table = QTableWidget()
        self.fav_table.setColumnCount(7)
        self.fav_table.setHorizontalHeaderLabels([
            "ID", "항공사", "가격", "출발지", "도착지", "출발일", "메모"
        ])
        self.fav_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fav_table.setColumnHidden(0, True)  # Hide ID column
        self.fav_table.setAlternatingRowColors(True)
        self.fav_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self.fav_table)
        
        # Stats
        self.fav_stats_label = QLabel("")
        self.fav_stats_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.fav_stats_label)
        
        self._refresh_favorites()
        return widget
    
    def _refresh_favorites(self):
        favorites = self.db.get_favorites()
        self.fav_table.setRowCount(len(favorites))
        
        for i, fav in enumerate(favorites):
            self.fav_table.setItem(i, 0, QTableWidgetItem(str(fav.id)))
            self.fav_table.setItem(i, 1, QTableWidgetItem(fav.airline))
            
            price_item = QTableWidgetItem(f"{fav.price:,}원")
            price_item.setForeground(QColor("#4cc9f0"))
            self.fav_table.setItem(i, 2, price_item)
            
            self.fav_table.setItem(i, 3, QTableWidgetItem(fav.origin))
            self.fav_table.setItem(i, 4, QTableWidgetItem(fav.destination))
            self.fav_table.setItem(i, 5, QTableWidgetItem(fav.departure_date))
            self.fav_table.setItem(i, 6, QTableWidgetItem(fav.note))
        
        stats = self.db.get_stats()
        self.fav_stats_label.setText(
            f"총 {stats['favorites']}개 즐겨찾기 | "
            f"가격기록 {stats['price_history']}건 | "
            f"검색로그 {stats['search_logs']}건"
        )
    
    def _add_to_favorites(self, row):
        flight = self.table.get_flight_at_row(row)
        if not flight:
            return
        
        # Check if already favorited
        if self.db.is_favorite(
            flight.airline, flight.price, flight.departure_time,
            self.current_search_params.get('origin', ''),
            self.current_search_params.get('dest', '')
        ):
            QMessageBox.information(self, "알림", "이미 즐겨찾기에 추가된 항공권입니다.")
            return
        
        # Ask for note
        note, ok = QInputDialog.getText(self, "즐겨찾기 메모", "메모를 입력하세요 (선택):")
        if not ok:
            return
        
        flight_data = {
            'airline': flight.airline,
            'price': flight.price,
            'origin': self.current_search_params.get('origin', ''),
            'destination': self.current_search_params.get('dest', ''),
            'departure_date': self.current_search_params.get('dep', ''),
            'return_date': self.current_search_params.get('ret'),
            'departure_time': flight.departure_time,
            'arrival_time': flight.arrival_time,
            'stops': flight.stops,
            'note': note
        }
        
        self.db.add_favorite(flight_data, self.current_search_params)
        self._refresh_favorites()
        self.log_viewer.append_log(f"⭐ 즐겨찾기 추가: {flight.airline} {flight.price:,}원")
        QMessageBox.information(self, "완료", "즐겨찾기에 추가되었습니다!")
    
    def _delete_selected_favorite(self):
        row = self.fav_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "선택 오류", "삭제할 항목을 선택하세요.")
            return
        
        fav_id = int(self.fav_table.item(row, 0).text())
        reply = QMessageBox.question(
            self, "삭제 확인", "선택한 즐겨찾기를 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.remove_favorite(fav_id)
            self._refresh_favorites()
            self.log_viewer.append_log("즐겨찾기 삭제됨")

    # --- Export Functions ---
    def _export_to_csv(self):
        """검색 결과를 CSV 파일로 저장"""
        if not self.all_results:
            QMessageBox.warning(self, "내보내기 오류", "내보낼 검색 결과가 없습니다.")
            return
        
        from PyQt6.QtWidgets import QFileDialog
        import csv
        
        fname, _ = QFileDialog.getSaveFileName(
            self, "CSV로 저장", 
            f"flight_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not fname:
            return
        
        try:
            with open(fname, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # Header
                writer.writerow([
                    "항공사", "가격", "가는편 출발", "가는편 도착", "경유",
                    "오는편 출발", "오는편 도착", "오는편 경유", "출처"
                ])
                
                # Data
                for flight in self.all_results:
                    writer.writerow([
                        flight.airline,
                        flight.price,
                        flight.departure_time,
                        flight.arrival_time,
                        flight.stops,
                        getattr(flight, 'return_departure_time', '-'),
                        getattr(flight, 'return_arrival_time', '-'),
                        getattr(flight, 'return_stops', '-'),
                        flight.source
                    ])
            
            self.log_viewer.append_log(f"📥 CSV 저장 완료: {fname}")
            QMessageBox.information(self, "저장 완료", f"{len(self.all_results)}개 결과가 저장되었습니다.\n{fname}")
            
        except Exception as e:
            QMessageBox.critical(self, "저장 오류", f"파일 저장 중 오류 발생:\n{e}")
    
    def _copy_results_to_clipboard(self):
        """검색 결과를 클립보드에 복사"""
        if not self.all_results:
            QMessageBox.warning(self, "복사 오류", "복사할 검색 결과가 없습니다.")
            return
        
        from PyQt6.QtWidgets import QApplication
        
        lines = ["항공사\t가격\t출발\t도착\t경유"]
        for flight in self.all_results[:50]:  # 최대 50개
            lines.append(f"{flight.airline}\t{flight.price:,}원\t{flight.departure_time}\t{flight.arrival_time}\t{flight.stops}회")
        
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        
        self.log_viewer.append_log(f"📋 {min(len(self.all_results), 50)}개 결과 클립보드에 복사됨")
        QMessageBox.information(self, "복사 완료", f"{min(len(self.all_results), 50)}개 결과가 클립보드에 복사되었습니다.")

    # --- Multi-Destination Search ---
    def _open_multi_dest_search(self):
        dialog = MultiDestDialog(self, self.prefs)
        dialog.search_requested.connect(self._start_multi_search)
        dialog.exec()
    
    def _start_multi_search(self, origin, destinations, dep, ret, adults):
        self.log_viewer.clear()
        self.log_viewer.append_log(f"🌍 다중 목적지 검색 시작: {', '.join(destinations)}")
        
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("다중 목적지 검색 중...")
        self.tabs.setCurrentIndex(2)  # Logs tab
        
        self.multi_worker = MultiSearchWorker(origin, destinations, dep, ret, adults)
        self.multi_worker.progress.connect(self._update_progress)
        self.multi_worker.all_finished.connect(self._multi_search_finished)
        self.multi_worker.start()
    
    def _multi_search_finished(self, results):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("다중 검색 완료")
        
        # Show results dialog
        dialog = MultiDestResultDialog(results, self)
        dialog.exec()
        
        self.log_viewer.append_log(f"✅ 다중 목적지 검색 완료: {len(results)}개 목적지")

    # --- Date Range Search ---
    def _open_date_range_search(self):
        dialog = DateRangeDialog(self, self.prefs)
        dialog.search_requested.connect(self._start_date_search)
        dialog.exec()
    
    def _start_date_search(self, origin, dest, dates, duration, adults):
        self.log_viewer.clear()
        self.log_viewer.append_log(f"📅 날짜 범위 검색 시작: {dates[0]} ~ {dates[-1]}")
        
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("날짜별 검색 중...")
        self.tabs.setCurrentIndex(2)  # Logs tab
        
        self.date_worker = DateRangeWorker(origin, dest, dates, duration, adults)
        self.date_worker.progress.connect(self._update_progress)
        self.date_worker.all_finished.connect(self._date_search_finished)
        self.date_worker.start()
    
    def _date_search_finished(self, results):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("날짜 검색 완료")
        
        # Show results dialog
        dialog = DateRangeResultDialog(results, self)
        dialog.exec()
        
        self.log_viewer.append_log(f"✅ 날짜 범위 검색 완료: {len(results)}일")

    # --- Standard Search ---
    def _start_search(self, origin, dest, dep, ret, adults):
        # Save search params for later use
        self.current_search_params = {
            "origin": origin,
            "dest": dest,
            "dep": dep,
            "ret": ret,
            "adults": adults,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        
        # Save to History
        self.prefs.add_history(self.current_search_params)
        self.prefs.save_last_search(self.current_search_params)
        
        # Refresh History Tab
        if hasattr(self, 'list_history'):
            self._refresh_history_tab()

        # Reset UI
        self.search_panel.set_searching(True)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFormat("항공권 검색 중...")
        self.table.setRowCount(0)
        self.manual_frame.setVisible(False)
        self.log_viewer.clear()
        self.log_viewer.append_log("검색 프로세스 시작...")
        self.tabs.setCurrentIndex(2)  # Switch to logs
        
        # Start Worker
        self.worker = SearchWorker(origin, dest, dep, ret, adults)
        self.worker.progress.connect(self._update_progress)
        self.worker.finished.connect(self._search_finished)
        self.worker.error.connect(self._search_error)
        self.worker.manual_mode_signal.connect(self._activate_manual_mode)
        self.worker.start()

    def _update_progress(self, msg):
        self.statusBar().showMessage(msg)
        self.progress_bar.setFormat(msg)
        self.log_viewer.append_log(msg)

    def _search_finished(self, results):
        self.search_panel.set_searching(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        
        if results:
            self.all_results = results
            self.results = results
            self.table.update_data(results)
            
            # Save price history
            if self.current_search_params:
                self.db.add_price_history_batch(
                    self.current_search_params.get('origin', ''),
                    self.current_search_params.get('dest', ''),
                    self.current_search_params.get('dep', ''),
                    [{'price': r.price, 'airline': r.airline} for r in results]
                )
                
                # Log search
                self.db.log_search(
                    self.current_search_params.get('origin', ''),
                    self.current_search_params.get('dest', ''),
                    self.current_search_params.get('dep', ''),
                    self.current_search_params.get('ret'),
                    self.current_search_params.get('adults', 1),
                    len(results),
                    results[0].price if results else None
                )
            
            best_price = results[0].price
            self.progress_bar.setFormat(f"✅ 검색 완료! 최저가: {best_price:,}원")
            self.log_viewer.append_log(f"검색 완료. {len(results)}건 발견.")
            self._apply_filter()
            self.tabs.setCurrentIndex(0)  # Switch to results
        else:
            self.progress_bar.setFormat("검색 결과 없음")
            self.log_viewer.append_log("검색 결과가 없습니다.")
            QMessageBox.information(self, "결과 없음", "항공권을 찾을 수 없습니다.")

    def _search_error(self, err_msg):
        self.search_panel.set_searching(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("오류 발생")
        self.log_viewer.append_log(f"오류 발생: {err_msg}")
        QMessageBox.critical(self, "오류", f"검색 중 오류 발생:\n{err_msg}")

    def _activate_manual_mode(self, searcher):
        self.active_searcher = searcher
        self.search_panel.set_searching(False)
        
        self.manual_frame.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(50)
        self.progress_bar.setFormat("수동 모드 대기 중...")
        self.log_viewer.append_log("수동 모드로 전환됨.")
        
        QMessageBox.warning(self, "수동 모드 전환", 
                            "자동 추출에 실패했습니다.\n"
                            "브라우저창이 유지됩니다. 직접 검색 후 '데이터 추출하기' 버튼을 누르세요.")

    def _manual_extract(self):
        if not self.active_searcher:
            return
            
        try:
            self.log_viewer.append_log("수동 추출 시도...")
            results = self.active_searcher.extract_manual()
            if results:
                self._search_finished(results)
                self.active_searcher.close()
                self.active_searcher = None
                self.manual_frame.setVisible(False)
            else:
                self.log_viewer.append_log("수동 추출 실패: 데이터 없음")
                QMessageBox.warning(self, "실패", "데이터를 찾을 수 없습니다.")
        except Exception as e:
            QMessageBox.critical(self, "오류", str(e))

    def _open_main_settings(self):
        dlg = SettingsDialog(self, self.prefs)
        dlg.exec()
        self.search_panel._refresh_dest_combo()
        self.search_panel._refresh_profiles()

    def _show_shortcuts(self):
        """키보드 단축키 다이얼로그 표시"""
        dlg = ShortcutsDialog(self)
        dlg.exec()

    def _toggle_theme(self):
        """라이트/다크 테마 전환"""
        if self.is_dark_theme:
            # 다크 -> 라이트
            self.setStyleSheet(LIGHT_THEME)
            self.btn_theme.setText("☀️ 라이트")
            self.is_dark_theme = False
        else:
            # 라이트 -> 다크
            self.setStyleSheet(DARK_THEME)
            self.btn_theme.setText("🌙 다크")
            self.is_dark_theme = True

    def _apply_filter(self, filters=None):
        if filters is None:
            filters = self.filter_panel.get_current_filters()
            
        if not self.all_results:
            return
            
        direct_only = filters.get("direct_only", False)
        include_layover = filters.get("include_layover", True)
        airline_category = filters.get("airline_category", "ALL")
        max_stops = filters.get("max_stops", 3)
        
        # Outbound Time Filter
        start_h = filters.get("start_time", 0)
        end_h = filters.get("end_time", 24)
        
        # Inbound Time Filter
        ret_start_h = filters.get("ret_start_time", 0)
        ret_end_h = filters.get("ret_end_time", 24)
        
        # 만약 필터 패널에서 값을 안 줬다면(초기 로딩 등) 설정값 사용
        if "start_time" not in filters:
            pref_time = self.prefs.get_preferred_time()
            start_h = pref_time.get("departure_start", 0)
            end_h = pref_time.get("departure_end", 24)
            # 오는편 선호 시간은 설정에 없으므로 기본값(0-24) 유지
            
        filtered = []
        for f in self.all_results:
            # 1. Stops Filter
            if direct_only and f.stops > 0:
                continue
            if not include_layover and f.stops > 0:
                continue
            if f.stops > max_stops:
                continue
            
            # 2. Airline Category Filter
            if airline_category != "ALL":
                category = config.get_airline_category(f.airline)
                if category != airline_category:
                    continue
            
            # 3. Time Filter (Outbound)
            try:
                if ':' in f.departure_time:
                    dep_h = int(f.departure_time.split(':')[0])
                    if not (start_h <= dep_h <= end_h):  # <= 로 변경하여 종료시간 포함
                        continue
            except Exception:
                pass
            
            # 4. Time Filter (Inbound) - Only for round trips
            if f.is_round_trip and hasattr(f, 'return_departure_time') and f.return_departure_time:
                try:
                    if ':' in f.return_departure_time:
                        ret_dep_h = int(f.return_departure_time.split(':')[0])
                        if not (ret_start_h <= ret_dep_h <= ret_end_h):  # <= 로 변경
                            continue
                except Exception:
                    pass
                
            filtered.append(f)
            
        self.table.update_data(filtered)
        msg = f"필터링: {len(filtered)}/{len(self.all_results)} | 시간: {start_h}~{end_h}시 | 항공사: {airline_category}"
        self.statusBar().showMessage(msg)
        self.log_viewer.append_log(msg)

    # --- History Tab Methods ---
    def create_history_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.list_history = QListWidget()
        self.list_history.itemDoubleClicked.connect(self.restore_search_from_history)
        layout.addWidget(self.list_history)
        
        btn_refresh = QPushButton("기록 새로고침")
        btn_refresh.clicked.connect(self._refresh_history_tab)
        layout.addWidget(btn_refresh)
        
        self._refresh_history_tab()
        return widget

    def _refresh_history_tab(self):
        if not hasattr(self, 'list_history'):
            return
        self.list_history.clear()
        history = self.prefs.get_history()
        for item in history:
            display = f"[{item.get('timestamp')}] {item.get('origin')} ➝ {item.get('dest')} ({item.get('dep')})"
            list_item = QListWidgetItem(display)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self.list_history.addItem(list_item)

    def restore_search_from_history(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        try:
            sp = self.search_panel
            
            idx_o = sp.cb_origin.findData(data['origin'])
            if idx_o >= 0:
                sp.cb_origin.setCurrentIndex(idx_o)
            else:
                sp.cb_origin.setCurrentText(data['origin'])
            
            idx_d = sp.cb_dest.findData(data['dest'])
            if idx_d >= 0:
                sp.cb_dest.setCurrentIndex(idx_d)
            else:
                sp.cb_dest.setCurrentText(data['dest'])
            
            qt_date = QDate.fromString(data['dep'], "yyyyMMdd")
            sp.date_dep.setDate(qt_date)
            
            if data['ret']:
                sp.rb_round.setChecked(True)
                sp.date_ret.setEnabled(True)
                sp.date_ret.setDate(QDate.fromString(data['ret'], "yyyyMMdd"))
            else:
                sp.rb_oneway.setChecked(True)
                sp._toggle_return_date()
                
            sp.spin_adults.setValue(data['adults'])
            
            QMessageBox.information(self, "복원 완료", "검색 조건이 복원되었습니다.")
            
        except Exception as e:
            QMessageBox.warning(self, "오류", f"복원 중 오류: {e}")

    def closeEvent(self, event):
        """창 닫기 시 워커 스레드 및 리소스 정리"""
        # Worker threads 정리
        workers = [self.worker, self.multi_worker, self.date_worker]
        for worker in workers:
            if worker and worker.isRunning():
                worker.terminate()
                worker.wait(2000)  # 최대 2초 대기
        
        # Active searcher 브라우저 종료
        if self.active_searcher:
            try:
                self.active_searcher.close()
            except Exception:
                pass
        
        # 설정 저장
        try:
            if hasattr(self, 'search_panel'):
                self.search_panel.save_settings()
            self.prefs.save()
        except Exception:
            pass
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
