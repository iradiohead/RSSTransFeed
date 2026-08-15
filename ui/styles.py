"""Styling and theme configuration for RSS Reader"""
import tkinter as tk
from tkinter import ttk


class Theme:
    """定义整个应用的深色视觉主题。

    这里集中存放颜色常量，用于统一窗口背景、文字颜色、按钮样式和高亮状态，
    保证界面风格一致。
    """
    
     # Colors - Dark blue-gray theme (照搬参考图配色)
    BG_PRIMARY = "#151C23"
    BG_SECONDARY = "#171D24"
    BG_SIDEBAR = "#151C23"
    BG_SPLIT = "#151C23"
    BG_SPLITTER = "#2D343B"
    BG_SPLITTER_HIGHLIGHT = "#4A5568"
    BG_LISTBOX = "#171D24"
    BG_ARTICLE = "#151C23"
    BG_FOOTER = "#151C23"

    # Text colors - Grayish white (not pure white)
    FG_PRIMARY = "#C1C7CE"
    FG_SECONDARY = "#B5BBC2"
    FG_MUTED = "#8E949C"
    FG_SELECTED = "#2D75E5"
    FG_SELECTED_MUTED = "#8E949C"

    # Button colors
    BTN_BG = "#1A2027"
    BTN_BG_ACTIVE = "#2D343B"
    BTN_BG_PRESSED = "#151C23"
    BTN_FG = "#C1C7CE"
    BTN_FG_ACTIVE = "#FFFFFF"

    # Input colors
    INPUT_BG = "#171D24"
    INPUT_FG = "#C1C7CE"

    # Selection colors
    SELECT_BG = "#2D75E5"
    SELECT_FG = "#FFFFFF"


def configure_styles() -> ttk.Style:
    """初始化 ttk 主题样式，返回一个已配置的 Style 对象。

    这个函数会设置窗口、按钮、输入框和标签的统一视觉风格，确保整个应用
    使用同一套深色 UI 设计。
    """
    style = ttk.Style()
    
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    
    # Configure TFrame
    style.configure("TFrame", background=Theme.BG_PRIMARY)
    
    # Configure TLabel
    style.configure("TLabel", background=Theme.BG_PRIMARY, foreground=Theme.FG_SECONDARY)
    
    # Configure TButton
    style.configure(
        "TButton",
        background=Theme.BTN_BG,
        foreground=Theme.BTN_FG,
        borderwidth=0
    )
    style.map(
        "TButton",
        background=[("active", Theme.BTN_BG_ACTIVE), ("pressed", Theme.BTN_BG_PRESSED)],
        foreground=[("active", Theme.BTN_FG_ACTIVE)]
    )
    
    # Configure TEntry
    style.configure(
        "TEntry",
        fieldbackground=Theme.INPUT_BG,
        foreground=Theme.INPUT_FG
    )
    
    return style
