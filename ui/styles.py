
"""
UI Styles and Themes
"""

DARK_THEME = """
/* ===== Base Application ===== */
QMainWindow, QWidget {
    background-color: #0f0f1a;
    color: #e2e8f0;
    font-family: 'Pretendard', 'Malgun Gothic', 'Segoe UI', sans-serif;
    font-size: 14px;
}

/* ===== Typography ===== */
QLabel#title {
    font-size: 32px;
    font-weight: 800;
    color: #06b6d4;
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
    color: #e2e8f0;
    margin-top: 10px;
    margin-bottom: 8px;
    padding-left: 8px;
    border-left: 3px solid #06b6d4;
}
QLabel#field_label {
    font-size: 12px;
    color: #94a3b8;
    margin-bottom: 3px;
}

/* ===== Cards (Glassmorphism) ===== */
QFrame#card {
    background-color: rgba(22, 33, 62, 0.9);
    border: 1px solid rgba(6, 182, 212, 0.2);
    border-radius: 16px;
    padding: 20px;
}
QFrame#card:hover {
    border: 1px solid rgba(6, 182, 212, 0.4);
    background-color: rgba(22, 33, 62, 0.95);
}

/* ===== Input Fields (Glow Focus) ===== */
QComboBox, QDateEdit, QSpinBox, QLineEdit {
    background-color: rgba(15, 52, 96, 0.8);
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 10px 14px;
    color: white;
    selection-background-color: #06b6d4;
    min-height: 22px;
}
QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QLineEdit:hover {
    border: 1px solid #06b6d4;
    background-color: rgba(15, 52, 96, 0.9);
}
QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QLineEdit:focus {
    border: 2px solid #06b6d4;
    background-color: rgba(6, 182, 212, 0.1);
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
    border-top: 6px solid #06b6d4;
    margin-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 1px solid #1e3a5f;
    selection-background-color: #6366f1;
    color: white;
    padding: 5px;
    border-radius: 8px;
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

/* ===== Buttons (Gradient + Glow) ===== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 #6366f1, stop:0.5 #8b5cf6, stop:1 #a855f7);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 12px 24px;
    font-weight: 600;
    min-height: 20px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 #818cf8, stop:0.5 #a78bfa, stop:1 #c084fc);
    border: 2px solid rgba(167, 139, 250, 0.5);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 #4f46e5, stop:0.5 #7c3aed, stop:1 #9333ea);
    padding-top: 13px;
    padding-bottom: 11px;
}
QPushButton:disabled {
    background-color: #1e293b;
    color: #475569;
}

/* Tool Buttons (Secondary - Cyan) */
QPushButton#tool_btn {
    background-color: rgba(6, 182, 212, 0.15);
    color: #06b6d4;
    padding: 8px 16px;
    border-radius: 8px;
    border: 1px solid rgba(6, 182, 212, 0.3);
}
QPushButton#tool_btn:hover {
    background-color: #06b6d4;
    color: #0f0f1a;
    border: 1px solid #06b6d4;
}

/* Filter/Toggle Buttons */
QPushButton#filter_btn {
    background-color: transparent;
    border: 1px solid #1e3a5f;
    color: #94a3b8;
    border-radius: 8px;
}
QPushButton#filter_btn:checked, QPushButton#filter_btn:hover {
    background-color: rgba(6, 182, 212, 0.15);
    border: 1px solid #06b6d4;
    color: #06b6d4;
}

/* Manual Extract Button (Attention - Rose) */
QPushButton#manual_btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #f43f5e, stop:1 #ec4899);
    font-size: 15px;
    padding: 14px 24px;
    border-radius: 12px;
}
QPushButton#manual_btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #fb7185, stop:1 #f472b6);
    border: 2px solid rgba(251, 113, 133, 0.5);
}

/* ===== Table (Enhanced Rows) ===== */
QTableWidget {
    background-color: rgba(22, 33, 62, 0.6);
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    gridline-color: rgba(30, 58, 95, 0.5);
    selection-background-color: rgba(99, 102, 241, 0.25);
    selection-color: #e0e7ff;
    alternate-background-color: rgba(15, 15, 26, 0.4);
}
QTableWidget::item {
    padding: 10px 8px;
    border-bottom: 1px solid rgba(30, 58, 95, 0.3);
}
QTableWidget::item:selected {
    background-color: rgba(99, 102, 241, 0.3);
    border-left: 3px solid #6366f1;
}
QTableWidget::item:hover {
    background-color: rgba(6, 182, 212, 0.1);
}
QHeaderView::section {
    background-color: rgba(15, 52, 96, 0.9);
    color: #94a3b8;
    padding: 12px 10px;
    border: none;
    border-bottom: 2px solid #06b6d4;
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

/* ===== Progress Bar (Animated Gradient) ===== */
QProgressBar {
    background: rgba(15, 52, 96, 0.6);
    border-radius: 12px;
    text-align: center;
    color: white;
    border: 1px solid #1e3a5f;
    height: 30px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #06b6d4, stop:0.5 #8b5cf6, stop:1 #ec4899);
    border-radius: 11px;
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

/* ===== GroupBox (Enhanced Sections) ===== */
QGroupBox {
    background-color: rgba(22, 33, 62, 0.7);
    border: 1px solid rgba(6, 182, 212, 0.2);
    border-radius: 12px;
    margin-top: 16px;
    padding: 20px 15px 15px 15px;
    font-weight: bold;
    color: #e2e8f0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    top: 3px;
    padding: 0 8px;
    background-color: rgba(22, 33, 62, 0.95);
    color: #06b6d4;
    border-radius: 4px;
}

/* ===== Secondary Button (Less Emphasis) ===== */
QPushButton#secondary_btn {
    background-color: rgba(30, 58, 95, 0.6);
    color: #94a3b8;
    border: 1px solid #30475e;
    border-radius: 8px;
    padding: 10px 16px;
    font-weight: 500;
}
QPushButton#secondary_btn:hover {
    background-color: rgba(6, 182, 212, 0.15);
    color: #06b6d4;
    border: 1px solid #06b6d4;
}

/* ===== Icon Button (Small Square) ===== */
QPushButton#icon_btn {
    background-color: transparent;
    border: 1px solid #30475e;
    border-radius: 8px;
    padding: 8px;
    min-width: 36px;
    max-width: 36px;
    min-height: 36px;
    max-height: 36px;
}
QPushButton#icon_btn:hover {
    background-color: rgba(6, 182, 212, 0.2);
    border: 1px solid #06b6d4;
}

/* ===== Slider (Price Filter) ===== */
QSlider::groove:horizontal {
    background: rgba(15, 52, 96, 0.8);
    height: 8px;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #06b6d4;
    width: 20px;
    height: 20px;
    margin: -6px 0;
    border-radius: 10px;
    border: 2px solid #0f0f1a;
}
QSlider::handle:horizontal:hover {
    background: #22d3ee;
    border: 2px solid #06b6d4;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #06b6d4, stop:1 #8b5cf6);
    border-radius: 4px;
}

/* ===== Separator Line ===== */
QFrame#separator {
    background-color: #30475e;
    max-height: 1px;
    margin: 10px 0;
}
QFrame#v_separator {
    background-color: #30475e;
    max-width: 1px;
    margin: 0 10px;
}

/* ===== Success/Warning/Error Labels ===== */
QLabel#success_label {
    color: #22c55e;
    font-weight: bold;
}
QLabel#warning_label {
    color: #f59e0b;
    font-weight: bold;
}
QLabel#error_label {
    color: #ef4444;
    font-weight: bold;
}

/* ===== Price Highlight ===== */
QLabel#price_highlight {
    font-size: 24px;
    font-weight: bold;
    color: #22c55e;
}
"""

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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #3b82f6, stop:1 #8b5cf6);
    border-radius: 6px;
}

/* ===== Tooltips ===== */
QToolTip {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #3b82f6;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
}

/* ===== List Widget ===== */
QListWidget {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 5px;
}
QListWidget::item {
    padding: 10px;
    border-radius: 6px;
    margin: 2px 0;
}
QListWidget::item:selected {
    background-color: #e0f2fe;
    color: #3b82f6;
}
QListWidget::item:hover {
    background-color: #f1f5f9;
}

/* ===== Message Boxes ===== */
QMessageBox {
    background-color: #f8fafc;
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

/* ===== GroupBox ===== */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-top: 16px;
    padding: 20px 15px 15px 15px;
    font-weight: bold;
    color: #1e293b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    top: 3px;
    padding: 0 8px;
    background-color: #f1f5f9;
    color: #3b82f6;
    border-radius: 4px;
}
"""


# Default theme alias
MODERN_THEME = DARK_THEME
