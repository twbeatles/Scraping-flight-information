""""Buttons" section of the styles_light theme (SRP: one QSS section per module)."""

BUTTONS = """/* ===== Buttons ===== */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #3b82f6, stop:1 #8b5cf6);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: bold;
    min-height: 20px;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #2563eb, stop:1 #7c3aed);
    border: 2px solid #a78bfa;
}
QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
        stop:0 #1d4ed8, stop:1 #6d28d9);
}
QPushButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
}

/* Tool Buttons (Secondary) */
QPushButton#tool_btn {
    background-color: #e2e8f0;
    color: #1e293b;
    padding: 8px 14px;
    border-radius: 6px;
}
QPushButton#tool_btn:hover {
    background-color: #3b82f6;
    color: white;
}

"""
