import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

class StorageService:
    def __init__(self, filename="subscriptions.json", storage_dir=None):
        """初始化存储服务。

        Args:
            filename: 订阅数据文件名。
            storage_dir: 数据目录。缺省时自动解析:打包运行时取可执行文件所在
                目录,源码运行时取项目根目录(与当前工作目录无关)。
        """
        self.filename = filename
        self.storage_dir = storage_dir if storage_dir is not None else self._resolve_base_dir()
        self.storage_path = os.path.join(self.storage_dir, filename)
        self._ensure_storage_dir_exists()

    def _resolve_base_dir(self) -> str:
        """返回可写的应用数据目录,兼容打包运行和源码运行两种方式。"""
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def get_storage_path(self) -> str:
        """返回订阅数据文件的绝对路径。"""
        return self.storage_path

    def _ensure_storage_dir_exists(self):
        """Ensure the storage directory exists"""
        os.makedirs(self.storage_dir, exist_ok=True)
    
    def save_file(self, uploaded_file):
        """Save an uploaded file to the storage directory"""
        # Create a unique filename to prevent overwrites
        file_extension = Path(uploaded_file.name).suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_filename = f"{timestamp}_{uploaded_file.name}"
        
        # Full path for the file
        file_path = os.path.join(self.storage_dir, unique_filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return file_path
    
    def list_files(self):
        """List all files in the storage directory"""
        files = []
        try:
            for filename in os.listdir(self.storage_dir):
                file_path = os.path.join(self.storage_dir, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append({
                        "name": filename,
                        "size": stat.st_size,
                        "upload_time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    })
        except Exception as e:
            raise Exception(f"Error listing files: {str(e)}")
        
        # Sort by upload time (newest first)
        files.sort(key=lambda x: x["upload_time"], reverse=True)
        return files
    
    def load_subscriptions(self):
        """Load subscriptions from the subscriptions.json file.
        
        Returns:
            List of Subscription objects
        """
        subscriptions_file = self.storage_path

        if not os.path.exists(subscriptions_file):
            # Create default subscriptions file if it doesn't exist
            self.save_subscriptions([])
            return []

        try:
            with open(subscriptions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            from models.subscription import Subscription
            subscriptions = [Subscription.from_dict(item) for item in data]
            return subscriptions
        except Exception as e:
            print(f"Error loading subscriptions: {e}")
            return []
    
    def save_subscriptions(self, subscriptions):
        """Save subscriptions to the subscriptions.json file.

        Args:
            subscriptions: List of Subscription objects

        Returns:
            bool: True if successful, False otherwise
        """
        subscriptions_file = self.storage_path

        try:
            # Convert subscriptions to dict format
            data = [sub.to_dict() for sub in subscriptions]

            with open(subscriptions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            print(f"Error saving subscriptions: {e}")

    def load_read_articles(self):
        """从 read_articles.json 读取已读文章标识。

        Returns:
            dict: 文章稳定标识 -> 阅读时间(ISO 字符串)；文件不存在或损坏时返回空字典。
        """
        path = os.path.join(self.storage_dir, "read_articles.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading read articles: {e}")
            return {}

    def save_read_articles(self, read_articles: dict) -> bool:
        """把已读文章标识写回 read_articles.json。

        Args:
            read_articles: 文章稳定标识 -> 阅读时间的字典。

        Returns:
            bool: 是否保存成功。
        """
        path = os.path.join(self.storage_dir, "read_articles.json")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(read_articles, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"Error saving read articles: {e}")
            return False
