""""Radio Buttons" section of the styles_light theme (SRP: one QSS section per module)."""

RADIO = """/* ===== Radio Buttons ===== */
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

"""
