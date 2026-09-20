""""Badge Styles (Best Price, Direct Flight)" section of the styles_dark theme (SRP: one QSS section per module)."""

BADGE = """/* ===== Badge Styles (Best Price, Direct Flight) ===== */
QLabel#badge_best {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #22c55e, stop:1 #4ade80);
    color: #052e16;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 12px;
    letter-spacing: 0.3px;
}
QLabel#badge_direct {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #06b6d4, stop:1 #22d3ee);
    color: #083344;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 12px;
}
QLabel#badge_info {
    background-color: rgba(99, 102, 241, 0.2);
    color: #a5b4fc;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 12px;
    border: 1px solid rgba(99, 102, 241, 0.4);
}

"""
