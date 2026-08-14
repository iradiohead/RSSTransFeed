"""Service for fetching and parsing RSS feeds"""
import feedparser
from typing import List
from models.subscription import Article
from utils.html_utils import strip_html


class FeedService:
    """Handles RSS feed fetching and parsing"""
    
    @staticmethod
    def fetch_feed(url: str) -> dict:
        """Fetch and parse an RSS feed
        
        Args:
            url: RSS feed URL
            
        Returns:
            Parsed feed dictionary
        """
        try:
            feed = feedparser.parse(url)
            return feed
        except Exception as e:
            print(f"Error fetching feed from {url}: {e}")
            return {}
    
    @staticmethod
    def parse_articles(feed: dict, feed_title: str = "") -> List[Article]:
        """Parse articles from a feed
        
        Args:
            feed: Parsed feedparser feed object
            feed_title: Title of the feed source
            
        Returns:
            List of Article objects
        """
        articles = []
        
        try:
            for entry in feed.entries:
                article = Article(
                    title=entry.get('title', 'No Title'),
                    link=entry.get('link', ''),
                    content=strip_html(entry.get('summary', '')),
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
        """Validate if a URL is a valid RSS feed
        
        Args:
            url: Feed URL to validate
            
        Returns:
            Tuple of (is_valid, message)
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
