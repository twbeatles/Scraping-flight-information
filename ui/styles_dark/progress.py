""""Progress Bar (Premium Animated Gradient)" section of the styles_dark theme (SRP: one QSS section per module)."""

PROGRESS = """/* ===== Progress Bar (Premium Animated Gradient) ===== */
QProgressBar {
    background: rgba(15, 52, 96, 0.5);
    border-radius: 14px;
    text-align: center;
    color: white;
    border: 1px solid rgba(30, 58, 95, 0.6);
    height: 32px;
    font-weight: 600;
    font-size: 12px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #06b6d4, stop:0.3 #667eea, stop:0.6 #a855f7, stop:1 #ec4899);
    border-radius: 13px;
}

"""
