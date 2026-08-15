import tkinter as tk
from tkinter import ttk, messagebox
import io
import threading
import webbrowser
from datetime import datetime, timedelta
from PIL import Image
from services.subscription_manager import SubscriptionManager
from services.storage_service import StorageService
from services.feed_service import FeedService
from services.translation_service import TranslationService
from ui.dialogs import AddSubscriptionDialog, AboutDialog
from ui.i18n import t
from ui.styles import Theme, configure_styles
from utils.date_utils import format_date
from utils.html_utils import download_image


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

        # 图片自适应缩放状态:嵌入图名 -> (文章, URL);当前显示宽度
        self._embedded_images = {}
        self._image_display_width = None
        self._resize_after_id = None
        
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
        
        ttk.Label(header_frame, text=t("订阅"), font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        
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
        # 图片加载失败占位提示的弱化样式
        self.article_content_text.tag_configure("img_failed", foreground=Theme.FG_MUTED)
        # 全文获取失败等提示的弱化样式
        self.article_content_text.tag_configure("hint", foreground=Theme.FG_MUTED)

        # Scrollbar for article content
        # 注意:滚动条必须先于文本 pack,否则会被挤压成右下角的小方块
        scrollbar = ttk.Scrollbar(bottom_frame, orient=tk.VERTICAL, command=self.article_content_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.article_content_text.pack(fill=tk.BOTH, expand=True)
        self.article_content_text.configure(yscrollcommand=scrollbar.set)

        # 窗口尺寸变化时自适应缩放图片
        self.article_content_text.bind("<Configure>", self._on_content_configure)
        
        # Translate button (packed first so it sits at the far right)
        self.translate_btn = ttk.Button(
            button_frame,
            text=t("翻译"),
            command=self.translate_current_article,
            state=tk.DISABLED
        )
        self.translate_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Open in browser button
        self.open_browser_btn = ttk.Button(
            button_frame,
            text=t("在浏览器中打开"),
            command=self.open_article_in_browser,
            state=tk.DISABLED
        )
        self.open_browser_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Refresh button
        self.refresh_btn = ttk.Button(
            button_frame,
            text=t("刷新订阅"),
            command=self.refresh_subscriptions
        )
        self.refresh_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # About button
        self.about_btn = ttk.Button(
            button_frame,
            text=t("关于"),
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
        self.article_listbox.insert(tk.END, t("正在加载文章..."))

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
            self.article_listbox.insert(tk.END, t("加载失败或无文章，请点击「刷新订阅」重试"))
            return

        for article in articles:
            # 刷新后会重建 Article 对象,用稳定标识恢复本次运行内的已读状态
            article.read = self._article_key(article) in self.read_article_ids
            self.article_listbox.insert(tk.END, self._format_article_label(article))
            self._apply_article_colors(tk.END, article)

    def _format_article_label(self, article):
        """列表条目标签:未读不显示标记,已读显示 [已读] 前缀。"""
        return f"{t('[已读] ') if article.read else ''}{article.title}"

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
            self.translate_btn.config(state=tk.DISABLED, text=t("翻译"))
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
                text=t("已翻译") if article.translated_content else t("翻译")
            )
            self.open_browser_btn.config(state=tk.NORMAL)

            # 后台抓取文章网页:摘要过短则替换正文,并提取图片
            self._maybe_fetch_full_content(article)

    def _render_article(self, article):
        """把文章详情渲染到内容区域(已有译文时显示译文)。

        原文视图支持图文混排:短摘要文章按正文块顺序渲染段落与图片,
        feed 自带长文则渲染原文并在文末追加图片。
        """
        self.article_content_text.config(state=tk.NORMAL)
        self.article_content_text.delete(1.0, tk.END)

        # 清空旧视图的嵌入图记录与显示宽度,重新计算
        self._embedded_images = {}
        self._image_display_width = None

        if article.translated_content:
            # Add article details (translated)
            content = t("标题: {title}\n\n").format(title=article.translated_title or article.title)
            content += t("(原标题: {title})\n\n").format(title=article.title)
            if article.author:
                content += t("作者: {author}\n\n").format(author=article.author)
            content += t("链接: {link}\n\n").format(link=article.link)
            content += t("发布时间: {date}\n\n").format(date=format_date(article.pub_date))

            if article.translated_block_texts:
                # 块级译文:图文按原文位置混排
                content += t("内容(已翻译):\n")
                self.article_content_text.insert(tk.END, content)
                text_iter = iter(article.translated_block_texts)
                for block in article.blocks:
                    if block.get('type') == 'image':
                        self._insert_article_image(article, block['src'])
                    else:
                        self.article_content_text.insert(tk.END, "\n\n" + next(text_iter, ''))
            else:
                # 整文译文:图片追加在译文末尾
                content += t("内容(已翻译):\n") + article.translated_content
                self.article_content_text.insert(tk.END, content)
                image_urls = [b['src'] for b in article.blocks if b.get('type') == 'image']
                image_urls.extend(article.extra_image_urls)
                for url in image_urls:
                    self._insert_article_image(article, url)
        else:
            # Add article details (original)
            header = t("标题: {title}\n\n").format(title=article.title)
            if article.author:
                header += t("作者: {author}\n\n").format(author=article.author)
            header += t("链接: {link}\n\n").format(link=article.link)
            header += t("发布时间: {date}\n\n").format(date=format_date(article.pub_date))
            header += t("内容:\n")
            self.article_content_text.insert(tk.END, header)

            if article.full_text_failed and len(article.content) < 300:
                self.article_content_text.insert(
                    tk.END, t("⚠ 全文获取失败,以下为摘要(重新选中本文会自动重试)\n\n"), ("hint",)
                )

            if article.blocks:
                # 图文块按文档顺序渲染
                for block in article.blocks:
                    if block.get('type') == 'image':
                        self._insert_article_image(article, block['src'])
                    else:
                        self.article_content_text.insert(tk.END, "\n\n" + block['text'])
            else:
                self.article_content_text.insert(tk.END, article.content)
                # feed 自带长文:网页图片追加在文末
                if article.photos is not None:
                    for url in article.extra_image_urls:
                        self._insert_article_image(article, url)

        self.article_content_text.config(state=tk.DISABLED)

    def _render_article_keep_scroll(self, article):
        """重新渲染文章视图,并保持当前滚动位置。

        用于译文替换、全文到达、图片就绪等"原地更新"场景,
        避免视图重建导致滚动位置跳回文章开头。
        """
        try:
            frac = self.article_content_text.yview()[0]
        except tk.TclError:
            frac = 0.0
        self._render_article(article)
        self.article_content_text.yview_moveto(max(0.0, min(1.0, frac)))

    def _insert_article_image(self, article, url):
        """在内容区插入一张图片(按当前可视宽度缩放)。

        未下载完成时先留空,失败时显示占位提示。
        """
        self.article_content_text.insert(tk.END, "\n")

        if url in (article.pil_images or {}):
            if self._image_display_width is None:
                self._image_display_width = self._display_image_width()
            photo = self._make_photo(article, url, self._image_display_width)
            if photo:
                name = self.article_content_text.image_create(tk.END, image=photo)
                self._embedded_images[name] = (article, url)
        elif article.photos is not None:
            self.article_content_text.insert(tk.END, t("[图片加载失败]"), ("img_failed",))

        self.article_content_text.insert(tk.END, "\n")

    def _display_image_width(self):
        """当前内容区的可视宽度(图片显示宽度按它计算)。"""
        w = self.article_content_text.winfo_width()
        if not w or w < 100:
            return 700  # 布局尚未完成时的兜底宽度
        return max(100, w - 10)

    def _make_photo(self, article, url, width):
        """把原始 PIL 图片按显示宽度等比缩放为 PhotoImage 并缓存。"""
        pil = article.pil_images.get(url)
        if pil is None:
            return None
        if pil.width > width:
            ratio = width / pil.width
            img = pil.resize((width, max(1, int(pil.height * ratio))), Image.LANCZOS)
        else:
            img = pil
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        photo = tk.PhotoImage(data=buf.getvalue())
        article.photos[url] = photo
        return photo

    def _on_content_configure(self, event):
        """内容区尺寸变化时防抖,稍后按新宽度重排图片。"""
        if self._resize_after_id:
            self.root.after_cancel(self._resize_after_id)
        self._resize_after_id = self.root.after(200, self._refit_images)

    def _refit_images(self):
        """按当前可视宽度重新缩放所有已嵌入图片(原位替换,不打断滚动)。"""
        self._resize_after_id = None
        if not self._embedded_images:
            return
        width = self._display_image_width()
        if width == self._image_display_width:
            return
        for name, (article, url) in self._embedded_images.items():
            try:
                photo = self._make_photo(article, url, width)
                if photo:
                    self.article_content_text.image_configure(name, image=photo)
            except Exception as e:
                print(f"Error refitting image {url}: {e}")
        self._image_display_width = width

    def translate_current_article(self):
        """把当前文章翻译成操作系统语言(语言相同则提示无需翻译)。

        优先块级翻译(逐块译文,图片保持在原文位置);分隔符丢失等
        情况下回退到整文翻译(图片追加文末)。
        """
        article = self.viewed_article
        if not article:
            return

        self.translate_btn.config(state=tk.DISABLED, text=t("翻译中..."))
        target = TranslationService.get_os_language()

        def worker():
            try:
                sample = article.title + "\n" + (article.content or '')
                if not TranslationService.needs_translation(sample, target):
                    return None  # 与系统语言相同,无需翻译

                # 块级翻译:保持图文位置
                if article.blocks:
                    texts = [
                        b.get('text', '') for b in article.blocks if b.get('type') == 'text'
                    ]
                    translated_texts = TranslationService.translate_blocks(texts, target)
                    if translated_texts is not None:
                        translated_title = TranslationService.translate_blocks(
                            [article.title], target
                        )
                        title = translated_title[0] if translated_title else article.title
                        return (title, "\n\n".join(translated_texts), translated_texts)

                # 回退:整文翻译
                result = TranslationService.translate_article(article.title, article.content, target)
                if result is None:
                    return None
                return (result[0], result[1], None)
            except Exception as e:
                print(f"Error translating article: {e}")
                return e  # 用异常对象作为失败标记

        def on_done(result):
            self.translate_btn.config(state=tk.NORMAL)
            if isinstance(result, Exception):
                self.translate_btn.config(text=t("翻译"))
                messagebox.showerror(t("翻译失败"), t("翻译时出错: {error}").format(error=result))
                return
            if result is None:
                self.translate_btn.config(text=t("翻译"))
                messagebox.showinfo(
                    t("翻译"),
                    t("文章语言与系统语言({target})相同，无需翻译").format(target=target),
                )
                return
            article.translated_title, article.translated_content, article.translated_block_texts = result
            self.translate_btn.config(text=t("已翻译"))
            if self.viewed_article is article:
                self._render_article_keep_scroll(article)

        self._run_in_background(worker, on_done)

    MAX_ARTICLE_IMAGES = 12  # 每篇文章最多下载的图片数

    def _maybe_fetch_full_content(self, article):
        """打开文章时后台抓取原网页。

        网页正文比当前内容更长时替换(覆盖短摘要与中长摘要),并按图文块渲染;
        feed 自带全文更长时保留原文,网页图片追加在文末;
        抓取失败时不标记完成,下次选中该文章会重试。
        """
        if not article.link or getattr(article, 'page_fetched', False):
            return

        def worker():
            try:
                return FeedService.fetch_full_content(article.link)
            except Exception as e:
                print(f"Error fetching article page: {e}")
                return "", [], {}

        def on_done(result):
            text, blocks, meta = result

            if not text and not blocks:
                # 抓取失败:标记失败并保留重试机会
                article.full_text_failed = True
                if self.viewed_article is article:
                    self._render_article_keep_scroll(article)
                return

            article.page_fetched = True
            article.full_text_failed = False

            # 用提取算法产出的元数据补全 RSS 缺失的作者/日期/标题
            if meta.get('author'):
                article.author = article.author or meta['author']
            if meta.get('date'):
                article.pub_date = article.pub_date or meta['date']
            if meta.get('title') and not article.title:
                article.title = meta['title']
            if meta.get('html'):
                article.clean_html = meta['html']

            should_replace = text and (
                # 摘要级内容(<500 字):网页正文更长就替换
                (len(article.content) < 500 and len(text) > len(article.content))
                # 中长内容:网页正文显著更长(1.5 倍以上)才替换,避免覆盖 feed 自带全文
                or len(text) > len(article.content) * 1.5
            )
            if should_replace:
                # 网页正文替换,并按图文块渲染
                article.content = text
                article.blocks = blocks
                # 原文已更新,基于旧摘要的译文作废
                article.translated_title = ""
                article.translated_content = ""
                article.translated_block_texts = None
            else:
                # feed 自带全文:保留原文,文末仅追加题图。
                # 容器内嵌图可能混入其它文章的推广图(如 newsletter 页的
                # 相关故事配图),因此不追加。
                article.blocks = []
                if meta.get('image'):
                    article.extra_image_urls = [meta['image']]
                else:
                    article.extra_image_urls = [
                        b['src'] for b in blocks if b.get('type') == 'image'
                    ]
            self._download_article_images(article)
            # 只有用户仍停留在该文章时才刷新视图
            if self.viewed_article is article:
                self._render_article_keep_scroll(article)
                self.translate_btn.config(text=t("翻译"))

        self._run_in_background(worker, on_done)

    def _download_article_images(self, article):
        """后台下载文章图片,主线程解码为 PhotoImage 后刷新视图。"""
        urls = [b['src'] for b in article.blocks if b.get('type') == 'image']
        urls.extend(article.extra_image_urls)

        # 去重并限量
        seen, unique = set(), []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)
        unique = unique[:self.MAX_ARTICLE_IMAGES]
        if not unique:
            return

        def worker():
            return [(u, download_image(u)) for u in unique]

        def on_done(pairs):
            article.photos = {}
            article.pil_images = {}
            for url, data in pairs:
                if not data:
                    continue
                try:
                    img = Image.open(io.BytesIO(data))
                    img.load()
                    # 原始图过宽时先压到 2000px 以内,节省内存
                    if img.width > 2000:
                        ratio = 2000 / img.width
                        img = img.resize((2000, max(1, int(img.height * ratio))), Image.LANCZOS)
                    article.pil_images[url] = img
                except Exception as e:
                    print(f"Error decoding image {url}: {e}")
            if self.viewed_article is article:
                self._render_article_keep_scroll(article)

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
                messagebox.showerror(
                    t("错误"), t("无法添加订阅: {message}").format(message=message)
                )
                return False

        except Exception as e:
            messagebox.showerror(t("错误"), t("添加订阅时出错: {error}").format(error=str(e)))
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
                    messagebox.showerror(t("错误"), t("无法打开链接: {error}").format(error=str(e)))
    
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

            messagebox.showinfo(t("成功"), t("订阅刷新完成"))
        except Exception as e:
            messagebox.showerror(t("错误"), t("刷新订阅时出错: {error}").format(error=str(e)))
    
    def show_about(self):
        """显示关于对话框。"""
        AboutDialog.show(self.root)