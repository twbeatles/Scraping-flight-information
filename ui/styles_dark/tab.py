""""Tab Widget (Modern Tabs)" section of the styles_dark theme (SRP: one QSS section per module)."""

TAB = """/* ===== Tab Widget (Modern Tabs) ===== */
QTabWidget::pane {
    border: 1px solid rgba(48, 71, 94, 0.6);
    background: rgba(22, 33, 62, 0.6);
    border-radius: 0 12px 12px 12px;
    padding: 8px;
}
QTabBar::tab {
    background: rgba(15, 52, 96, 0.6);
    color: #94a3b8;
    padding: 12px 28px;
    margin-right: 3px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 500;
    font-size: 13px;
}
QTabBar::tab:selected {
    background: rgba(22, 33, 62, 0.9);
    color: #22d3ee;
    border-bottom: 3px solid #22d3ee;
}
QTabBar::tab:hover:!selected {
    background: rgba(30, 58, 95, 0.7);
    color: #f1f5f9;
}

"""
