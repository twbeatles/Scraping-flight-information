""""Input Fields" section of the styles_light theme (SRP: one QSS section per module)."""

INPUT = """/* ===== Input Fields ===== */
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

"""
