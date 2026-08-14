"""Utility functions for date handling"""
from datetime import datetime


def format_date(date_string: str) -> str:
    """把 RSS/网页中的时间字符串转换成更易读的格式。

    该函数优先尝试解析常见的 RSS 日期格式，并兼容 ISO 8601 的时间字符串，
    例如 "Mon, 02 Jan 2024 10:11:12 +0000" 或 "2024-01-02T10:11:12Z"。
    若解析失败，则直接返回原始字符串，避免界面崩溃。
    """
    if not date_string:
        return ""
    
    try:
        # 先尝试 RSS 常见格式: "Tue, 02 Jan 2024 12:34:56 +0000"
        try:
            dt = datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            try:
                # 再尝试 ISO 8601 形式
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                return date_string
    except Exception as e:
        print(f"Error formatting date: {e}")
        return date_string
