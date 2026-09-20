""""GroupBox (Enhanced Sections)" section of the styles_dark theme (SRP: one QSS section per module)."""

GROUPBOX = """/* ===== GroupBox (Enhanced Sections) ===== */
QGroupBox {
    background-color: rgba(22, 33, 62, 0.7);
    border: 1px solid rgba(6, 182, 212, 0.2);
    border-radius: 12px;
    margin-top: 16px;
    padding: 20px 15px 15px 15px;
    font-weight: bold;
    color: #e2e8f0;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 15px;
    top: 3px;
    padding: 0 8px;
    background-color: rgba(22, 33, 62, 0.95);
    color: #06b6d4;
    border-radius: 4px;
}

"""
