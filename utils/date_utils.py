"""Utility functions for date handling"""
from datetime import datetime


def format_date(date_string: str) -> str:
    """Format date string to readable format"""
    if not date_string:
        return ""
    
    try:
        # Try to parse common RSS date formats
        try:
            dt = datetime.strptime(date_string, "%a, %d %b %Y %H:%M:%S %z")
            return dt.strftime("%Y-%m-%d %H:%M")
        except ValueError:
            try:
                dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d %H:%M")
            except ValueError:
                return date_string
    except Exception as e:
        print(f"Error formatting date: {e}")
        return date_string
