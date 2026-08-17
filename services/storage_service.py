"""Atomic JSON persistence for subscriptions and read-state data."""

from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import uuid
from collections.abc import Iterable
from pathlib import Path

from models import Subscription


def default_data_root() -> Path:
    """Return the operating system's standard per-user application-data root."""
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support"
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    return Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))


class StorageService:
    """Store application data in a writable per-user directory."""

    def __init__(self, data_dir: str | Path | None = None):
        """Create the data directory and initialize the two JSON file paths."""
        self.data_dir = (
            Path(data_dir)
            if data_dir
            else default_data_root() / "RSSTransFeed"
        )
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.subscriptions_path = self.data_dir / "subscriptions.json"
        self.read_path = self.data_dir / "read_articles.json"
        self._lock = threading.RLock()

    def migrate_legacy(self, legacy_dir: str | Path) -> None:
        """Copy legacy JSON files only when the new data files do not exist."""
        source_dir = Path(legacy_dir)
        for name, destination in (
            ("subscriptions.json", self.subscriptions_path),
            ("read_articles.json", self.read_path),
        ):
            source = source_dir / name
            if destination.exists() or not source.exists():
                continue
            try:
                shutil.copy2(source, destination)
            except OSError:
                continue

    @staticmethod
    def _read_json(path: Path, default):
        """Read JSON and return a safe default for missing or malformed files."""
        try:
            with path.open("r", encoding="utf-8") as stream:
                return json.load(stream)
        except (OSError, json.JSONDecodeError):
            return default

    def _write_json(self, path: Path, value) -> None:
        """Write JSON atomically so interruption cannot corrupt the live file."""
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with self._lock:
            try:
                with temporary.open("w", encoding="utf-8") as stream:
                    json.dump(value, stream, ensure_ascii=False, indent=2)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)

    def load_subscriptions(self) -> list[Subscription]:
        """Deserialize valid subscription objects and ignore malformed entries."""
        value = self._read_json(self.subscriptions_path, [])
        if not isinstance(value, list):
            return []
        return [
            Subscription.from_dict(item)
            for item in value
            if isinstance(item, dict)
        ]

    def save_subscriptions(self, subscriptions: Iterable[Subscription]) -> None:
        """Persist the current subscription collection."""
        self._write_json(
            self.subscriptions_path,
            [subscription.to_dict() for subscription in subscriptions],
        )

    def load_read_articles(self) -> dict[str, str]:
        """Load stable article keys mapped to ISO read timestamps."""
        value = self._read_json(self.read_path, {})
        return value if isinstance(value, dict) else {}

    def save_read_articles(self, value: dict[str, str]) -> None:
        """Persist stable article keys mapped to ISO read timestamps."""
        self._write_json(self.read_path, value)
