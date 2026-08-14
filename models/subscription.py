"""Data models for subscriptions and articles"""
from datetime import datetime
from typing import Optional


class Subscription:
    """Represents an RSS subscription"""
    
    def __init__(self, id: str, url: str, title: str, last_updated: Optional[str] = None):
        self.id = id
        self.url = url
        self.title = title
        self.last_updated = last_updated or datetime.now().isoformat()
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'url': self.url,
            'title': self.title,
            'last_updated': self.last_updated
        }
    
    @staticmethod
    def from_dict(data: dict):
        """Create from dictionary"""
        return Subscription(
            id=data.get('id'),
            url=data.get('url'),
            title=data.get('title'),
            last_updated=data.get('last_updated')
        )


class Article:
    """Represents an RSS article"""
    
    def __init__(self, title: str, link: str, content: str, 
                 pub_date: str = "", author: str = "", 
                 feed_title: str = "", guid: str = ""):
        self.title = title
        self.link = link
        self.content = content
        self.pub_date = pub_date
        self.author = author
        self.feed_title = feed_title
        self.guid = guid
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'title': self.title,
            'link': self.link,
            'content': self.content,
            'pubDate': self.pub_date,
            'author': self.author,
            'feedTitle': self.feed_title,
            'guid': self.guid
        }
    
    @staticmethod
    def from_dict(data: dict):
        """Create from dictionary"""
        return Article(
            title=data.get('title', 'No Title'),
            link=data.get('link', ''),
            content=data.get('content', ''),
            pub_date=data.get('pubDate', ''),
            author=data.get('author', ''),
            feed_title=data.get('feedTitle', ''),
            guid=data.get('guid', '')
        )
