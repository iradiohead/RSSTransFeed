"""Utility functions for HTML processing"""
from bs4 import BeautifulSoup


def strip_html(html_content: str) -> str:
    """Remove HTML tags from content"""
    if not html_content:
        return ""
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        return soup.get_text()
    except Exception as e:
        print(f"Error stripping HTML: {e}")
        return html_content
