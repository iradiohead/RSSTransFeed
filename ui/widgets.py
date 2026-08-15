"""Custom UI widgets"""
import tkinter as tk

from ui.styles import Theme


class RoundedSplitter(tk.Canvas):
    """圆角胶囊样式的分割条:细线两端为圆形端帽,整条均可拖动。

    用 Canvas 画一条 capstyle=ROUND 的线实现圆角收尾,
    背景色与所在容器一致,视觉上只露出圆角细条。
    """

    def __init__(self, parent, orient: str = "vertical", thickness: int = 8,
                 bar_width: int = 4, **kwargs):
        super().__init__(
            parent,
            bg=Theme.BG_PRIMARY,
            highlightthickness=0,
            borderwidth=0,
            **kwargs
        )
        self.orient = orient
        self.thickness = thickness
        self.bar_width = bar_width
        self.bind("<Configure>", self._redraw)
        
        # 添加光标变化和点击事件，提升用户体验
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, event):
        """鼠标进入分割线区域时改变光标"""
        if self.orient == "vertical":
            self.config(cursor="sb_h_double_arrow")
        else:
            self.config(cursor="sb_v_double_arrow")

    def _on_leave(self, event):
        """鼠标离开分割线区域时恢复默认光标"""
        self.config(cursor="")

    def _redraw(self, event=None):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return
        margin = 6
        if self.orient == "vertical":
            self.create_line(
                w / 2, margin,
                w / 2, max(margin + 1, h - margin),
                width=self.bar_width,
                fill=Theme.BG_SPLITTER_HIGHLIGHT,
                capstyle=tk.ROUND,
            )
        else:
            self.create_line(
                margin, h / 2,
                max(margin + 1, w - margin), h / 2,
                width=self.bar_width,
                fill=Theme.BG_SPLITTER_HIGHLIGHT,
                capstyle=tk.ROUND,
            )
