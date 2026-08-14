"""Dialog windows for RSS Reader"""
import tkinter as tk
from tkinter import ttk, messagebox


class AddSubscriptionDialog:
    """用于新增订阅的弹窗。

    这个对话框让用户输入 RSS 地址，并在确认后把地址交给回调函数处理。
    """
    
    def __init__(self, parent, on_add_callback=None):
        """初始化订阅添加窗口。

        Args:
            parent: 父窗口，用于挂载对话框。
            on_add_callback: 用户确认时调用的回调函数，通常负责校验和保存订阅。
        """
        self.parent = parent
        self.on_add_callback = on_add_callback
        self.result = None
        self.create_dialog()
    
    def create_dialog(self):
        """构造弹窗界面，并绑定添加/取消逻辑。"""
        dialog = tk.Toplevel(self.parent)
        dialog.title("添加订阅")
        dialog.geometry("400x150")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # URL input
        ttk.Label(dialog, text="RSS 地址:").pack(pady=(10, 5))
        url_entry = ttk.Entry(dialog, width=50)
        url_entry.pack(pady=5)
        url_entry.focus()
        
        # Buttons frame
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def handle_add():
            """处理用户点击“添加”的事件。"""
            url = url_entry.get().strip()
            if not url:
                messagebox.showerror("错误", "请输入 RSS 地址")
                return
            
            if self.on_add_callback:
                result = self.on_add_callback(url)
                if result:
                    dialog.destroy()
        
        ttk.Button(button_frame, text="取消", command=dialog.destroy).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="添加", command=handle_add).pack(side=tk.LEFT)
        
        self.dialog = dialog


class AboutDialog:
    """显示软件介绍窗口。"""
    
    @staticmethod
    def show(parent):
        """弹出关于窗口，展示应用名称和基础说明。"""
        messagebox.showinfo(
            "关于 RSSTransFeed",
            "RSSTransFeed Desktop Application\n\n"
            "一个原生风格的 macOS RSS 阅读器\n"
            "使用 Python 和 Tkinter 构建"
        )
