"""Service for managing subscriptions"""
from datetime import datetime
from typing import List, Optional
from models.subscription import Subscription, Article
from services.storage_service import StorageService
from services.feed_service import FeedService


class SubscriptionManager:
    """集中管理订阅源、文章加载与缓存逻辑。

    它是应用的核心控制层：负责加载历史订阅、添加/删除订阅、抓取文章列表、
    缓存文章结果，并在用户点击刷新时更新订阅状态。
    """
    
    def __init__(self, storage_service: StorageService):
        """创建订阅管理器并立即加载已保存的订阅数据。

        Args:
            storage_service: 提供订阅 JSON 读写能力的 StorageService 实例。
        """
        self.storage = storage_service
        self.subscriptions: List[Subscription] = []
        self.feed_cache: dict = {}  # key: feed_id 或 "all"，value: 文章列表
        self.load_subscriptions()
    
    def load_subscriptions(self) -> None:
        """从持久化文件中读取所有订阅，并同步到内存对象。"""
        self.subscriptions = self.storage.load_subscriptions()
    
    def save_subscriptions(self) -> bool:
        """将当前内存中的订阅列表写回本地文件。"""
        return self.storage.save_subscriptions(self.subscriptions)
    
    def add_subscription(self, url: str) -> tuple[bool, str]:
        """添加一个新的 RSS 订阅。

        Args:
            url: RSS 源地址。

        Returns:
            (是否成功, 订阅标题或错误信息) 的二元组。
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
        """删除指定订阅，并清理该订阅对应的缓存数据。"""
        self.subscriptions = [s for s in self.subscriptions if s.id != sub_id]
        if sub_id in self.feed_cache:
            del self.feed_cache[sub_id]
        return self.save_subscriptions()
    
    def get_articles(self, feed_id: Optional[str] = None) -> List[Article]:
        """返回全部文章或某个订阅源下的文章列表。

        Args:
            feed_id: 订阅 ID；若为 None，则返回所有订阅的文章。

        Returns:
            文章列表，按时间/来源经过整理后返回。
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
        """重新拉取所有订阅源并刷新最新更新时间。"""
        self.feed_cache.clear()  # Clear cache to force reload
        
        for sub in self.subscriptions:
            try:
                feed = FeedService.fetch_feed(sub.url)
                if feed:
                    sub.last_updated = datetime.now().isoformat()
            except Exception as e:
                print(f"Error refreshing feed {sub.title}: {e}")
        
        self.save_subscriptions()
    
    def refresh_all_subscriptions(self) -> None:
        """重新拉取所有订阅源并刷新最新更新时间（兼容旧方法名）。"""
        self.refresh_all()
