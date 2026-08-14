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
    """启动主窗口并进入 Tkinter 事件循环。

    这是程序的入口函数。它创建应用主窗口，实例化 RSS 阅读器界面，
    然后让 Tkinter 持续监听用户事件，直到窗口关闭。
    """
    root = tk.Tk()
    app = RSSReaderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
