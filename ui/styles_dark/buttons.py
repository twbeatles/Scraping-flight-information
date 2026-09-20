""""Buttons (Premium Gradient + Glow)" section of the styles_dark theme (SRP: one QSS section per module)."""

BUTTONS = """/* ===== Buttons (Premium Gradient + Glow) ===== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 #667eea, stop:0.5 #764ba2, stop:1 #f093fb);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 12px 26px;
    font-weight: 600;
    font-size: 13px;
    min-height: 22px;
    letter-spacing: 0.3px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 #818cf8, stop:0.5 #a78bfa, stop:1 #f5a9d0);
    border: 2px solid rgba(167, 139, 250, 0.6);
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
        stop:0 #4f46e5, stop:0.5 #6d28d9, stop:1 #d946ef);
    padding-top: 13px;
    padding-bottom: 11px;
}
QPushButton:disabled {
    background-color: #1e293b;
    color: #475569;
    border: none;
}

/* Tool Buttons (Secondary - Glass Effect) */
QPushButton#tool_btn {
    background-color: rgba(34, 211, 238, 0.12);
    color: #22d3ee;
    padding: 9px 18px;
    border-radius: 10px;
    border: 1px solid rgba(34, 211, 238, 0.25);
    font-weight: 500;
}
QPushButton#tool_btn:hover {
    background-color: rgba(34, 211, 238, 0.95);
    color: #0a0a14;
    border: 1px solid #22d3ee;
}
QPushButton#tool_btn:pressed {
    background-color: #0891b2;
    color: white;
}

/* Filter/Toggle Buttons */
QPushButton#filter_btn {
    background-color: rgba(30, 58, 95, 0.3);
    border: 1px solid rgba(71, 85, 105, 0.5);
    color: #94a3b8;
    border-radius: 10px;
    padding: 8px 14px;
}
QPushButton#filter_btn:checked, QPushButton#filter_btn:hover {
    background-color: rgba(34, 211, 238, 0.18);
    border: 1px solid #22d3ee;
    color: #22d3ee;
}

/* Manual Extract Button (Attention - Rose Glow) */
QPushButton#manual_btn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #f43f5e, stop:0.5 #ec4899, stop:1 #d946ef);
    font-size: 15px;
    padding: 14px 28px;
    border-radius: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QPushButton#manual_btn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #fb7185, stop:0.5 #f472b6, stop:1 #e879f9);
    border: 2px solid rgba(251, 113, 133, 0.6);
}

"""
