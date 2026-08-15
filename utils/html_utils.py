"""Utility functions for HTML processing"""
import re
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def strip_html(html_content: str) -> str:
    """把 HTML 文本转换成纯文本，去掉标签和脚本内容。

    这个函数主要用于 RSS 摘要内容的展示，避免文章正文里混入 HTML 标签。
    例如 "<p>Hello</p>" 会变成 "Hello"。
    """
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text()
    except Exception as e:
        print(f"Error stripping HTML: {e}")
        return html_content


def normalize_whitespace(text: str) -> str:
    """压缩多余空白，保持正文段落格式干净。

    该函数会把连续空白、换行和制表符统一成单个空格，方便后续正文展示。
    """
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def extract_article_text(html_content: str, url: Optional[str] = None) -> str:
    """从网页 HTML 中提取真正的正文内容。

    这一步会优先定位常见的正文容器，如 article、main、.content 等，
    然后去掉脚本、导航、侧边栏、页脚等干扰区域，最后保留文章正文段落。
    
    Args:
        html_content: 文章页面的 HTML 源码。
        url: 可选文章地址，主要用于调试/日志。

    Returns:
        清理后的正文纯文本。
    """
    if not html_content:
        return ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        for selector in [
            "article",
            "main",
            ".article-content",
            ".content",
            ".post-content",
            ".entry-content",
            "#content",
            "#article",
            "#main",
        ]:
            node = soup.select_one(selector)
            if node:
                soup = node
                break

        for bad in soup.select("script, style, noscript, iframe, svg, nav, aside, footer, header, form, button"):
            bad.decompose()

        paragraphs = []
        for node in soup.select("p, h1, h2, h3, li"):
            text = normalize_whitespace(node.get_text(" ", strip=True))
            if text and len(text) > 12:
                paragraphs.append(text)

        if paragraphs:
            return "\n\n".join(paragraphs)

        text = normalize_whitespace(soup.get_text(" ", strip=True))
        return text
    except Exception as e:
        print(f"Error extracting article text: {e}")
        return strip_html(html_content)


def fetch_article_html(url: str, timeout: int = 20) -> str:
    """下载文章页面 HTML，作为正文提取的兜底方案。

    当 RSS 中的 summary 太短或只有摘要时，程序会调用此函数去抓取文章原链接，
    再用正文提取逻辑恢复完整文章内容。

    Args:
        url: 文章原始 URL。
        timeout: 请求超时秒数。

    Returns:
        HTML 字符串；若请求失败则返回空字符串。
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error fetching article HTML for {url}: {e}")
        return ""


# 正文容器候选选择器(按优先级)
CONTAINER_SELECTORS = [
    "article",
    "main",
    ".article-content",
    ".post-content",
    ".entry-content",
    ".article-body",
    ".post-body",
    ".story-body",
    ".content",
    "#content",
    "#article",
    "#main",
]

# 干扰元素的 class/id 关键词:导航栏、推荐、广告、评论区、分享、页脚、菜单等
BOILERPLATE_KEYWORDS = [
    "nav", "menu", "header", "footer", "breadcrumb", "sidebar", "widget",
    "share", "social", "follow", "newsletter", "subscribe", "signup",
    "related", "recommend", "promo", "advert", "ad-", "-ad", "sponsor",
    "comment", "reply", "author-bio", "byline", "login", "search",
    "pagination", "cookie", "consent", "popup", "modal", "trending",
    "read-more", "readmore", "read-next", "keep-reading", "also-read",
    "tags", "category", "meta-", "post-meta",
    "toolbar", "dropdown", "overlay", "banner", "popular",
    "affiliate", "disclaimer", "disclosure",
    "author-card", "post-authors", "author-box", "about-author",
]


def _matches_boilerplate(tag) -> bool:
    """判断元素是否属于噪音区域(按 class/id 关键词)。

    空标签(如 <br> 的占位)attrs 可能为 None,需防御。
    """
    for attr in ("class", "id"):
        values = (getattr(tag, 'attrs', None) or {}).get(attr) or []
        if isinstance(values, str):
            values = [values]
        for val in values:
            val = val.lower()
            if any(kw in val for kw in BOILERPLATE_KEYWORDS):
                return True
    return False


def remove_boilerplate(soup):
    """按关键词黑名单整页移除噪音元素(导航/推荐/广告/评论/作者卡等)。

    在交给正文提取器(trafilatura 等)之前调用,从源头去掉噪音,
    保证提取出的正文与正文块都不包含这些内容。原地修改并返回 soup。
    """
    for el in list(soup.find_all(True)):
        if _matches_boilerplate(el):
            el.decompose()
    return soup


def extract_article_blocks(html_content: str, url: Optional[str] = None, container=None):
    """从网页 HTML 按文档顺序提取正文块:段落文本和图片 URL。

    定位正文容器(或使用传入的容器),过滤导航/推荐/广告/评论/分享等噪音元素。
    支持懒加载 data-src,相对地址自动转绝对地址,并过滤尺寸过小的装饰性图标。

    Args:
        html_content: 文章页面的 HTML 源码。
        url: 文章原始 URL,用于相对图片地址的解析。
        container: 可选的 BeautifulSoup 元素,指定正文容器,跳过自动定位。

    Returns:
        块列表,每项为 {'type': 'text', 'text': ...} 或 {'type': 'image', 'src': ...}。
    """
    if not html_content and container is None:
        return []

    try:
        soup = container if container is not None else BeautifulSoup(html_content, "html.parser")

        if container is None:
            for selector in CONTAINER_SELECTORS:
                node = soup.select_one(selector)
                if node and len(normalize_whitespace(node.get_text(" ", strip=True))) > 100:
                    soup = node
                    break

        for bad in soup.select("script, style, noscript, iframe, svg, nav, aside, footer, header, form, button, input"):
            bad.decompose()

        # 噪音元素(分享按钮/推荐/广告/评论等)整体移除
        for el in list(soup.find_all(True)):
            if _matches_boilerplate(el):
                el.decompose()

        blocks = []
        seen_srcs = set()
        for el in soup.select("p, h1, h2, h3, li, blockquote, pre, img, figure"):
            if _matches_boilerplate(el):
                continue

            if el.name in ("img", "figure"):
                img = el if el.name == "img" else el.find("img")
                if img is None:
                    continue
                src = img.get("data-src") or img.get("src") or ""
                if not src or src.startswith("data:"):
                    continue
                if url:
                    src = urljoin(url, src)
                # 过滤装饰性小图标(宽高属性均小于 50px)
                w, h = img.get("width"), img.get("height")
                try:
                    if w and h and int(w) < 50 and int(h) < 50:
                        continue
                except (TypeError, ValueError):
                    pass
                if src in seen_srcs:
                    continue
                seen_srcs.add(src)
                blocks.append({'type': 'image', 'src': src})
                continue

            text = normalize_whitespace(el.get_text(" ", strip=True))
            if text and len(text) > 12:
                blocks.append({'type': 'text', 'text': text})

        return blocks
    except Exception as e:
        print(f"Error extracting article blocks: {e}")
        return []


def download_image(url: str, timeout: int = 15, max_bytes: int = 8 * 1024 * 1024):
    """下载图片字节,用于详情页图片渲染。

    Args:
        url: 图片地址。
        timeout: 请求超时秒数。
        max_bytes: 超过该大小视为异常图片,返回 None。

    Returns:
        图片二进制数据;请求失败或过大时返回 None。
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.content
        if len(data) > max_bytes:
            print(f"Image too large ({len(data)} bytes): {url}")
            return None
        return data
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
        return None
