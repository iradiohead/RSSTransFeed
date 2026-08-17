"""Main PySide6 window."""

from __future__ import annotations

import webbrowser
from collections.abc import Callable

from langdetect.lang_detect_exception import LangDetectException
from PySide6.QtCore import QSettings, Qt, QThreadPool, QUrl
from PySide6.QtGui import QAction, QColor, QDesktopServices, QImage
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from models import Article, ArticleBlock, Subscription, TranslationResult
from services import (
    FeedService,
    ReadState,
    StorageService,
    SubscriptionManager,
    TranslationService,
    download_image,
    translate_article_with_fallback,
)
from services.baidu_translation_service import BAIDU_APP_ID_KEY, BAIDU_SECRET_KEY
from ui.article_browser import ArticleBrowser
from ui.dialogs import (
    AddSubscriptionDialog,
    TranslationSettingsDialog,
    show_about,
)
from ui.i18n import t
from ui.theme import COLORS
from ui.workers import Worker


class MainWindow(QMainWindow):
    """Coordinate the desktop UI, background work, and application services."""

    MAX_IMAGES = 12

    def __init__(self, storage: StorageService):
        """Initialize application state, build widgets, and load the first feed."""
        super().__init__()
        self.manager = SubscriptionManager(storage)
        self.thread_pool = QThreadPool.globalInstance()
        self._workers: set[Worker] = set()
        self._load_generation = 0
        self._translation_generation = 0
        self._closing = False
        self.current_subscription_id: str | None = None
        self.current_articles: list[Article] = []
        self.viewed_article: Article | None = None
        self._pending_article_selection: tuple[str | None, str] | None = None
        self.read_state = ReadState(storage)
        self.settings = QSettings("RSSTransFeed", "RSSTransFeed")
        self.setWindowTitle("RSSTransFeed")
        self.resize(1200, 760)
        self.setMinimumSize(820, 600)
        self._build_ui()
        self._restore_layout()
        initial_id = (
            self.manager.subscriptions[0].id
            if self.manager.subscriptions
            else None
        )
        self._populate_subscriptions(initial_id)

    def _build_ui(self) -> None:
        """Assemble the main split view and status area."""
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(10, 10, 10, 6)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(self._build_sidebar())
        self.main_splitter.addWidget(self._build_content_panel())
        root_layout.addWidget(self.main_splitter, 1)

        self.status_label = QLabel()
        self.status_label.setStyleSheet(
            f"color: {COLORS['muted']}; padding: 2px 4px;"
        )
        root_layout.addWidget(self.status_label)
        self.setCentralWidget(root)

    def _build_sidebar(self) -> QWidget:
        """Create the subscription list and its add/remove controls."""
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 5, 0)
        header = QHBoxLayout()
        title = QLabel(t("订阅"))
        title.setStyleSheet("font-size: 15px; font-weight: 600;")
        self.add_button = QPushButton("+")
        self.add_button.setFixedWidth(36)
        self.add_button.setToolTip(t("添加订阅"))
        self.add_button.clicked.connect(self._show_add_dialog)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.add_button)
        sidebar_layout.addLayout(header)

        self.subscription_list = QListWidget()
        self.subscription_list.setContextMenuPolicy(
            Qt.ContextMenuPolicy.ActionsContextMenu
        )
        remove_action = QAction(t("删除订阅"), self.subscription_list)
        remove_action.triggered.connect(self._remove_current_subscription)
        self.subscription_list.addAction(remove_action)
        self.subscription_list.currentRowChanged.connect(self._subscription_changed)
        sidebar_layout.addWidget(self.subscription_list)
        return sidebar

    def _build_content_panel(self) -> QWidget:
        """Create the article list, reader, and action-button panel."""
        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setChildrenCollapsible(False)
        self.article_list = QListWidget()
        self.article_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.article_list.currentRowChanged.connect(self._article_changed)
        self.content_splitter.addWidget(self.article_list)

        article_panel = QWidget()
        article_layout = QVBoxLayout(article_panel)
        article_layout.setContentsMargins(0, 4, 0, 0)
        self.article_view = ArticleBrowser()
        article_layout.addWidget(self.article_view, 1)
        article_layout.addLayout(self._build_action_bar())
        self.content_splitter.addWidget(article_panel)
        return self.content_splitter

    def _build_action_bar(self) -> QHBoxLayout:
        """Create and connect the reader's persistent action buttons."""
        layout = QHBoxLayout()
        layout.addStretch()
        self.about_button = QPushButton(t("关于"))
        self.refresh_button = QPushButton(t("刷新"))
        self.open_button = QPushButton(t("浏览器打开"))
        self.translation_settings_button = QPushButton(t("翻译设置"))
        self.translate_button = QPushButton(t("翻译"))
        self.open_button.setEnabled(False)
        self.translate_button.setEnabled(False)
        self.about_button.clicked.connect(lambda: show_about(self))
        self.refresh_button.clicked.connect(self._refresh)
        self.open_button.clicked.connect(self._open_article)
        self.translation_settings_button.clicked.connect(
            self._show_translation_settings
        )
        self.translate_button.clicked.connect(self._translate_article)
        for button in (
            self.about_button,
            self.refresh_button,
            self.open_button,
            self.translation_settings_button,
            self.translate_button,
        ):
            layout.addWidget(button)
        return layout

    def _restore_layout(self) -> None:
        """Restore splitter positions from QSettings with safe integer conversion."""
        def sizes(key: str, default: list[int]) -> list[int]:
            """Read one stored splitter-size list or return its default."""
            value = self.settings.value(key)
            try:
                return [int(item) for item in value] if value else default
            except (TypeError, ValueError):
                return default

        self.main_splitter.setSizes(sizes("horizontal_splitter", [250, 950]))
        self.content_splitter.setSizes(sizes("vertical_splitter", [260, 440]))

    def closeEvent(self, event) -> None:
        """Disconnect pending workers and save splitter positions before closing."""
        self._closing = True
        for worker in self._workers:
            for signal in (
                worker.signals.result,
                worker.signals.error,
                worker.signals.finished,
            ):
                try:
                    signal.disconnect()
                except RuntimeError:
                    pass
        self._workers.clear()
        self.settings.setValue("horizontal_splitter", self.main_splitter.sizes())
        self.settings.setValue("vertical_splitter", self.content_splitter.sizes())
        super().closeEvent(event)

    def _run(
        self,
        function: Callable[[], object],
        on_result: Callable[[object], None],
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        """Execute a callable in QThreadPool and marshal callbacks to the GUI thread."""
        if self._closing:
            return
        worker = Worker(function)
        self._workers.add(worker)
        queued = Qt.ConnectionType.QueuedConnection
        worker.signals.result.connect(on_result, queued)
        if on_error:
            worker.signals.error.connect(on_error, queued)
        else:
            worker.signals.error.connect(self._show_worker_error, queued)
        worker.signals.finished.connect(
            lambda task=worker: self._workers.discard(task), queued
        )
        self.thread_pool.start(worker)

    def _show_worker_error(self, details: str) -> None:
        """Show the final traceback line in both status text and an error dialog."""
        if self._closing:
            return
        message = details.strip().splitlines()[-1] if details.strip() else "Unknown error"
        self.status_label.setText(message)
        QMessageBox.critical(self, t("错误"), message)

    def _populate_subscriptions(self, selected_id: str | None = None) -> None:
        """Rebuild the sidebar and restore the requested subscription selection."""
        self.subscription_list.blockSignals(True)
        self.subscription_list.clear()
        all_item = QListWidgetItem(t("全部文章"))
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self.subscription_list.addItem(all_item)
        selected_row = 0
        for row, subscription in enumerate(self.manager.subscriptions, start=1):
            item = QListWidgetItem(subscription.title)
            item.setData(Qt.ItemDataRole.UserRole, subscription.id)
            item.setToolTip(subscription.url)
            self.subscription_list.addItem(item)
            if subscription.id == selected_id:
                selected_row = row
        self.subscription_list.blockSignals(False)
        self.subscription_list.setCurrentRow(selected_row)

    def _subscription_changed(self, row: int) -> None:
        """Reset article state and asynchronously load the selected subscription."""
        item = self.subscription_list.item(row)
        if item is None:
            return
        subscription_id = item.data(Qt.ItemDataRole.UserRole)
        if (
            self._pending_article_selection
            and self._pending_article_selection[0] != subscription_id
        ):
            self._pending_article_selection = None
        self.current_subscription_id = subscription_id
        self.viewed_article = None
        self._translation_generation += 1
        self.current_articles = []
        self.article_view.reset()
        self.open_button.setEnabled(False)
        self.translate_button.setEnabled(False)
        self.article_list.clear()
        self.article_list.addItem(t("正在加载文章…"))
        self._load_generation += 1
        generation = self._load_generation
        self.status_label.setText(t("正在加载文章…"))
        self._run(
            lambda: self.manager.get_articles(subscription_id),
            lambda articles, token=generation: self._articles_loaded(token, articles),
            lambda error, token=generation: self._articles_failed(token, error),
        )

    def _articles_loaded(self, generation: int, articles: list[Article]) -> None:
        """Display a completed article result unless it belongs to an old selection."""
        if generation != self._load_generation:
            return
        self.current_articles = articles
        self.article_list.clear()
        for index, article in enumerate(articles):
            article.read = self.read_state.contains(article)
            item = QListWidgetItem(self._article_label(article))
            item.setData(Qt.ItemDataRole.UserRole, index)
            self._style_article_item(item, article)
            self.article_list.addItem(item)
        if not articles:
            self.article_list.addItem(t("加载失败或暂无文章"))
        self.status_label.setText(f"{len(articles)} articles")
        self._restore_pending_article_selection()

    def _restore_pending_article_selection(self) -> None:
        """Reselect the same article after a refresh rebuilds the article list."""
        pending = self._pending_article_selection
        self._pending_article_selection = None
        if pending is None or pending[0] != self.current_subscription_id:
            return
        article_key = pending[1]
        row = next(
            (
                index
                for index, article in enumerate(self.current_articles)
                if article.key == article_key
            ),
            None,
        )
        if row is not None:
            self.article_list.setCurrentRow(row)

    def _articles_failed(self, generation: int, details: str) -> None:
        """Display a load failure only when it belongs to the current selection."""
        if generation != self._load_generation:
            return
        self._pending_article_selection = None
        self.current_articles = []
        self.article_list.clear()
        self.article_list.addItem(t("加载失败或暂无文章"))
        self._show_worker_error(details)

    def _article_label(self, article: Article) -> str:
        """Build a list label with read state and source in the aggregate view."""
        read = t("[已读] ") if article.read else ""
        source = (
            f"[{article.feed_title}] "
            if self.current_subscription_id is None and article.feed_title
            else ""
        )
        return f"{read}{source}{article.title}"

    @staticmethod
    def _style_article_item(item: QListWidgetItem, article: Article) -> None:
        """Use muted text for read articles and normal text for unread articles."""
        item.setForeground(QColor(COLORS["muted"] if article.read else COLORS["text"]))

    def _article_changed(self, row: int) -> None:
        """Mark the selected article read, render it, and request its full content."""
        item = self.article_list.item(row)
        if item is None:
            return
        index = item.data(Qt.ItemDataRole.UserRole)
        if index is None or not 0 <= index < len(self.current_articles):
            return
        article = self.current_articles[index]
        self.viewed_article = article
        self._translation_generation += 1
        if not article.read:
            article.read = True
            self.read_state.mark(article)
            item.setText(self._article_label(article))
            self._style_article_item(item, article)
        self.article_view.display(article)
        self.open_button.setEnabled(bool(article.link))
        self._update_translation_button(article)
        self._fetch_full_article(article)

    def _update_translation_button(self, article: Article) -> None:
        """Enable translation only when article and system languages differ."""
        if article.translated_content:
            self.translate_button.setText(t("已翻译"))
            self.translate_button.setEnabled(False)
            return
        sample = f"{article.title}\n{article.content}"
        try:
            enabled = TranslationService.needs_translation(sample)
        except LangDetectException:
            enabled = False
        self.translate_button.setText(t("翻译"))
        self.translate_button.setEnabled(enabled)

    def _fetch_full_article(self, article: Article) -> None:
        """Start one background full-text request for an article when needed."""
        if not article.link or article.page_fetched:
            return
        article.page_fetched = True
        self._run(
            lambda: FeedService.fetch_full_content(article.link),
            lambda result, target=article: self._full_article_loaded(target, result),
            lambda _error, target=article: self._full_article_failed(target),
        )

    def _full_article_loaded(
        self,
        article: Article,
        result: tuple[str, list[ArticleBlock], dict[str, str]],
    ) -> None:
        """Merge extracted text and metadata, then start progressive image loading."""
        text, blocks, metadata = result
        if not text and not blocks:
            self._full_article_failed(article)
            return
        article.full_text_failed = False
        article.author = article.author or metadata.get("author", "")
        article.pub_date = article.pub_date or metadata.get("date", "")
        should_replace = bool(text) and (
            (len(article.content) < 500 and len(text) > len(article.content))
            or len(text) > len(article.content) * 1.5
        )
        if should_replace:
            article.content = text
            article.blocks = blocks
            self._clear_translation_after_content_change(article)
        else:
            image = metadata.get("image", "")
            article.extra_image_urls = [image] if image else [
                block["src"] for block in blocks if block.get("type") == "image"
            ]
        self._download_images(article)
        if self.viewed_article is article:
            self.article_view.display(article)
            self._update_translation_button(article)

    def _clear_translation_after_content_change(self, article: Article) -> None:
        """Clear stale translation and cancel it only when this article is active."""
        article.clear_translation()
        if self.viewed_article is article:
            self._translation_generation += 1

    def _full_article_failed(self, article: Article) -> None:
        """Mark extraction failed while allowing a later selection to retry it."""
        article.page_fetched = False
        article.full_text_failed = True
        if self.viewed_article is article:
            self.article_view.display(article)

    def _download_images(self, article: Article) -> None:
        """Schedule unique article images up to the per-article safety limit."""
        for url in article.image_urls[: self.MAX_IMAGES]:
            if url in article.image_states:
                continue
            article.image_states[url] = "downloading"
            self._run(
                lambda source=url: download_image(source),
                lambda data, target=article, source=url: self._image_loaded(target, source, data),
                lambda _error, target=article, source=url: self._image_failed(target, source),
            )

    def _image_loaded(self, article: Article, source: str, data: bytes) -> None:
        """Validate and cache downloaded image bytes before refreshing the view."""
        if QImage.fromData(data).isNull():
            self._image_failed(article, source)
            return
        article.image_data[source] = data
        article.image_states[source] = "done"
        if self.viewed_article is article:
            self.article_view.display(article)

    def _image_failed(self, article: Article, source: str) -> None:
        """Record an image failure and refresh its visible placeholder."""
        article.image_states[source] = "failed"
        if self.viewed_article is article:
            self.article_view.display(article)

    def _show_add_dialog(self) -> None:
        """Collect an RSS URL and validate it in a background task."""
        dialog = AddSubscriptionDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        self.add_button.setEnabled(False)
        self.status_label.setText(t("正在加载文章…"))
        self._run(
            lambda: self.manager.add_subscription(dialog.url),
            self._subscription_added,
            self._add_subscription_failed,
        )

    def _subscription_added(self, result: tuple[bool, str]) -> None:
        """Handle subscription validation and select a successfully added feed."""
        self.add_button.setEnabled(True)
        success, message = result
        if not success:
            QMessageBox.warning(self, t("错误"), message)
            self.status_label.setText(message)
            return
        subscription = self.manager.subscriptions[-1]
        self._populate_subscriptions(subscription.id)
        self.status_label.setText(message)

    def _add_subscription_failed(self, details: str) -> None:
        """Restore the add button and report an unexpected add failure."""
        self.add_button.setEnabled(True)
        self._show_worker_error(details)

    def _selected_subscription(self) -> Subscription | None:
        """Return the domain object represented by the selected sidebar item."""
        item = self.subscription_list.currentItem()
        subscription_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        return next(
            (entry for entry in self.manager.subscriptions if entry.id == subscription_id),
            None,
        )

    def _remove_current_subscription(self) -> None:
        """Confirm and asynchronously remove the selected real subscription."""
        subscription = self._selected_subscription()
        if subscription is None:
            return
        answer = QMessageBox.question(
            self,
            t("确认删除"),
            t("确定删除“{title}”吗？").format(title=subscription.title),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.subscription_list.setEnabled(False)
        self._run(
            lambda: self.manager.remove_subscription(subscription.id),
            lambda _result: self._subscription_removed(),
            self._remove_subscription_failed,
        )

    def _subscription_removed(self) -> None:
        """Re-enable and rebuild the sidebar after removal completes."""
        self.subscription_list.setEnabled(True)
        self._populate_subscriptions()

    def _remove_subscription_failed(self, details: str) -> None:
        """Restore the sidebar and report an unexpected removal failure."""
        self.subscription_list.setEnabled(True)
        self._show_worker_error(details)

    def _refresh(self) -> None:
        """Refresh all feeds in the background and preserve current selection."""
        selected_id = self.current_subscription_id
        selected_article_key = (
            self.viewed_article.key if self.viewed_article is not None else None
        )
        self.refresh_button.setEnabled(False)
        self.status_label.setText(t("正在加载文章…"))

        def done(_result) -> None:
            """Restore controls, subscription, and article after a refresh."""
            self.refresh_button.setEnabled(True)
            if selected_article_key:
                self._pending_article_selection = (
                    selected_id,
                    selected_article_key,
                )
            self._populate_subscriptions(selected_id)
            self.status_label.setText(t("刷新完成"))

        def failed(details: str) -> None:
            """Restore controls and report a refresh failure."""
            self.refresh_button.setEnabled(True)
            self._show_worker_error(details)

        self._run(self.manager.refresh_all, done, failed)

    def _open_article(self) -> None:
        """Open the active article URL with the operating-system browser."""
        if (
            self.viewed_article
            and self.viewed_article.link
            and not QDesktopServices.openUrl(QUrl(self.viewed_article.link))
        ):
            webbrowser.open(self.viewed_article.link)

    def _show_translation_settings(self) -> None:
        """Open the Baidu credential editor and report a successful save."""
        dialog = TranslationSettingsDialog(self.settings, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.status_label.setText(t("百度翻译设置已保存"))

    def _translate_article(self) -> None:
        """Translate the active article online with automatic local fallback."""
        article = self.viewed_article
        if article is None:
            return
        self.translate_button.setEnabled(False)
        self.translate_button.setText(t("翻译中…"))
        target = TranslationService.os_language()
        app_id = str(self.settings.value(BAIDU_APP_ID_KEY, "") or "")
        secret_key = str(self.settings.value(BAIDU_SECRET_KEY, "") or "")
        self._translation_generation += 1
        generation = self._translation_generation
        self._run(
            lambda: translate_article_with_fallback(
                article,
                target,
                app_id,
                secret_key,
            ),
            lambda result, current=article, token=generation: self._translation_loaded(
                current, token, result
            ),
            lambda details, current=article, token=generation: self._translation_failed(
                current, token, details
            ),
        )

    def _translation_loaded(
        self,
        article: Article,
        generation: int,
        result: TranslationResult | None,
    ) -> None:
        """Apply a translation only if its article and generation are still active."""
        if self.viewed_article is not article or generation != self._translation_generation:
            return
        if result is None:
            self.translate_button.setText(t("翻译"))
            self.translate_button.setEnabled(False)
            return
        article.translated_title, article.translated_content, article.translated_block_texts = result
        if self.viewed_article is article:
            self.translate_button.setText(t("已翻译"))
            self.translate_button.setEnabled(False)
            self.article_view.display(article)

    def _translation_failed(
        self, article: Article, generation: int, details: str
    ) -> None:
        """Report translation failure only for the currently active request."""
        if self.viewed_article is not article or generation != self._translation_generation:
            return
        self.translate_button.setEnabled(True)
        self.translate_button.setText(t("翻译"))
        self._show_worker_error(details)
