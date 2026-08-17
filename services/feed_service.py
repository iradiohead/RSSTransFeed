"""Network access for RSS feeds, article pages, and article images."""

from __future__ import annotations

from urllib.parse import urlparse

import requests

from models import Article, ArticleBlock
from utils.article_extractor import extract_article_content, strip_html

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def download_image(url: str, max_bytes: int = 8 * 1024 * 1024) -> bytes:
    """Download one image and reject responses larger than the memory limit."""
    response = requests.get(
        url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"}, timeout=15
    )
    response.raise_for_status()
    if len(response.content) > max_bytes:
        raise ValueError("Image is larger than 8 MB")
    return response.content


class FeedService:
    """Fetch and normalize remote RSS and article content."""

    READER_PROXY = "https://r.jina.ai/"
    CONTENT_FIELDS = ("content", "summary_detail", "summary", "description")

    @staticmethod
    def fetch_feed(url: str):
        """Download an RSS document with a timeout and parse its entries."""
        import feedparser

        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        response.raise_for_status()
        return feedparser.parse(response.content)

    @classmethod
    def validate_feed(cls, url: str) -> tuple[bool, str]:
        """Validate an RSS URL and return either its title or an error message."""
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False, "Invalid RSS URL"
        feed = cls.fetch_feed(url)
        if not getattr(feed, "entries", None):
            error = getattr(feed, "bozo_exception", None)
            return False, str(error or "No articles found in feed")
        return True, feed.feed.get("title", "Untitled Feed")

    @staticmethod
    def _entry_content(entry) -> str:
        """Choose the most useful HTML content field from one RSS entry."""
        candidates = (
            FeedService._content_value(entry.get(key))
            for key in FeedService.CONTENT_FIELDS
        )
        cleaned = [strip_html(value) for value in candidates if value]
        return next(
            (item for item in cleaned if len(item.strip()) > 300),
            cleaned[0] if cleaned else "",
        )

    @staticmethod
    def _content_value(value: object) -> str:
        """Normalize the different content shapes produced by feedparser."""
        if isinstance(value, list):
            return FeedService._content_value(value[0]) if value else ""
        if isinstance(value, dict):
            return str(value.get("value", ""))
        return value if isinstance(value, str) else ""

    @classmethod
    def parse_articles(cls, feed, feed_title: str) -> list[Article]:
        """Convert parsed RSS entries into UI-independent Article objects."""
        return [
            Article(
                title=entry.get("title", "No Title"),
                link=entry.get("link", ""),
                content=cls._entry_content(entry),
                pub_date=entry.get("published", ""),
                author=entry.get("author", ""),
                feed_title=feed_title,
                guid=entry.get("id", ""),
            )
            for entry in getattr(feed, "entries", [])
        ]

    @classmethod
    def fetch_full_content(
        cls, url: str
    ) -> tuple[str, list[ArticleBlock], dict[str, str]]:
        """Fetch and extract a full article, using the reader proxy as fallback."""
        try:
            response = requests.get(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
                timeout=20,
            )
            response.raise_for_status()
            return extract_article_content(response.text, url)
        except requests.RequestException:
            return cls._fetch_via_proxy(url)

    @classmethod
    def _fetch_via_proxy(
        cls, url: str
    ) -> tuple[str, list[ArticleBlock], dict[str, str]]:
        """Fetch Markdown through the reader proxy when direct HTML access fails."""
        try:
            response = requests.get(cls.READER_PROXY + url, timeout=30)
            response.raise_for_status()
        except requests.RequestException:
            return "", [], {}

        text = response.text.split("Markdown Content:", 1)[-1].strip()
        if len(text) < 200:
            return "", [], {}
        blocks = [
            {"type": "text", "text": paragraph.strip()}
            for paragraph in text.split("\n\n")
            if len(paragraph.strip()) > 12
        ]
        return text, blocks, {}
