"""Persistent read-state management for articles."""

from __future__ import annotations

from datetime import datetime, timedelta

from models import Article
from services.storage_service import StorageService


class ReadState:
    """Track recently read article keys and keep the JSON file bounded."""

    def __init__(
        self,
        storage: StorageService,
        max_age_days: int = 90,
        max_entries: int = 5000,
    ):
        """Load read markers and discard entries beyond age and count limits."""
        self.storage = storage
        self.max_entries = max_entries
        cutoff = (
            datetime.now().astimezone() - timedelta(days=max_age_days)
        ).isoformat()
        values = {
            key: timestamp
            for key, timestamp in storage.load_read_articles().items()
            if isinstance(timestamp, str) and timestamp >= cutoff
        }
        self.values = self._newest(values)

    def _newest(self, values: dict[str, str]) -> dict[str, str]:
        """Return only the newest read markers within the configured limit."""
        ordered = sorted(values.items(), key=lambda item: item[1], reverse=True)
        return dict(ordered[: self.max_entries])

    def contains(self, article: Article) -> bool:
        """Return whether the article's stable key has been marked as read."""
        return article.key in self.values

    def mark(self, article: Article) -> None:
        """Mark an article read and immediately persist the updated state."""
        self.values[article.key] = datetime.now().astimezone().isoformat()
        self.values = self._newest(self.values)
        self.storage.save_read_articles(self.values)
