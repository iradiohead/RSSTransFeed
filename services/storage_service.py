"""Service for managing subscription storage"""
import json
import os
import sys
from typing import List
from models.subscription import Subscription


class StorageService:
    """Handles persistent storage of subscriptions"""

    def __init__(self, filename: str = 'subscriptions.json'):
        self.filename = filename
        self.base_dir = self._resolve_base_dir()
        self.storage_path = self._resolve_storage_path()

    def _resolve_base_dir(self) -> str:
        """Return the writable app data directory for bundled or source runs."""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _resolve_storage_path(self) -> str:
        """Resolve the actual file path for subscriptions.json."""
        return os.path.join(self.base_dir, self.filename)

    def get_storage_path(self) -> str:
        return self.storage_path

    def load_subscriptions(self) -> List[Subscription]:
        """Load subscriptions from JSON file"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [Subscription.from_dict(item) for item in data]
        except Exception as e:
            print(f"Error loading subscriptions: {e}")
        return []

    def save_subscriptions(self, subscriptions: List[Subscription]) -> bool:
        """Save subscriptions to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                data = [sub.to_dict() for sub in subscriptions]
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving subscriptions: {e}")
            return False
