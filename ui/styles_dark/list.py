""""List Widget" section of the styles_dark theme (SRP: one QSS section per module)."""

LIST = """/* ===== List Widget ===== */
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

"""
