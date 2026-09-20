""""Table" section of the styles_light theme (SRP: one QSS section per module)."""

TABLE = """/* ===== Table ===== */
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

"""
