#!/usr/bin/env python3
"""RSSTransFeed PySide6 entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from services import StorageService
from ui.main_window import MainWindow
from ui.theme import STYLESHEET


def main() -> int:
    """Configure QApplication, migrate legacy data, and run the main window."""
    app = QApplication(sys.argv)
    app.setApplicationName("RSSTransFeed")
    app.setOrganizationName("RSSTransFeed")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLESHEET)

    storage = StorageService()
    project_root = Path(__file__).resolve().parent
    storage.migrate_legacy(Path(sys.executable).resolve().parent)
    storage.migrate_legacy(project_root.parent / "RSSTransFeed")

    window = MainWindow(storage)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
