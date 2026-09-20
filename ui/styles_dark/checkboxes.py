""""Checkboxes" section of the styles_dark theme (SRP: one QSS section per module)."""

CHECKBOXES = """/* ===== Checkboxes ===== */
QCheckBox {
    spacing: 8px;
    color: #e6e6e6;
}
QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border-radius: 4px;
    border: 2px solid #30475e;
    background-color: #0f3460;
}
QCheckBox::indicator:hover {
    border: 2px solid #4cc9f0;
}
QCheckBox::indicator:checked {
    background-color: #4cc9f0;
    border: 2px solid #4cc9f0;
    image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMxYTFhMmUiIHN0cm9rZS13aWR0aD0iMyIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSIyMCA2IDkgMTcgNCAxMiI+PC9wb2x5bGluZT48L3N2Zz4=);
}

"""
