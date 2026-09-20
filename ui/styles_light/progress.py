""""Progress Bar" section of the styles_light theme (SRP: one QSS section per module)."""

PROGRESS = """/* ===== Progress Bar ===== */
QProgressBar {
    background: #f1f5f9;
    border-radius: 8px;
    text-align: center;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    height: 28px;
    font-weight: bold;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #3b82f6, stop:1 #8b5cf6);
    border-radius: 6px;
}

"""
