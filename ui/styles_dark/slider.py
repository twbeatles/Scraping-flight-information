""""Slider (Price Filter)" section of the styles_dark theme (SRP: one QSS section per module)."""

SLIDER = """/* ===== Slider (Price Filter) ===== */
QSlider::groove:horizontal {
    background: rgba(15, 52, 96, 0.8);
    height: 8px;
    border-radius: 4px;
}
QSlider::handle:horizontal {
    background: #06b6d4;
    width: 20px;
    height: 20px;
    margin: -6px 0;
    border-radius: 10px;
    border: 2px solid #0f0f1a;
}
QSlider::handle:horizontal:hover {
    background: #22d3ee;
    border: 2px solid #06b6d4;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #06b6d4, stop:1 #8b5cf6);
    border-radius: 4px;
}

"""
