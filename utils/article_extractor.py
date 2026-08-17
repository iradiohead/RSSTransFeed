"""Extract readable text, images, and metadata from article HTML."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from models import ArticleBlock

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

NOISE_WORDS = (
    "nav", "menu", "header", "footer", "breadcrumb", "sidebar", "widget",
    "share", "social", "newsletter", "subscribe", "related", "recommend",
    "promo", "advert", "sponsor", "comment", "author-bio", "author-card",
    "post-authors", "login", "search", "cookie", "popup", "banner",
    "affiliate", "disclaimer",
)
ARTICLE_SELECTORS = (
    "article", "main", ".article-content", ".post-content", ".entry-content",
    ".article-body", ".story-body", "#article", "#main",
)


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace while preserving readable text content."""
    return re.sub(r"\s+", " ", text or "").strip()


def strip_html(value: str) -> str:
    """Convert an RSS HTML fragment to plain text."""
    from bs4 import BeautifulSoup

    return BeautifulSoup(value, "html.parser").get_text() if value else ""


def _is_noise(tag) -> bool:
    """Return whether a tag belongs to navigation, advertising, or other noise."""
    attrs = getattr(tag, "attrs", {}) or {}
    values: list[str] = []
    for key in ("class", "id"):
        value = attrs.get(key, [])
        values.extend([value] if isinstance(value, str) else value)
    joined = " ".join(str(value).lower() for value in values)
    return any(word in joined for word in NOISE_WORDS)


def _clean_document(html: str) -> BeautifulSoup:
    """Parse HTML and remove non-article elements before content extraction."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for node in soup.select(
        "script, style, noscript, iframe, svg, nav, aside, footer, header, "
        "form, button, input"
    ):
        node.decompose()
    for node in list(soup.find_all(True)):
        if _is_noise(node):
            node.decompose()
    return soup


def _find_article_container(soup: BeautifulSoup):
    """Select the first sufficiently large, article-like HTML container."""
    for selector in ARTICLE_SELECTORS:
        node = soup.select_one(selector)
        if node and len(normalize_whitespace(node.get_text(" ", strip=True))) > 100:
            return node
    return soup.body or soup


def _image_source(image, base_url: str) -> str:
    """Resolve a usable image URL and reject data URIs and tiny icons."""
    source = image.get("data-src") or image.get("src") or ""
    if not source or source.startswith("data:"):
        return ""
    try:
        width = int(image.get("width", 100))
        height = int(image.get("height", 100))
        if width < 50 and height < 50:
            return ""
    except (TypeError, ValueError):
        pass
    return urljoin(base_url, source)


def _extract_blocks(container, base_url: str) -> list[ArticleBlock]:
    """Build ordered text and image blocks from the selected article container."""
    blocks: list[ArticleBlock] = []
    seen_images: set[str] = set()
    for node in container.select("p, h1, h2, h3, li, blockquote, pre, img, figure"):
        if _is_noise(node):
            continue
        if node.name in {"img", "figure"}:
            image = node if node.name == "img" else node.find("img")
            source = _image_source(image, base_url) if image else ""
            if source and source not in seen_images:
                seen_images.add(source)
                blocks.append({"type": "image", "src": source})
            continue
        text = normalize_whitespace(node.get_text(" ", strip=True))
        if len(text) > 12:
            blocks.append({"type": "text", "text": text})
    return blocks


def _node_value(node, *attributes: str) -> str:
    """Return the first populated attribute or the node's visible text."""
    if node is None:
        return ""
    return next(
        (str(value) for name in attributes if (value := node.get(name))),
        node.get_text(" ", strip=True),
    )


def _metadata(soup: BeautifulSoup, document, base_url: str) -> dict[str, str]:
    """Combine trafilatura metadata with standard HTML metadata fallbacks."""
    title_node = soup.select_one("meta[property='og:title'], h1")
    author_node = soup.select_one(
        "meta[name='author'], meta[property='article:author']"
    )
    date_node = soup.select_one(
        "meta[property='article:published_time'], meta[name='date'], time[datetime]"
    )
    image = urljoin(base_url, getattr(document, "image", "") or "")
    return {
        "title": (getattr(document, "title", "") or "")
        or _node_value(title_node, "content"),
        "author": (getattr(document, "author", "") or "")
        or _node_value(author_node, "content"),
        "date": str(getattr(document, "date", "") or "")
        or _node_value(date_node, "content", "datetime"),
        "image": image,
    }


def extract_article_content(
    html: str, url: str = ""
) -> tuple[str, list[ArticleBlock], dict[str, str]]:
    """Return clean text, ordered content blocks, and metadata for one article."""
    if not html:
        return "", [], {}

    soup = _clean_document(html)
    cleaned_html = str(soup)
    try:
        import trafilatura

        document = trafilatura.bare_extraction(
            cleaned_html, url=url or None, with_metadata=True, include_images=True
        )
    except Exception:  # noqa: BLE001 - malformed third-party HTML must fall back
        document = None

    container = _find_article_container(soup)
    blocks = _extract_blocks(container, url)
    main_image = urljoin(url, getattr(document, "image", "") or "")
    if main_image and not any(block.get("src") == main_image for block in blocks):
        blocks.insert(0, {"type": "image", "src": main_image})

    extracted = (
        getattr(document, "text", "")
        or getattr(document, "raw_text", "")
        or ""
    ).strip()
    text = extracted or "\n\n".join(
        block["text"] for block in blocks if block["type"] == "text"
    )
    return text, blocks, _metadata(soup, document, url)
