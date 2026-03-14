"""Light UI theme."""

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
