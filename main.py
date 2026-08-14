#!/usr/bin/env python3
"""
RSSTransFeed Desktop Application
A native-style RSS reader for macOS built with Python and Tkinter

Entry point for the application.
"""

import tkinter as tk
import sys
import os

# Add current directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.app import RSSReaderApp


def main():
    """Main entry point"""
    root = tk.Tk()
    app = RSSReaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
