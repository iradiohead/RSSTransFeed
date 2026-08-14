import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
from datetime import datetime, timedelta
from services.subscription_manager import SubscriptionManager
from services.storage_service import StorageService
from services.feed_service import FeedService
from services.translation_service import TranslationService
from ui.dialogs import AddSubscriptionDialog, AboutDialog
from ui.styles import Theme, configure_styles
from utils.date_utils import format_date


class RSSReaderApp:
    """主应用程序类，负责管理整个 RSS 阅读器界面和交互逻辑。
    
    这个类创建并管理 Tkinter 主窗口，包含左侧订阅列表、右侧文章列表和文章内容显示区域。
    它处理用户的所有交互事件，如添加订阅、选择订阅、查看文章等。
    """
    
    def __init__(self, root):
        """初始化 RSS 阅读器应用。
        
        Args:
            root: Tkinter 主窗口对象
        """
        self.root = root
        self.root.title("RSSTransFeed")
        self.root.geometry("1200x700")
        self.root.minsize(800, 600)
        
        # Initialize storage service and subscription manager
        self.storage_service = StorageService()
        self.subscription_manager = SubscriptionManager(self.storage_service)

        # Current feed/article state
        self.current_subscription_id = None
        self.current_articles = []
        self.viewed_article = None
        # 已读文章标识(key -> 阅读时间),持久化到 read_articles.json,重启后仍生效
        self.read_article_ids = self._prune_read_articles(
            self.storage_service.load_read_articles()
        )

        # Splitter drag state
        self.article_list_height = 260
        self.dragging_splitter = False
        
        # Configure styles
        self.style = configure_styles()
        
        # Set window background to match theme
        self.root.configure(bg=Theme.BG_PRIMARY)
        
        # Create UI components
        self.create_widgets()
        
        # Load subscriptions
        self.load_subscriptions()
        
        # Load articles for the first subscription
        if self.subscription_manager.subscriptions:
            self.load_articles_for_subscription(self.subscription_manager.subscriptions[0])
    
    def create_widgets(self):
        """创建并布局所有 UI 组件。"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a horizontal splitter (using frames to simulate split)
        self.splitter_frame = ttk.Frame(main_frame)
        self.splitter_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left sidebar (subscriptions)
        self.sidebar_frame = ttk.Frame(self.splitter_frame, width=250)
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.sidebar_frame.pack_propagate(False)  # Prevent frame from shrinking
        
        # Right content area
        self.content_frame = ttk.Frame(self.splitter_frame)
        self.content_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Create sidebar widgets
        self.create_sidebar_widgets()
        
        # Create content widgets
        self.create_content_widgets()
    
    def create_sidebar_widgets(self):
        """创建侧边栏组件（订阅列表）。"""
        # Sidebar header
        header_frame = ttk.Frame(self.sidebar_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(header_frame, text="订阅", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
        # Add subscription button
        add_btn = ttk.Button(header_frame, text="+", width=2, command=self.add_subscription)
        add_btn.pack(side=tk.RIGHT)
        
        # Subscription listbox
        self.subscription_listbox = tk.Listbox(
            self.sidebar_frame,
            selectmode=tk.SINGLE,
            bg=Theme.BG_LISTBOX,
            fg=Theme.FG_PRIMARY,
            selectbackground=Theme.SELECT_BG,
            selectforeground=Theme.SELECT_FG,
            font=("Arial", 10),
            borderwidth=0,
            highlightthickness=0
        )
        self.subscription_listbox.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Bind selection event
        self.subscription_listbox.bind('<<ListboxSelect>>', self.on_subscription_selected)
    
    def create_content_widgets(self):
        """创建内容区域组件（文章列表和文章内容）。"""
        # Top frame for article list (fixed height, resizable via splitter)
        self.article_list_frame = ttk.Frame(self.content_frame, height=self.article_list_height)
        self.article_list_frame.pack(side=tk.TOP, fill=tk.X, expand=False)
        self.article_list_frame.pack_propagate(False)  # Keep the fixed height

        # Article listbox
        self.article_listbox = tk.Listbox(
            self.article_list_frame,
            selectmode=tk.SINGLE,
            exportselection=False,
            bg=Theme.BG_LISTBOX,
            fg=Theme.FG_PRIMARY,
            selectbackground=Theme.SELECT_BG,
            selectforeground=Theme.SELECT_FG,
            font=("Arial", 10),
            borderwidth=0,
            highlightthickness=0
        )
        self.article_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Bind selection event
        self.article_listbox.bind('<<ListboxSelect>>', self.on_article_selected)

        # Splitter between article list and content (draggable)
        self.splitter = tk.Frame(self.content_frame, height=6, bg=Theme.BG_SPLITTER)
        self.splitter.pack(side=tk.TOP, fill=tk.X)
        self.splitter.configure(cursor="sb_v_double_arrow")
        self.splitter.bind("<Button-1>", self.start_split_drag)
        self.splitter.bind("<B1-Motion>", self.on_split_drag)
        self.splitter.bind("<ButtonRelease-1>", self.stop_split_drag)

        # Bottom frame for buttons (packed before the expanding content frame
        # so it keeps its requested height)
        button_frame = ttk.Frame(self.content_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

        # Bottom frame for article content
        bottom_frame = ttk.Frame(self.content_frame)
        bottom_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(5, 0))
        
        # Article content text widget
        self.article_content_text = tk.Text(
            bottom_frame,
            bg=Theme.BG_ARTICLE,
            fg=Theme.FG_PRIMARY,
            font=("Arial", 10),
            borderwidth=0,
            highlightthickness=0,
            wrap=tk.WORD,
            state=tk.DISABLED
        )

        # Scrollbar for article content
        # 注意:滚动条必须先于文本 pack,否则会被挤压成右下角的小方块
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=self.article_content_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.article_content_text.pack(fill=tk.BOTH, expand=True)
        self.article_content_text.configure(yscrollcommand=scrollbar.set)
        
        # Translate button (packed first so it sits at the far right)
        self.translate_btn = ttk.Button(
            button_frame,
            text="翻译",
            command=self.translate_current_article,
            state=tk.DISABLED
        )
        self.translate_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Open in browser button
        self.open_browser_btn = ttk.Button(
            button_frame,
            text="在浏览器中打开",
            command=self.open_article_in_browser,
            state=tk.DISABLED
        )
        self.open_browser_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Refresh button
        self.refresh_btn = ttk.Button(
            button_frame,
            text="刷新订阅",
            command=self.refresh_subscriptions
        )
        self.refresh_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # About button
        self.about_btn = ttk.Button(
            button_frame,
            text="关于",
            command=self.show_about
        )
        self.about_btn.pack(side=tk.RIGHT, padx=(5, 0))
    
    def load_subscriptions(self):
        """从存储中加载订阅列表并显示在侧边栏。"""
        self.subscription_listbox.delete(0, tk.END)
        
        for subscription in self.subscription_manager.subscriptions:
            self.subscription_listbox.insert(tk.END, subscription.title)
    
    def _run_in_background(self, worker, on_done):
        """在后台线程执行 worker，完成后回到主线程调用 on_done。

        每次调用使用闭包内独立的槽位传递结果，互不覆盖；
        主线程用 after 轮询，避免跨线程直接操作 Tk 组件。
        """
        slot = {'done': False, 'value': None}

        def run():
            slot['value'] = worker()
            slot['done'] = True

        threading.Thread(target=run, daemon=True).start()

        def poll():
            if slot['done']:
                on_done(slot['value'])
            else:
                self.root.after(100, poll)

        self.root.after(100, poll)

    def load_articles_for_subscription(self, subscription):
        """为指定订阅加载文章列表。

        文章抓取涉及网络请求，放在后台线程执行，避免阻塞界面。

        Args:
            subscription: 要加载文章的订阅对象
        """
        self.current_subscription_id = subscription.id
        self.current_articles = []
        self.article_listbox.delete(0, tk.END)
        self.article_listbox.insert(tk.END, "正在加载文章...")

        def worker():
            try:
                return self.subscription_manager.get_articles(subscription.id)
            except Exception as e:
                print(f"Error loading articles: {e}")
                return []

        self._run_in_background(
            worker,
            lambda articles: self._update_article_list(subscription.id, articles)
        )

    def _update_article_list(self, subscription_id, articles):
        """把后台加载完成的文章渲染到列表。

        若加载期间用户已切换到其它订阅，则丢弃过期结果。
        """
        if self.current_subscription_id != subscription_id:
            return

        self.current_articles = articles
        self.article_listbox.delete(0, tk.END)

        # 重建列表会清空文章选择,打开/翻译按钮随之禁用
        self.open_browser_btn.config(state=tk.DISABLED)

        if not articles:
            # 拉取失败或订阅暂无文章时给出明确提示
            self.article_listbox.insert(tk.END, "加载失败或无文章，请点击「刷新订阅」重试")
            return

        for article in articles:
            # 刷新后会重建 Article 对象,用稳定标识恢复本次运行内的已读状态
            article.read = self._article_key(article) in self.read_article_ids
            self.article_listbox.insert(tk.END, self._format_article_label(article))
            self._apply_article_colors(tk.END, article)

    def _format_article_label(self, article):
        """列表条目标签:未读不显示标记,已读显示 [已读] 前缀。"""
        return f"{'[已读] ' if article.read else ''}{article.title}"

    def _apply_article_colors(self, index, article):
        """已读文章用更灰的弱化色,未读用主文字色。"""
        fg = Theme.FG_MUTED if article.read else Theme.FG_PRIMARY
        self.article_listbox.itemconfig(index, fg=fg, selectforeground=fg)

    def _article_key(self, article):
        """返回文章的稳定标识(guid → 链接 → 标题),用于跟踪已读状态。"""
        return article.guid or article.link or article.title

    @staticmethod
    def _prune_read_articles(data, max_age_days=90, max_entries=5000):
        """清理过久或过多的已读记录,防止 read_articles.json 无限膨胀。"""
        cutoff = (datetime.now() - timedelta(days=max_age_days)).isoformat()
        pruned = {
            key: ts for key, ts in data.items()
            if isinstance(ts, str) and ts >= cutoff
        }
        if len(pruned) > max_entries:
            # 按阅读时间保留最新的 max_entries 条
            newest = sorted(pruned.items(), key=lambda kv: kv[1], reverse=True)[:max_entries]
            pruned = dict(newest)
        return pruned
    
    def start_split_drag(self, event):
        """开始拖拽分割线。"""
        self.dragging_splitter = True
        self.drag_start_y = event.y_root
        self.drag_start_height = self.article_list_height

    def on_split_drag(self, event):
        """处理分割线拖拽，动态调整文章列表高度。"""
        if not self.dragging_splitter:
            return

        delta = event.y_root - self.drag_start_y
        new_height = max(120, min(500, self.drag_start_height + delta))
        self.article_list_height = int(new_height)
        self.article_list_frame.configure(height=self.article_list_height)

    def stop_split_drag(self, event):
        """结束分割线拖拽。"""
        self.dragging_splitter = False

    def on_subscription_selected(self, event):
        """处理订阅选择事件。"""
        selection = self.subscription_listbox.curselection()
        if selection:
            index = selection[0]
            subscription = self.subscription_manager.subscriptions[index]
            self.load_articles_for_subscription(subscription)
            
            # Enable the article list and clear content
            self.viewed_article = None
            self.translate_btn.config(state=tk.DISABLED, text="翻译")
            self.open_browser_btn.config(state=tk.DISABLED)
            self.article_content_text.config(state=tk.NORMAL)
            self.article_content_text.delete(1.0, tk.END)
            self.article_content_text.config(state=tk.DISABLED)
    
    def on_article_selected(self, event):
        """处理文章选择事件。"""
        selection = self.article_listbox.curselection()
        if selection and self.current_articles:
            index = selection[0]
            if index >= len(self.current_articles):
                return

            article = self.current_articles[index]

            # Mark as read and update the entry in place
            if not article.read:
                article.read = True
                self.read_article_ids[self._article_key(article)] = datetime.now().isoformat()
                self.storage_service.save_read_articles(self.read_article_ids)
                self.article_listbox.delete(index)
                self.article_listbox.insert(index, self._format_article_label(article))
                self._apply_article_colors(index, article)
                # selection_set 不会自动清除旧选择,先显式清空再选中
                self.article_listbox.selection_clear(0, tk.END)
                self.article_listbox.selection_set(index)

            # Display article content
            self.viewed_article = article
            self._render_article(article)
            self.translate_btn.config(
                state=tk.NORMAL,
                text="已翻译" if article.translated_content else "翻译"
            )
            self.open_browser_btn.config(state=tk.NORMAL)

            # 摘要过短时后台抓取网页全文，完成后自动刷新详情
            self._maybe_fetch_full_text(article)

    def _render_article(self, article):
        """把文章详情渲染到内容区域(已有译文时显示译文)。"""
        self.article_content_text.config(state=tk.NORMAL)
        self.article_content_text.delete(1.0, tk.END)

        if article.translated_content:
            # Add article details (translated)
            content = f"标题: {article.translated_title or article.title}\n\n"
            content += f"(原标题: {article.title})\n\n"
            content += f"链接: {article.link}\n\n"
            content += f"发布时间: {format_date(article.pub_date)}\n\n"
            content += f"内容(已翻译):\n{article.translated_content}"
        else:
            # Add article details (original)
            content = f"标题: {article.title}\n\n"
            content += f"链接: {article.link}\n\n"
            content += f"发布时间: {format_date(article.pub_date)}\n\n"
            content += f"内容:\n{article.content}"

        self.article_content_text.insert(tk.END, content)
        self.article_content_text.config(state=tk.DISABLED)

    def translate_current_article(self):
        """把当前文章翻译成操作系统语言(语言相同则提示无需翻译)。"""
        article = self.viewed_article
        if not article:
            return

        self.translate_btn.config(state=tk.DISABLED, text="翻译中...")
        target = TranslationService.get_os_language()

        def worker():
            try:
                return TranslationService.translate_article(article.title, article.content, target)
            except Exception as e:
                print(f"Error translating article: {e}")
                return e  # 用异常对象作为失败标记

        def on_done(result):
            self.translate_btn.config(state=tk.NORMAL)
            if isinstance(result, Exception):
                self.translate_btn.config(text="翻译")
                messagebox.showerror("翻译失败", f"翻译时出错: {result}")
                return
            if result is None:
                self.translate_btn.config(text="翻译")
                messagebox.showinfo("翻译", f"文章语言与系统语言({target})相同，无需翻译")
                return
            article.translated_title, article.translated_content = result
            self.translate_btn.config(text="已翻译")
            if self.viewed_article is article:
                self._render_article(article)

        self._run_in_background(worker, on_done)

    def _maybe_fetch_full_text(self, article):
        """当 RSS 摘要过短时，后台抓取网页全文补全详情。"""
        if not article.link or len(article.content) >= 300:
            return
        if getattr(article, 'full_text_fetched', False):
            return

        def worker():
            try:
                return FeedService.fetch_full_text(article.link)
            except Exception as e:
                print(f"Error fetching full text: {e}")
                return ""

        def on_done(text):
            article.full_text_fetched = True
            if text:
                article.content = text
                # 原文已更新,基于旧摘要的译文作废
                article.translated_title = ""
                article.translated_content = ""
                # 只有用户仍停留在该文章时才刷新视图
                if self.viewed_article is article:
                    self._render_article(article)
                    self.translate_btn.config(text="翻译")

        self._run_in_background(worker, on_done)
    
    def add_subscription(self):
        """添加新订阅。"""
        dialog = AddSubscriptionDialog(self.root, on_add_callback=self.handle_add_subscription)
        self.root.wait_window(dialog.dialog)
    
    def handle_add_subscription(self, url):
        """处理添加订阅的回调。
        
        Args:
            url: 用户输入的 RSS 地址
            
        Returns:
            bool: 添加是否成功
        """
        try:
            # Add subscription using manager (returns (success, message))
            success, message = self.subscription_manager.add_subscription(url)

            if success:
                # Reload subscriptions list
                self.load_subscriptions()

                # If this is the first subscription, load its articles
                if len(self.subscription_manager.subscriptions) == 1:
                    self.load_articles_for_subscription(self.subscription_manager.subscriptions[0])

                return True
            else:
                messagebox.showerror("错误", f"无法添加订阅: {message}")
                return False

        except Exception as e:
            messagebox.showerror("错误", f"添加订阅时出错: {str(e)}")
            return False
    
    def open_article_in_browser(self):
        """在浏览器中打开当前选中的文章。"""
        current_article_index = self.article_listbox.curselection()

        if current_article_index and self.current_articles:
            index = current_article_index[0]
            if index < len(self.current_articles):
                article = self.current_articles[index]

                try:
                    webbrowser.open(article.link)
                except Exception as e:
                    messagebox.showerror("错误", f"无法打开链接: {str(e)}")
    
    def refresh_subscriptions(self):
        """刷新所有订阅。"""
        try:
            # 记住当前选中的订阅（load_subscriptions 会清空列表选择，必须先取）
            selection = self.subscription_listbox.curselection()
            current_index = selection[0] if selection else 0

            self.subscription_manager.refresh_all_subscriptions()
            # Reload subscriptions
            self.load_subscriptions()

            # 刷新后重新加载刷新前正在查看的订阅
            if self.subscription_manager.subscriptions:
                current_index = min(current_index, len(self.subscription_manager.subscriptions) - 1)
                self.subscription_listbox.selection_clear(0, tk.END)
                self.subscription_listbox.selection_set(current_index)
                self.load_articles_for_subscription(
                    self.subscription_manager.subscriptions[current_index]
                )

            messagebox.showinfo("成功", "订阅刷新完成")
        except Exception as e:
            messagebox.showerror("错误", f"刷新订阅时出错: {str(e)}")
    
    def show_about(self):
        """显示关于对话框。"""
        AboutDialog.show(self.root)