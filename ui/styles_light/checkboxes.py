""""Checkboxes" section of the styles_light theme (SRP: one QSS section per module)."""

CHECKBOXES = """/* ===== Checkboxes ===== */
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

"""
