""""Radio Buttons" section of the styles_dark theme (SRP: one QSS section per module)."""

RADIO = """/* ===== Radio Buttons ===== */
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

"""
