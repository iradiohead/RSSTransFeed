"""Rich-text article display with responsive inline images."""

from __future__ import annotations

import html
from datetime import datetime

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QTextBrowser

from models import Article
from ui.i18n import t
from ui.theme import COLORS


def _format_date(value: str) -> str:
    """Format common RSS and ISO timestamps without failing on unknown formats."""
    if not value:
        return ""
    for parser in (
        lambda: datetime.strptime(value, "%a, %d %b %Y %H:%M:%S %z"),
        lambda: datetime.fromisoformat(value.replace("Z", "+00:00")),
    ):
        try:
            return parser().strftime("%Y-%m-%d %H:%M")
        except ValueError:
            continue
    return value


class ArticleBrowser(QTextBrowser):
    """Render an Article as readable HTML and resize its images responsively."""

    MAX_CONTENT_WIDTH = 760

    def __init__(self, parent=None):
        """Configure the browser and a debounced image-resize timer."""
        super().__init__(parent)
        self.article: Article | None = None
        self._rerender_pending = False
        self.setOpenExternalLinks(True)
        self.setReadOnly(True)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.viewport().installEventFilter(self)
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(180)
        self._resize_timer.timeout.connect(self.rerender)
        self.verticalScrollBar().sliderReleased.connect(
            self._finish_deferred_rerender
        )

    def display(self, article: Article) -> None:
        """Set the active article and render it while preserving scroll position."""
        self.article = article
        self.rerender()

    def reset(self) -> None:
        """Clear both the displayed document and its active Article reference."""
        self.article = None
        self.clear()

    def eventFilter(self, watched, event) -> bool:
        """Debounce rerendering when the text viewport changes width."""
        if (
            watched is self.viewport()
            and event.type() == QEvent.Type.Resize
            and self.article is not None
        ):
            self._resize_timer.start()
        return super().eventFilter(watched, event)

    def rerender(self) -> None:
        """Rebuild the current document and restore its vertical scroll offset."""
        if self.article is None:
            return
        scrollbar = self.verticalScrollBar()
        if scrollbar.isSliderDown():
            self._rerender_pending = True
            return
        self._rerender_pending = False
        old_position = scrollbar.value()
        body, resources = self._build_body(self.article)
        self.setHtml(
            f"<html><head><style>{self._stylesheet()}</style></head>"
            f"<body>{body}</body></html>"
        )
        document = self.document()
        for resource_url, image in resources.items():
            document.addResource(
                QTextDocument.ResourceType.ImageResource, resource_url, image
            )
        if resources:
            document.markContentsDirty(0, document.characterCount())
        scrollbar.setValue(old_position)

    def _finish_deferred_rerender(self) -> None:
        """Apply content updates postponed while the user dragged the scrollbar."""
        if self._rerender_pending:
            self.rerender()

    def _build_body(self, article: Article) -> tuple[str, dict[QUrl, QImage]]:
        """Build article HTML and collect image resources for QTextDocument."""
        resources: dict[QUrl, QImage] = {}
        parts = self._header_html(article)
        parts.extend(self._content_html(article, resources))
        if article.link:
            escaped_link = html.escape(article.link, quote=True)
            parts.append(
                f"<p class='meta'><a href='{escaped_link}'>"
                f"{html.escape(article.link)}</a></p>"
            )
        return "".join(parts), resources

    @staticmethod
    def _header_html(article: Article) -> list[str]:
        """Create title, source metadata, and extraction-warning HTML."""
        title = article.translated_title or article.title
        parts = [f"<h1>{html.escape(title)}</h1>"]
        if article.translated_title:
            parts.append(f"<div class='meta'>原标题：{html.escape(article.title)}</div>")
        metadata = [
            value
            for value in (
                article.author,
                _format_date(article.pub_date),
                article.feed_title,
            )
            if value
        ]
        if metadata:
            parts.append(
                f"<div class='meta'>{' · '.join(map(html.escape, metadata))}</div>"
            )
        if article.full_text_failed and len(article.content) < 300:
            parts.append("<p class='hint'>⚠ 全文获取失败，当前显示 RSS 摘要。</p>")
        return parts

    def _content_html(
        self, article: Article, resources: dict[QUrl, QImage]
    ) -> list[str]:
        """Render original or translated text while retaining image positions."""
        if article.blocks and (
            not article.translated_content or article.translated_block_texts
        ):
            translated = iter(article.translated_block_texts or [])
            return [
                (
                    f"<p>{html.escape(
                        next(translated, block.get('text', ''))
                        if article.translated_block_texts
                        else block.get('text', '')
                    )}</p>"
                    if block.get("type") == "text"
                    else self._image_html(article, block.get("src", ""), resources)
                )
                for block in article.blocks
            ]

        content = article.translated_content or article.content
        parts = [
            f"<p>{html.escape(paragraph)}</p>"
            for paragraph in content.split("\n\n")
            if paragraph.strip()
        ]
        parts.extend(
            self._image_html(article, url, resources)
            for url in article.image_urls
        )
        return parts

    def _image_html(
        self, article: Article, source: str, resources: dict[QUrl, QImage]
    ) -> str:
        """Register one decoded image or return a localized failure placeholder."""
        image = QImage.fromData(article.image_data.get(source, b""))
        if not image.isNull():
            resource_url = QUrl(f"rss-image://{abs(hash(source))}")
            resources[resource_url] = image
            width = min(max(100, self.viewport().width() - 40), image.width())
            return f"<p><img src='{resource_url.toString()}' width='{width}'></p>"
        if article.image_states.get(source) == "failed":
            return f"<p class='meta'>{html.escape(t('[图片加载失败]'))}</p>"
        return ""

    @classmethod
    def _stylesheet(cls) -> str:
        """Return the compact stylesheet used inside the article document."""
        return f"""
        body {{
            color: {COLORS['text']}; background: {COLORS['background']};
            font-family: Georgia, "Microsoft YaHei", serif; font-size: 18px;
            line-height: 1.65; max-width: {cls.MAX_CONTENT_WIDTH}px; margin: 12px auto;
        }}
        h1 {{ color: #E2E7EC; font-size: 28px; line-height: 1.25; }}
        .meta {{ color: {COLORS['muted']}; font: 13px "Segoe UI"; line-height: 1.5; }}
        .hint {{ color: #D7A75F; }}
        img {{ margin: 12px auto; }}
        a {{ color: #68A0F2; }}
        """
