"""Service for managing subscriptions"""
from datetime import datetime
from typing import List, Optional
from models.subscription import Subscription, Article
from services.storage_service import StorageService
from services.feed_service import FeedService


class SubscriptionManager:
    """Manages subscriptions and articles"""
    
    def __init__(self, storage_service: StorageService):
        self.storage = storage_service
        self.subscriptions: List[Subscription] = []
        self.feed_cache: dict = {}  # Cache for articles by feed ID
        self.load_subscriptions()
    
    def load_subscriptions(self) -> None:
        """Load subscriptions from storage"""
        self.subscriptions = self.storage.load_subscriptions()
    
    def save_subscriptions(self) -> bool:
        """Save subscriptions to storage"""
        return self.storage.save_subscriptions(self.subscriptions)
    
    def add_subscription(self, url: str) -> tuple[bool, str]:
        """Add a new subscription
        
        Args:
            url: RSS feed URL
            
        Returns:
            Tuple of (success, message or feed_title)
        """
        # Validate feed (includes URL validation)
        is_valid, message = FeedService.validate_feed(url)
        if not is_valid:
            return False, message
        
        feed_title = message
        
        # Create subscription
        sub_id = str(len(self.subscriptions) + 1)
        subscription = Subscription(
            id=sub_id,
            url=url,
            title=feed_title,
            last_updated=datetime.now().isoformat()
        )
        
        self.subscriptions.append(subscription)
        self.save_subscriptions()
        
        return True, feed_title
    
    def remove_subscription(self, sub_id: str) -> bool:
        """Remove a subscription"""
        self.subscriptions = [s for s in self.subscriptions if s.id != sub_id]
        if sub_id in self.feed_cache:
            del self.feed_cache[sub_id]
        return self.save_subscriptions()
    
    def get_articles(self, feed_id: Optional[str] = None) -> List[Article]:
        """Get articles for a subscription or all subscriptions
        
        Args:
            feed_id: Subscription ID (None for all articles)
            
        Returns:
            List of Article objects
        """
        # Check cache first
        cache_key = feed_id or "all"
        if cache_key in self.feed_cache:
            return self.feed_cache[cache_key]
        
        articles = []
        
        if feed_id:
            # Get articles from specific subscription
            sub = next((s for s in self.subscriptions if s.id == feed_id), None)
            if sub:
                feed = FeedService.fetch_feed(sub.url)
                articles = FeedService.parse_articles(feed, sub.title)[:50]
        else:
            # Get articles from all subscriptions
            for sub in self.subscriptions:
                try:
                    feed = FeedService.fetch_feed(sub.url)
                    sub_articles = FeedService.parse_articles(feed, sub.title)[:20]
                    articles.extend(sub_articles)
                except Exception as e:
                    print(f"Error loading feed {sub.title}: {e}")
            
            # Sort by date (newest first)
            articles.sort(key=lambda x: x.pub_date, reverse=True)
            articles = articles[:50]  # Limit to 50 articles
        
        # Cache the articles
        self.feed_cache[cache_key] = articles
        return articles
    
    def refresh_all(self) -> None:
        """Refresh all subscriptions"""
        self.feed_cache.clear()  # Clear cache to force reload
        
        for sub in self.subscriptions:
            try:
                feed = FeedService.fetch_feed(sub.url)
                if feed:
                    sub.last_updated = datetime.now().isoformat()
            except Exception as e:
                print(f"Error refreshing feed {sub.title}: {e}")
        
        self.save_subscriptions()
