import hashlib
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import requests

from models import Article, Subscription
from services import (
    BaiduTranslationService,
    FeedService,
    ReadState,
    StorageService,
    SubscriptionManager,
    TranslationService,
    translate_article_with_fallback,
)
from ui.main_window import MainWindow
from utils.article_extractor import extract_article_content, strip_html


def test_storage_round_trip(tmp_path):
    """Read-state JSON should survive an atomic save/load round trip."""
    storage = StorageService(tmp_path)
    storage.save_read_articles({"article": "2026-08-17T10:00:00"})
    assert storage.load_read_articles() == {"article": "2026-08-17T10:00:00"}
    assert json.loads(storage.read_path.read_text(encoding="utf-8"))["article"]


def test_malformed_subscription_shape_falls_back_to_empty(tmp_path):
    """A structurally invalid subscriptions file should not crash startup."""
    storage = StorageService(tmp_path)
    storage.subscriptions_path.write_text('{"not": "a list"}', encoding="utf-8")
    assert storage.load_subscriptions() == []


def test_read_state_marks_articles(tmp_path):
    """Marking an article should update memory and persistent JSON."""
    storage = StorageService(tmp_path)
    article = Article("Title", "https://example.com", "Body")
    state = ReadState(storage)
    state.mark(article)
    assert state.contains(article)
    assert article.key in storage.load_read_articles()


def test_read_state_keeps_entry_limit_after_new_marks(tmp_path):
    """Adding a marker should not let read-state grow beyond its size limit."""
    now = datetime.now().astimezone()
    storage = StorageService(tmp_path)
    storage.save_read_articles(
        {
            "old": (now - timedelta(minutes=2)).isoformat(),
            "recent": (now - timedelta(minutes=1)).isoformat(),
        }
    )
    state = ReadState(storage, max_entries=2)
    state.mark(Article("Newest", "https://example.com/newest", "Body"))
    assert len(state.values) == 2
    assert "https://example.com/newest" in state.values
    assert "old" not in state.values


def test_refresh_fetches_each_feed_once_and_reuses_cache(tmp_path, monkeypatch):
    """Refreshing should populate caches without a second request from the UI."""
    storage = StorageService(tmp_path)
    storage.save_subscriptions(
        [
            Subscription("1", "https://one.example/rss", "One"),
            Subscription("2", "https://two.example/rss", "Two"),
        ]
    )
    calls: list[str] = []

    def fake_fetch(url):
        """Return one deterministic feed entry while recording its URL."""
        calls.append(url)
        return SimpleNamespace(
            entries=[{"title": url, "link": url, "summary": "summary"}],
            feed={"title": url},
        )

    monkeypatch.setattr(FeedService, "fetch_feed", fake_fetch)
    manager = SubscriptionManager(storage)
    manager.refresh_all()
    assert len(calls) == 2
    assert len(manager.get_articles(None)) == 2
    assert len(calls) == 2


def test_failed_feed_load_is_not_cached(tmp_path, monkeypatch):
    """A transient network failure should be retried on the next feed load."""
    storage = StorageService(tmp_path)
    storage.save_subscriptions(
        [Subscription("1", "https://example.com/rss", "Example")]
    )
    calls = 0

    def flaky_fetch(url):
        """Fail once, then return a valid feed to exercise retry behavior."""
        nonlocal calls
        calls += 1
        if calls == 1:
            raise requests.RequestException("temporary failure")
        return SimpleNamespace(
            entries=[{"title": "Recovered", "link": url, "summary": "summary"}],
            feed={"title": "Example"},
        )

    monkeypatch.setattr(FeedService, "fetch_feed", flaky_fetch)
    manager = SubscriptionManager(storage)
    assert manager.get_articles("1") == []
    assert "1" not in manager.feed_cache
    assert len(manager.get_articles("1")) == 1
    assert calls == 2


def test_strip_html():
    """RSS HTML fragments should become plain readable text."""
    assert strip_html("<p>Hello <strong>world</strong></p>").strip() == "Hello world"


def test_content_extraction_filters_noise():
    """Article extraction should retain content while filtering page chrome."""
    source = """
    <html><head><meta property="og:title" content="Example"></head><body>
      <nav>Navigation must disappear</nav>
      <article>
        <p>This is the first sufficiently long paragraph in the article body.</p>
        <img src="/hero.jpg">
        <p>This is the second sufficiently long paragraph in the article body.</p>
        <div class="related-articles">Unrelated recommendation</div>
      </article>
    </body></html>
    """
    text, blocks, metadata = extract_article_content(
        source, "https://example.com/post"
    )
    assert "first sufficiently long" in text
    assert "Navigation" not in text
    assert "recommendation" not in text
    assert metadata["title"] == "Example"
    assert any(block.get("src") == "https://example.com/hero.jpg" for block in blocks)


def test_article_stable_key():
    """Article keys should prefer GUID, then URL, then title."""
    assert Article("Title", "https://example.com", "Body", guid="abc").key == "abc"
    assert Article("Title", "https://example.com", "Body").key == "https://example.com"


def test_article_image_urls_are_unique_and_ordered():
    """Article image helpers should merge block and fallback URLs predictably."""
    article = Article(
        "Title",
        "https://example.com",
        "Body",
        blocks=[
            {"type": "image", "src": "https://example.com/one.jpg"},
            {"type": "text", "text": "Paragraph"},
        ],
        extra_image_urls=[
            "https://example.com/one.jpg",
            "https://example.com/two.jpg",
        ],
    )
    assert article.image_urls == [
        "https://example.com/one.jpg",
        "https://example.com/two.jpg",
    ]


def test_background_content_does_not_cancel_active_translation():
    """Only content changes on the active article should advance its task token."""
    active = Article("Active", "https://example.com/active", "Body")
    background = Article(
        "Background",
        "https://example.com/background",
        "Body",
        translated_title="Translated",
        translated_content="Translated body",
    )
    window_state = SimpleNamespace(
        viewed_article=active,
        _translation_generation=3,
    )

    MainWindow._clear_translation_after_content_change(window_state, background)
    assert window_state._translation_generation == 3
    assert not background.translated_content

    MainWindow._clear_translation_after_content_change(window_state, active)
    assert window_state._translation_generation == 4


def test_refresh_restores_article_by_stable_key():
    """Refresh selection restoration should locate the rebuilt article object."""
    first = Article("First", "https://example.com/first", "Body")
    selected = Article("Selected", "https://example.com/selected", "Body")
    selected_rows: list[int] = []
    window_state = SimpleNamespace(
        _pending_article_selection=(None, selected.key),
        current_subscription_id=None,
        current_articles=[first, selected],
        article_list=SimpleNamespace(setCurrentRow=selected_rows.append),
    )

    MainWindow._restore_pending_article_selection(window_state)
    assert selected_rows == [1]
    assert window_state._pending_article_selection is None


def test_translation_short_code():
    """Locale normalization should produce Argos-compatible language codes."""
    assert TranslationService.short_code("zh-CN") == "zh"
    assert TranslationService.short_code("en_US") == "en"


def test_translation_pair_selection():
    """Translation should prefer direct models and otherwise pivot through English."""
    assert TranslationService._translation_pairs("fr", "de", True) == [("fr", "de")]
    assert TranslationService._translation_pairs("fr", "de", False) == [
        ("fr", "en"),
        ("en", "de"),
    ]


def test_baidu_translation_signs_and_batches_article(monkeypatch):
    """Baidu translation should sign one batch and preserve text-block order."""
    captured: dict = {}

    class Response:
        """Minimal successful requests response used by the API client."""

        @staticmethod
        def raise_for_status():
            """Represent a successful HTTP status."""

        @staticmethod
        def json():
            """Return one translated result for each submitted line."""
            return {
                "trans_result": [
                    {"dst": "标题"},
                    {"dst": "第一段"},
                    {"dst": "第二段"},
                ]
            }

    def fake_post(url, data, timeout):
        """Capture the signed request and return deterministic translations."""
        captured.update(url=url, data=data, timeout=timeout)
        return Response()

    monkeypatch.setattr(
        "services.baidu_translation_service.secrets.token_hex",
        lambda _size: "fixed-salt",
    )
    monkeypatch.setattr(
        "services.baidu_translation_service.requests.post",
        fake_post,
    )
    article = Article(
        "Title",
        "https://example.com",
        "Body",
        blocks=[
            {"type": "text", "text": "First"},
            {"type": "image", "src": "https://example.com/image.jpg"},
            {"type": "text", "text": "Second"},
        ],
    )

    result = BaiduTranslationService.translate_article(
        article,
        "zh-CN",
        "app-id",
        "secret",
    )
    query = "Title\nFirst\nSecond"
    expected_sign = hashlib.md5(
        f"app-id{query}fixed-saltsecret".encode()
    ).hexdigest()
    assert result == ("标题", "第一段\n\n第二段", ["第一段", "第二段"])
    assert captured["data"]["q"] == query
    assert captured["data"]["sign"] == expected_sign
    assert captured["data"]["to"] == "zh"


def test_baidu_failure_falls_back_to_local_translation(monkeypatch):
    """Online API errors should transparently invoke the local translator."""
    expected = ("Local title", "Local body", None)

    def fail_online(*_args):
        """Simulate an API-level Baidu failure."""
        raise RuntimeError("invalid credentials")

    monkeypatch.setattr(
        BaiduTranslationService,
        "translate_article",
        fail_online,
    )
    monkeypatch.setattr(
        TranslationService,
        "translate_article",
        lambda *_args: expected,
    )
    article = Article("Title", "https://example.com", "Body")
    assert translate_article_with_fallback(
        article,
        "zh-CN",
        "app-id",
        "secret",
    ) == expected
