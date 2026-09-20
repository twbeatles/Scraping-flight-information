""""Table (Modern Rows with Enhanced Effects)" section of the styles_dark theme (SRP: one QSS section per module)."""

TABLE = """/* ===== Table (Modern Rows with Enhanced Effects) ===== */
QTableWidget {
    background-color: rgba(22, 33, 62, 0.7);
    border: 1px solid rgba(30, 58, 95, 0.8);
    border-radius: 16px;
    gridline-color: rgba(30, 58, 95, 0.35);
    selection-background-color: rgba(102, 126, 234, 0.35);
    selection-color: #f1f5f9;
    alternate-background-color: rgba(15, 20, 35, 0.4);
}
QTableWidget::item {
    padding: 14px 12px;
    border-bottom: 1px solid rgba(30, 58, 95, 0.2);
}
QTableWidget::item:selected {
    background-color: rgba(102, 126, 234, 0.4);
    border-left: 4px solid #818cf8;
}
QTableWidget::item:hover {
    background-color: rgba(34, 211, 238, 0.18);
}
QHeaderView::section {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(15, 52, 96, 0.98), stop:1 rgba(22, 33, 62, 0.98));
    color: #e2e8f0;
    padding: 16px 14px;
    border: none;
    border-bottom: 3px solid #22d3ee;
    font-weight: 700;
    font-size: 13px;
    letter-spacing: 0.4px;
}

"""
