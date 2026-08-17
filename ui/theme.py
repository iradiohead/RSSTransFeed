"""Application palette and Qt stylesheet."""

COLORS = {
    "background": "#151C23",
    "surface": "#171D24",
    "border": "#2D343B",
    "text": "#C1C7CE",
    "muted": "#8E949C",
    "accent": "#2D75E5",
    "button": "#1A2027",
}

STYLESHEET = f"""
QWidget {{
    background: {COLORS["background"]};
    color: {COLORS["text"]};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}
QMainWindow, QDialog {{ background: {COLORS["background"]}; }}
QListWidget, QTextBrowser, QLineEdit {{
    background: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 7px;
    padding: 5px;
    selection-background-color: {COLORS["accent"]};
    selection-color: white;
}}
QListWidget::item {{ min-height: 28px; border-radius: 4px; padding: 2px 6px; }}
QListWidget::item:selected {{ background: {COLORS["accent"]}; }}
QPushButton {{
    background: {COLORS["button"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    padding: 6px 12px;
}}
QPushButton:hover {{ background: {COLORS["border"]}; color: white; }}
QPushButton:pressed {{ background: {COLORS["background"]}; }}
QPushButton:disabled {{ color: #59616A; }}
QSplitter::handle {{ background: {COLORS["border"]}; border-radius: 2px; }}
QSplitter::handle:horizontal {{ width: 5px; margin: 5px 1px; }}
QSplitter::handle:vertical {{ height: 5px; margin: 1px 5px; }}
QScrollBar:vertical {{
    background: transparent; width: 18px; margin: 1px;
}}
QScrollBar::handle:vertical {{
    background: #4A5568; border-radius: 6px; min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{ background: #64748B; }}
QScrollBar::handle:vertical:pressed {{ background: #718096; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""
