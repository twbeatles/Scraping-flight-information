""""Scrollbars" section of the styles_dark theme (SRP: one QSS section per module)."""

SCROLLBARS = """/* ===== Scrollbars ===== */
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

"""
