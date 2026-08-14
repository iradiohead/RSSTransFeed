"""Styling and theme configuration for RSS Reader"""
import tkinter as tk
from tkinter import ttk


class Theme:
    """Dark theme colors for RSS Reader"""
    
    # Colors
    BG_PRIMARY = "#0f1115"
    BG_SECONDARY = "#11151b"
    BG_SIDEBAR = "#171b22"
    BG_SPLIT = "#151922"
    BG_SPLITTER = "#2a2e37"
    BG_LISTBOX = "#1b1f27"
    BG_ARTICLE = "#121821"
    BG_FOOTER = "#0f1115"
    
    # Text colors
    FG_PRIMARY = "#edf1f7"
    FG_SECONDARY = "#e7e8ea"
    FG_MUTED = "#8a939f"
    FG_SELECTED = "#3ad17f"
    FG_SELECTED_MUTED = "#2fbf6f"
    
    # Button colors
    BTN_BG = "#1f242c"
    BTN_BG_ACTIVE = "#2a3038"
    BTN_BG_PRESSED = "#1b2128"
    BTN_FG = "#e7e8ea"
    BTN_FG_ACTIVE = "#ffffff"
    
    # Input colors
    INPUT_BG = "#1d2128"
    INPUT_FG = "#e7e8ea"
    
    # Selection colors
    SELECT_BG = "#2d4d75"
    SELECT_FG = "#ffffff"


def configure_styles() -> ttk.Style:
    """Configure ttk styles with dark theme
    
    Returns:
        Configured ttk.Style object
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
