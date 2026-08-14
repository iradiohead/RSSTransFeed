"""Service for managing subscription storage"""
import json
import os
from typing import List
from models.subscription import Subscription


class StorageService:
    """Handles persistent storage of subscriptions"""
    
    def __init__(self, filename: str = 'subscriptions.json'):
        self.filename = filename
    
    def load_subscriptions(self) -> List[Subscription]:
        """Load subscriptions from JSON file"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [Subscription.from_dict(item) for item in data]
        except Exception as e:
            print(f"Error loading subscriptions: {e}")
        return []
    
    def save_subscriptions(self, subscriptions: List[Subscription]) -> bool:
        """Save subscriptions to JSON file"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                data = [sub.to_dict() for sub in subscriptions]
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving subscriptions: {e}")
            return False
