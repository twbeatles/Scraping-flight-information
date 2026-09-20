""""GroupBox" section of the styles_light theme (SRP: one QSS section per module)."""

GROUPBOX = """/* ===== GroupBox ===== */
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    margin-top: 16px;
    padding: 20px 15px 15px 15px;
    font-weight: bold;
    color: #1e293b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    top: 3px;
    padding: 0 8px;
    background-color: #f1f5f9;
    color: #3b82f6;
    border-radius: 4px;
}
"""
