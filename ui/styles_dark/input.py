""""Input Fields (Enhanced Glow Focus)" section of the styles_dark theme (SRP: one QSS section per module)."""

INPUT = """/* ===== Input Fields (Enhanced Glow Focus) ===== */
QComboBox, QDateEdit, QSpinBox, QLineEdit {
    background-color: rgba(15, 52, 96, 0.85);
    border: 1px solid rgba(30, 58, 95, 0.8);
    border-radius: 12px;
    padding: 11px 16px;
    color: white;
    selection-background-color: #06b6d4;
    min-height: 24px;
}
QComboBox:hover, QDateEdit:hover, QSpinBox:hover, QLineEdit:hover {
    border: 1px solid rgba(6, 182, 212, 0.7);
    background-color: rgba(15, 52, 96, 0.95);
}
QComboBox:focus, QDateEdit:focus, QSpinBox:focus, QLineEdit:focus {
    border: 2px solid #22d3ee;
    background-color: rgba(6, 182, 212, 0.15);
    outline: none;
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

"""
