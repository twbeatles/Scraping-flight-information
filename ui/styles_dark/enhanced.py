""""Enhanced Progress States" section of the styles_dark theme (SRP: one QSS section per module)."""

ENHANCED = """/* ===== Enhanced Progress States ===== */
QProgressBar#progress_success {
    background: rgba(15, 52, 96, 0.5);
    border-radius: 14px;
}
QProgressBar#progress_success::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #22c55e, stop:1 #4ade80);
    border-radius: 13px;
}
QProgressBar#progress_error::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #ef4444, stop:1 #f87171);
    border-radius: 13px;
}

"""
