"""Main application class for RSS Reader"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import webbrowser
from typing import Optional, List

from models.subscription import Article
from services.subscription_manager import SubscriptionManager
from services.storage_service import StorageService
from ui.styles import Theme, configure_styles
from ui.dialogs import AddSubscriptionDialog, AboutDialog
from utils.date_utils import format_date


class RSSReaderApp:
    """Main RSS Reader application"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("RSSTransFeed")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.root.configure(bg=Theme.BG_PRIMARY)
        
        # Initialize services
        self.storage = StorageService('subscriptions.json')
        self.subscription_manager = SubscriptionManager(self.storage)
        
        # UI state
        self.selected_index: Optional[int] = None
        self.article_list_height = 260
        self.dragging_splitter = False
        self.read_articles = set()  # Track read article IDs
        self.is_refreshing = False
        
        # Current state
        self.current_feed_id: Optional[str] = None
        self.current_articles: List[Article] = []
        
        # Create UI
        self.create_menu()
        self.create_widgets()
        self.update_subscription_list()
    
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="添加订阅", command=self.add_subscription)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="关于", command=self.show_about)
    
    def create_widgets(self):
        """Create UI widgets"""
        configure_styles()
        
        # Main frame
        main_frame = tk.Frame(self.root, bg=Theme.BG_PRIMARY)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Split frame for sidebar and content
        split_frame = tk.Frame(main_frame, bg=Theme.BG_SPLIT)
        split_frame.pack(fill=tk.BOTH, expand=True)
        
        # Sidebar
        self._create_sidebar(split_frame)
        
        # Content area
        self._create_content_area(split_frame)
    
    def _create_sidebar(self, parent):
        """Create left sidebar with subscriptions"""
        self.sidebar_frame = tk.Frame(parent, width=250, bg=Theme.BG_SIDEBAR)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.sidebar_frame.pack_propagate(False)
        
        # Sidebar header
        sidebar_header = tk.Frame(self.sidebar_frame, bg=Theme.BG_SIDEBAR)
        sidebar_header.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(sidebar_header, text="RSS 订阅", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        ttk.Button(sidebar_header, text="+", width=3, command=self.add_subscription).pack(side=tk.RIGHT)
        
        # Subscription list
        self.subscription_listbox = tk.Listbox(
            self.sidebar_frame,
            selectmode=tk.SINGLE,
            bg=Theme.BG_LISTBOX,
            fg=Theme.FG_PRIMARY,
            selectbackground=Theme.SELECT_BG,
            selectforeground=Theme.SELECT_FG
        )
        self.subscription_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.subscription_listbox.bind('<<ListboxSelect>>', self.on_subscription_select)
        
        # Refresh button
        self.refresh_btn = ttk.Button(self.sidebar_frame, text="🔄 刷新", command=self.refresh_all)
        self.refresh_btn.pack(fill=tk.X, pady=(0, 10))
    
    def _create_content_area(self, parent):
        """Create main content area with article list and viewer"""
        self.content_frame = tk.Frame(parent, bg=Theme.BG_SECONDARY)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Stacked content (top to bottom)
        stacked_content = tk.Frame(self.content_frame, bg=Theme.BG_SECONDARY)
        stacked_content.pack(fill=tk.BOTH, expand=True)
        
        # Article list panel
        article_frame = tk.Frame(stacked_content, bg=Theme.BG_SECONDARY, height=self.article_list_height)
        article_frame.pack(side=tk.TOP, fill=tk.X, expand=False)
        
        article_header = tk.Frame(article_frame, bg=Theme.BG_SECONDARY)
        article_header.pack(fill=tk.X)
        
        self.article_title_label = ttk.Label(article_header, text="文章列表", font=("Arial", 12, "bold"))
        self.article_title_label.pack(side=tk.LEFT)
        
        # Article listbox
        self.article_listbox = tk.Listbox(
            article_frame,
            selectmode=tk.SINGLE,
            highlightthickness=0,
            exportselection=False,
            activestyle='none',
            bd=0,
            relief=tk.FLAT,
            bg=Theme.BG_LISTBOX,
            fg=Theme.FG_PRIMARY,
            selectbackground=Theme.SELECT_BG,
            selectforeground=Theme.SELECT_FG,
            font=("Arial", 12),
            height=18
        )
        self.article_listbox.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.article_listbox.bind('<Button-1>', self.on_article_click)
        
        # Splitter
        self.splitter = tk.Frame(stacked_content, height=6, bg=Theme.BG_SPLITTER)
        self.splitter.pack(side=tk.TOP, fill=tk.X)
        self.splitter.configure(cursor="sb_v_double_arrow")
        self.splitter.bind("<Button-1>", self.start_split_drag)
        self.splitter.bind("<B1-Motion>", self.on_split_drag)
        self.splitter.bind("<ButtonRelease-1>", self.stop_split_drag)
        
        # Article content panel
        self.article_content_frame = tk.Frame(stacked_content, bg=Theme.BG_SECONDARY)
        self.article_content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Article title
        self.article_title = ttk.Label(
            self.article_content_frame,
            text="",
            font=("Arial", 14, "bold")
        )
        self.article_title.pack(anchor=tk.W)
        
        # Article metadata
        self.article_meta = ttk.Label(
            self.article_content_frame,
            text="",
            font=("Arial", 10)
        )
        self.article_meta.pack(anchor=tk.W, pady=(5, 10))
        
        # Footer (must pack before content for space reservation)
        self.article_footer = tk.Frame(self.article_content_frame, bg=Theme.BG_FOOTER, height=44)
        self.article_footer.pack(side=tk.BOTTOM, fill=tk.X)
        self.article_footer.pack_propagate(False)
        
        # Open in browser button
        self.open_browser_btn = ttk.Button(
            self.article_footer,
            text="在浏览器中打开 ↗",
            command=self.open_article_in_browser
        )
        self.open_browser_btn.pack(side=tk.RIGHT, padx=10, pady=6)
        
        # Article content
        self.article_content = scrolledtext.ScrolledText(
            self.article_content_frame,
            wrap=tk.WORD,
            width=80,
            height=20,
            font=("Arial", 10),
            bg=Theme.BG_ARTICLE,
            fg=Theme.FG_PRIMARY,
            insertbackground=Theme.FG_PRIMARY,
            highlightthickness=0
        )
        self.article_content.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
    
    def start_split_drag(self, event):
        """Start dragging splitter"""
        self.dragging_splitter = True
        self.drag_start_y = event.y_root
        self.drag_start_height = self.article_list_height
    
    def on_split_drag(self, event):
        """Handle splitter dragging"""
        if not self.dragging_splitter:
            return
        
        delta = event.y_root - self.drag_start_y
        new_height = max(120, min(500, self.drag_start_height + delta))
        self.article_list_height = int(new_height)
        self.article_listbox.master.configure(height=self.article_list_height)
        self.article_listbox.master.pack_propagate(False)
    
    def stop_split_drag(self, event):
        """Stop dragging splitter"""
        self.dragging_splitter = False
    
    def update_subscription_list(self):
        """Update subscription list display"""
        self.subscription_listbox.delete(0, tk.END)
        self.subscription_listbox.insert(tk.END, "全部文章")
        
        for sub in self.subscription_manager.subscriptions:
            self.subscription_listbox.insert(tk.END, sub.title)
    
    def on_subscription_select(self, event):
        """Handle subscription selection"""
        selection = event.widget.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index == 0:  # "All Articles"
            self.current_feed_id = None
        else:
            self.current_feed_id = self.subscription_manager.subscriptions[index - 1].id
        
        self.selected_index = None
        self.load_articles()
    
    def load_articles(self):
        """Load and display articles"""
        self.article_listbox.delete(0, tk.END)
        self.article_content.delete(1.0, tk.END)
        self.article_listbox.insert(tk.END, "正在加载文章...")
        
        def load_thread():
            try:
                self.current_articles = self.subscription_manager.get_articles(self.current_feed_id)
                
                # Update UI
                self.root.after(0, lambda: self.article_listbox.delete(0, tk.END))
                for article in self.current_articles:
                    self.root.after(
                        0,
                        lambda a=article: self.article_listbox.insert(
                            tk.END,
                            f"{a.title} - {a.feed_title}" if not self.current_feed_id else a.title
                        )
                    )
                self.root.after(0, self.update_article_list_display)
            except Exception as e:
                print(f"Error loading articles: {e}")
        
        threading.Thread(target=load_thread, daemon=True).start()
    
    def update_article_list_display(self):
        """Update article list colors based on read/selection status"""
        if not self.article_listbox.size() > 0:
            return
        
        for i in range(len(self.current_articles)):
            article = self.current_articles[i]
            article_id = article.guid or article.title
            is_read = article_id in self.read_articles
            is_selected = self.selected_index == i
            
            # Map status to colors
            if is_selected:
                fg, select_fg = Theme.FG_SELECTED, Theme.FG_SELECTED_MUTED
            elif is_read:
                fg, select_fg = Theme.FG_MUTED, Theme.FG_MUTED
            else:
                fg, select_fg = Theme.FG_PRIMARY, Theme.FG_PRIMARY
            
            self.article_listbox.itemconfig(i, {'fg': fg, 'selectforeground': select_fg})
    
    def on_article_click(self, event):
        """Handle article click"""
        index = self.article_listbox.nearest(event.y)
        
        if 0 <= index < len(self.current_articles):
            article = self.current_articles[index]
            article_id = article.guid or article.title
            self.read_articles.add(article_id)
            
            self.selected_index = index
            self.article_listbox.selection_clear(0, tk.END)
            self.article_listbox.selection_set(index)
            
            self.update_article_list_display()
            self.display_article(article)
    
    def display_article(self, article: Article):
        """Display article content"""
        self.article_title.config(text=article.title)
        self.article_meta.config(
            text=f"{article.author} - {format_date(article.pub_date)}"
        )
        self.article_content.delete(1.0, tk.END)
        self.article_content.insert(tk.END, article.content)
    
    def _get_selected_article_index(self) -> Optional[int]:
        """Get the currently selected article index or None if not selected"""
        current_selection = self.article_listbox.curselection()
        if current_selection:
            return current_selection[0]
        elif self.selected_index is not None:
            return self.selected_index
        return None
    
    def open_article_in_browser(self):
        """Open current article in browser"""
        try:
            index = self._get_selected_article_index()
            if index is None:
                messagebox.showwarning("警告", "请先选择一篇文章")
                return
            
            if 0 <= index < len(self.current_articles):
                article = self.current_articles[index]
                if article.link:
                    webbrowser.open(article.link)
                else:
                    messagebox.showwarning("警告", "未找到文章链接")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开浏览器: {str(e)}")
    
    def add_subscription(self):
        """Show add subscription dialog"""
        def handle_add(url: str):
            try:
                success, message = self.subscription_manager.add_subscription(url)
                if success:
                    messagebox.showinfo("成功", f"订阅添加成功: {message}")
                    self.update_subscription_list()
                    return True
                else:
                    messagebox.showerror("错误", f"添加订阅失败: {message}")
                    return False
            except Exception as e:
                messagebox.showerror("错误", f"添加订阅失败: {str(e)}")
                return False
        
        AddSubscriptionDialog(self.root, handle_add)
    
    def refresh_all(self):
        """Refresh all subscriptions"""
        if self.is_refreshing:
            return
        
        self.is_refreshing = True
        self.refresh_btn.config(state='disabled')
        
        def refresh_thread():
            try:
                self.subscription_manager.refresh_all()
                self.root.after(0, self.load_articles)
            except Exception as e:
                print(f"Error refreshing: {e}")
            finally:
                self.root.after(0, lambda: self.refresh_btn.config(state='normal'))
                self.root.after(0, lambda: setattr(self, 'is_refreshing', False))
        
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def show_about(self):
        """Show about dialog"""
        AboutDialog.show(self.root)
