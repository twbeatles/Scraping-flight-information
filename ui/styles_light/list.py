""""List Widget" section of the styles_light theme (SRP: one QSS section per module)."""

LIST = """/* ===== List Widget ===== */
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

"""
