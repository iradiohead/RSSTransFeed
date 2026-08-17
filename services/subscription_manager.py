"""Subscription lifecycle and in-memory article cache."""

from __future__ import annotations

import threading
from datetime import datetime

import requests

from models import Article, Subscription
from services.feed_service import FeedService
from services.storage_service import StorageService


class SubscriptionManager:
    """Coordinate feed access, subscription changes, and article caching."""

    def __init__(self, storage: StorageService):
        """Load saved subscriptions and create an empty feed cache."""
        self.storage = storage
        self.subscriptions = storage.load_subscriptions()
        self.feed_cache: dict[str, list[Article]] = {}
        self._lock = threading.RLock()

    def add_subscription(self, url: str) -> tuple[bool, str]:
        """Validate, assign an ID to, and persist a new subscription."""
        with self._lock:
            if any(item.url == url for item in self.subscriptions):
                return False, "This feed is already subscribed"
            valid, message = FeedService.validate_feed(url)
            if not valid:
                return False, message
            subscription = Subscription(self._next_id(), url, message)
            self.subscriptions.append(subscription)
            self.feed_cache.pop("all", None)
            self.storage.save_subscriptions(self.subscriptions)
            return True, message

    def _next_id(self) -> str:
        """Return the next numeric subscription ID without reusing active IDs."""
        numeric_ids = [
            int(item.id) for item in self.subscriptions if item.id.isdigit()
        ]
        return str(max(numeric_ids, default=0) + 1)

    def remove_subscription(self, subscription_id: str) -> None:
        """Delete a subscription and invalidate its related article caches."""
        with self._lock:
            self.subscriptions = [
                item for item in self.subscriptions if item.id != subscription_id
            ]
            self.feed_cache.pop(subscription_id, None)
            self.feed_cache.pop("all", None)
            self.storage.save_subscriptions(self.subscriptions)

    def get_articles(self, subscription_id: str | None) -> list[Article]:
        """Return up to 50 articles, without caching complete network failure."""
        with self._lock:
            key = subscription_id or "all"
            if key in self.feed_cache:
                return self.feed_cache[key]
            selected = (
                [item for item in self.subscriptions if item.id == subscription_id]
                if subscription_id
                else list(self.subscriptions)
            )
            limit_per_feed = 50 if subscription_id else 20
            articles, fetched_any = self._fetch_articles(selected, limit_per_feed)
            if not subscription_id:
                articles.sort(key=lambda item: item.pub_date, reverse=True)
            result = articles[:50]
            if fetched_any:
                self.feed_cache[key] = result
            return result

    @staticmethod
    def _fetch_articles(
        subscriptions: list[Subscription], limit_per_feed: int
    ) -> tuple[list[Article], bool]:
        """Return collected articles and whether any feed request succeeded."""
        articles: list[Article] = []
        fetched_any = not subscriptions
        for subscription in subscriptions:
            fetched = SubscriptionManager._fetch_subscription(subscription)
            if fetched is None:
                continue
            fetched_any = True
            articles.extend(fetched[:limit_per_feed])
        return articles, fetched_any

    @staticmethod
    def _fetch_subscription(
        subscription: Subscription,
    ) -> list[Article] | None:
        """Fetch one feed, returning None when its network request fails."""
        try:
            feed = FeedService.fetch_feed(subscription.url)
        except requests.RequestException:
            return None
        return FeedService.parse_articles(feed, subscription.title)

    def refresh_all(self) -> None:
        """Fetch each feed once, rebuild all caches, and update valid timestamps."""
        with self._lock:
            self.feed_cache.clear()
            aggregate: list[Article] = []
            for subscription in self.subscriptions:
                articles = self._fetch_subscription(subscription)
                if articles is None:
                    continue
                self.feed_cache[subscription.id] = articles[:50]
                aggregate.extend(articles[:20])
                subscription.last_updated = datetime.now().astimezone().isoformat()
            aggregate.sort(key=lambda item: item.pub_date, reverse=True)
            self.feed_cache["all"] = aggregate[:50]
            self.storage.save_subscriptions(self.subscriptions)
