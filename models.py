"""Application data models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

ArticleBlock = dict[str, str]
TranslationResult = tuple[str, str, list[str] | None]


@dataclass(slots=True)
class Subscription:
    """Persistent metadata for one RSS subscription."""

    id: str
    url: str
    title: str
    last_updated: str = field(
        default_factory=lambda: datetime.now().astimezone().isoformat()
    )

    @classmethod
    def from_dict(cls, data: dict) -> Subscription:
        """Build a subscription from a tolerant JSON dictionary."""
        return cls(
            id=str(data.get("id", "")),
            url=data.get("url", ""),
            title=data.get("title", "Untitled Feed"),
            last_updated=data.get("last_updated")
            or datetime.now().astimezone().isoformat(),
        )

    def to_dict(self) -> dict:
        """Serialize the subscription for JSON persistence."""
        return asdict(self)


@dataclass
class Article:
    """Article content plus session-only translation and image state."""

    title: str
    link: str
    content: str
    pub_date: str = ""
    author: str = ""
    feed_title: str = ""
    guid: str = ""
    read: bool = False
    translated_title: str = ""
    translated_content: str = ""
    translated_block_texts: list[str] | None = None
    blocks: list[ArticleBlock] = field(default_factory=list)
    extra_image_urls: list[str] = field(default_factory=list)
    image_data: dict[str, bytes] = field(default_factory=dict)
    image_states: dict[str, str] = field(default_factory=dict)
    page_fetched: bool = False
    full_text_failed: bool = False

    @property
    def key(self) -> str:
        """Return the most stable available identifier for read-state tracking."""
        return self.guid or self.link or self.title

    @property
    def image_urls(self) -> list[str]:
        """Return unique image URLs while preserving their display order."""
        block_urls = [
            block["src"]
            for block in self.blocks
            if block.get("type") == "image" and block.get("src")
        ]
        return list(dict.fromkeys(block_urls + self.extra_image_urls))

    def clear_translation(self) -> None:
        """Discard translated fields after the original article text changes."""
        self.translated_title = ""
        self.translated_content = ""
        self.translated_block_texts = None
