"""Service for fetching and parsing RSS feeds"""
import feedparser
from typing import List

from models.subscription import Article
from utils.html_utils import extract_article_text, fetch_article_html, strip_html


class FeedService:
    """负责获取 RSS 源并把文章结构化成程序可用的 Article 对象。"""

    @staticmethod
    def fetch_feed(url: str) -> dict:
        """拉取并解析 RSS 地址返回的 feed 数据。

        Args:
            url: 订阅源网址。

        Returns:
            feedparser 返回的解析结果字典；如果失败则返回空字典。
        """
        try:
            feed = feedparser.parse(url)
            return feed
        except Exception as e:
            print(f"Error fetching feed from {url}: {e}")
            return {}

    @staticmethod
    def _extract_entry_content(entry: dict) -> str:
        """从单篇 RSS 条目中选择正文内容。

        只使用 feed 自带内容：优先选择超过 300 字符的候选（视为完整正文），
        否则回退到最优先的候选（即使是短摘要）。抓网页补全文改为在用户
        打开文章时按需进行（fetch_full_text），避免列表加载被大量网页请求拖慢。
        """
        candidates = []

        for key in ['content', 'summary_detail', 'summary', 'description']:
            value = entry.get(key)
            if isinstance(value, list):
                if value:
                    text = value[0].get('value', '') if isinstance(value[0], dict) else str(value[0])
                    candidates.append(text)
            elif isinstance(value, dict):
                text = value.get('value', '')
                if text:
                    candidates.append(text)
            elif isinstance(value, str):
                if value:
                    candidates.append(value)

        # 先尝试从 RSS 摘要中找到足够长的内容（300 字符以上）
        for candidate in candidates:
            cleaned = strip_html(candidate)
            if cleaned and len(cleaned.strip()) > 300:
                return cleaned

        # 回退到最优先的候选（即使它很短）；网页全文由 fetch_full_text 按需补充
        fallback = candidates[0] if candidates else ''
        return strip_html(fallback)

    @staticmethod
    def fetch_full_text(url: str) -> str:
        """抓取文章原网页并提取正文，用于补全过短的 RSS 摘要。

        Args:
            url: 文章原始 URL。

        Returns:
            提取出的正文纯文本；请求或解析失败时返回空字符串。
        """
        html = fetch_article_html(url)
        if not html:
            return ""
        return extract_article_text(html, url)

    @staticmethod
    def parse_articles(feed: dict, feed_title: str = "") -> List[Article]:
        """将解析后的 feed 转换成 Article 列表。

        Args:
            feed: feedparser 返回的对象。
            feed_title: 订阅源标题，用于 UI 展示和文章归属标签。

        Returns:
            生成的 Article 列表。
        """
        articles = []

        try:
            for entry in feed.entries:
                article = Article(
                    title=entry.get('title', 'No Title'),
                    link=entry.get('link', ''),
                    content=FeedService._extract_entry_content(entry),
                    pub_date=entry.get('published', ''),
                    author=entry.get('author', ''),
                    feed_title=feed_title,
                    guid=entry.get('id', '')
                )
                articles.append(article)
        except Exception as e:
            print(f"Error parsing articles: {e}")

        return articles

    @staticmethod
    def validate_feed(url: str) -> tuple[bool, str]:
        """校验一个 URL 是否确实是有效的 RSS 订阅源。

        Args:
            url: 待校验地址。

        Returns:
            二元组 (is_valid, message)。当合法时返回 (True, feed_title)，
            否则返回 (False, 错误原因)。
        """
        # Quick URL format check
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                return False, "Invalid URL format"
        except Exception as e:
            return False, str(e)

        try:
            feed = FeedService.fetch_feed(url)

            if feed.bozo and feed.bozo_exception:
                return False, f"Feed parse warning: {feed.bozo_exception}"

            if not feed.entries:
                return False, "No articles found in feed"

            return True, feed.feed.get('title', 'Untitled Feed')
        except Exception as e:
            return False, str(e)
