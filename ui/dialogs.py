"""Dialog windows for RSS Reader"""
import tkinter as tk
from tkinter import ttk, messagebox


class AddSubscriptionDialog:
    """Dialog for adding a new subscription"""
    
    def __init__(self, parent, on_add_callback=None):
        self.parent = parent
        self.on_add_callback = on_add_callback
        self.result = None
        self.create_dialog()
    
    def create_dialog(self):
        """Create the dialog window"""
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
    """Show about information"""
    
    @staticmethod
    def show(parent):
        """Show the about dialog"""
        messagebox.showinfo(
            "关于 RSSTransFeed",
            "RSSTransFeed Desktop Application\n\n"
            "一个原生风格的 macOS RSS 阅读器\n"
            "使用 Python 和 Tkinter 构建"
        )
