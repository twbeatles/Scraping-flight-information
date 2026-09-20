""""Scrollbars" section of the styles_light theme (SRP: one QSS section per module)."""

SCROLLBARS = """/* ===== Scrollbars ===== */
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

"""
