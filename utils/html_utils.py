"""Utility functions for HTML processing"""
import re
from typing import Optional

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
