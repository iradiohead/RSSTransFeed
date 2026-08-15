"""Content extraction: boilerplate removal for article pages

提取文章页面的:
- 标题 / 作者 / 发布时间(trafilatura 元数据,meta 标签兜底)
- 正文纯文本(trafilatura 噪音去除结果优先)
- 正文块(段落与正文图片,按文档顺序;容器定位 + 关键词黑名单过滤)
- 正文 HTML(清理后的正文容器 HTML)

自动过滤:导航栏、推荐文章、广告、评论区、页脚、分享按钮、
"相关文章"、网站菜单等噪音内容。
"""
import re
from difflib import SequenceMatcher
from typing import Optional

import trafilatura
from bs4 import BeautifulSoup

from utils.html_utils import (
    CONTAINER_SELECTORS,
    extract_article_blocks,
    normalize_whitespace,
    remove_boilerplate,
)

# 正文容器选择时的参照文本长度与评分截断长度
REFERENCE_LEN = 1500

# 正文尾部附加推荐模块的典型开头标记(用于截断)
TRAILING_MARKERS = [
    "keep reading", "most popular", "read more", "read next",
    "related articles", "related stories", "related posts",
    "recommended", "also read", "more stories", "popular articles",
    "continue reading",
]


def _strip_trailing_boilerplate(text: str) -> str:
    """截掉正文尾部附加的推荐模块(如 Keep Reading / Most Popular)。

    推荐模块通常出现在文章后半段、以固定短语开头;遇到即截断其后的全部内容。
    """
    lines = text.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip().lower()
        if any(stripped.startswith(m) for m in TRAILING_MARKERS):
            # 只在文章后半段出现的标记才视为尾随模块,避免误伤正文引用
            if i > len(lines) * 0.4:
                return "\n".join(lines[:i]).strip()
    return text


def _strip_disclaimer_lines(text: str) -> str:
    """过滤联盟营销免责声明行(如'通过文章中的链接购买可能赚取佣金')。

    结构过滤覆盖不到时(例如纯文本来源)兜底使用。
    """
    lines = text.split("\n")
    kept = []
    for line in lines:
        low = line.lower()
        if re.search(r"earn.{0,40}commission", low):
            continue
        if "commission" in low and ("affiliate" in low or "link" in low):
            continue
        if "编辑独立性" in line or "editorial independence" in low:
            continue
        kept.append(line)
    return "\n".join(kept)


def _score_container(soup: BeautifulSoup, reference_text: str):
    """在与 trafilatura 干净文本最相似的候选中定位正文容器。"""
    reference = reference_text[:REFERENCE_LEN]
    best, best_score = None, 0.0
    for selector in CONTAINER_SELECTORS:
        for node in soup.select(selector):
            text = normalize_whitespace(node.get_text(" ", strip=True))
            if len(text) < 100:
                continue
            score = SequenceMatcher(None, reference, text[:2500]).ratio()
            if score > best_score:
                best, best_score = node, score
    return best


def _fallback_title(soup: BeautifulSoup) -> str:
    for selector in ["meta[property='og:title']", "h1"]:
        node = soup.select_one(selector)
        if node:
            return node.get("content") or node.get_text(" ", strip=True)
    return ""


def _fallback_author(soup: BeautifulSoup) -> str:
    for selector in ["meta[name='author']", "meta[property='article:author']"]:
        node = soup.select_one(selector)
        if node and node.get("content"):
            return node["content"]
    return ""


def _fallback_date(soup: BeautifulSoup) -> str:
    for selector in [
        "meta[property='article:published_time']",
        "meta[name='date']",
        "time[datetime]",
    ]:
        node = soup.select_one(selector)
        if node:
            return (
                node.get("content")
                or node.get("datetime")
                or node.get_text(" ", strip=True)
            )
    return ""


def extract_article_content(html: str, url: Optional[str] = None) -> dict:
    """从文章页 HTML 提取结构化内容(标题/作者/时间/正文/正文块/正文HTML)。

    Args:
        html: 文章页面的 HTML 源码。
        url: 文章原始 URL,用于相对图片地址解析。

    Returns:
        dict,键为 title/author/date/text/html/blocks;提取失败时各字段为空。
    """
    if not html:
        return {"title": "", "author": "", "date": "", "text": "", "html": "", "blocks": []}

    # 0. 整页预去噪:先用关键词黑名单移除导航/推荐/广告/评论/作者卡等元素,
    #    从源头保证正文与正文块都不含噪音
    soup = BeautifulSoup(html, "html.parser")
    remove_boilerplate(soup)
    precleaned_html = str(soup)

    # 1. trafilatura:正文噪音去除 + 标题/作者/日期提取
    meta_title = meta_author = meta_date = clean_text = ""
    doc = None
    try:
        doc = trafilatura.bare_extraction(precleaned_html, url=url, with_metadata=True, include_images=True)
        if doc:
            meta_title = doc.title or ""
            meta_author = doc.author or ""
            meta_date = str(doc.date) if doc.date else ""
            clean_text = _strip_disclaimer_lines(
                _strip_trailing_boilerplate(doc.text or doc.raw_text or "")
            )
    except Exception as e:
        print(f"trafilatura extraction failed: {e}")

    # 2. 定位正文容器:trafilatura 有结果时按文本相似度选择,否则按选择器顺序
    container = None
    if clean_text:
        container = _score_container(soup, clean_text)
    if container is None:
        for selector in CONTAINER_SELECTORS:
            node = soup.select_one(selector)
            if node and len(normalize_whitespace(node.get_text(" ", strip=True))) > 100:
                container = node
                break

    # 3. 正文块(段落 + 正文图片,已过滤噪音元素)
    blocks = extract_article_blocks(html, url, container=container) if container is not None else []

    # 3.1 trafilatura 提取的主图(通常为题图)作为第一个图文块;
    #     内嵌广告横幅/小头像已被上面的容器提取正确排除
    main_image = doc.image if doc else None
    if main_image and not any(
        b.get('type') == 'image' and b['src'] == main_image for b in blocks
    ):
        blocks.insert(0, {'type': 'image', 'src': main_image})

    # 4. 元数据兜底(meta 标签)
    title = meta_title or _fallback_title(soup)
    author = meta_author or _fallback_author(soup)
    date = meta_date or _fallback_date(soup)

    # 5. 正文文本:优先 trafilatura 的干净文本
    text = clean_text or "\n\n".join(b["text"] for b in blocks if b["type"] == "text")

    return {
        "title": title,
        "author": author,
        "date": date,
        "text": text,
        "html": str(container) if container is not None else "",
        "blocks": blocks,
        # 题图(og:image/trafilatura 主图):feed 长文场景仅追加此图,避免混入其它文章的推广图
        "image": main_image or "",
    }
