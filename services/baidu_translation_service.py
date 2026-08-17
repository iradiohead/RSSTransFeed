"""Baidu Translate API client with local Argos fallback orchestration."""

from __future__ import annotations

import hashlib
import secrets

import requests

from models import Article, TranslationResult
from services.translation_service import TranslationService

BAIDU_APP_ID_KEY = "translation/baidu_app_id"
BAIDU_SECRET_KEY = "translation/baidu_secret_key"


class BaiduTranslationService:
    """Translate article text through Baidu's signed HTTP API."""

    ENDPOINT = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    MAX_QUERY_BYTES = 4500
    LANGUAGE_CODES = {
        "zh": "zh",
        "en": "en",
        "ja": "jp",
        "ko": "kor",
        "fr": "fra",
        "es": "spa",
        "de": "de",
        "it": "it",
        "ru": "ru",
        "pt": "pt",
    }

    @classmethod
    def translate_article(
        cls,
        article: Article,
        target: str,
        app_id: str,
        secret_key: str,
    ) -> TranslationResult:
        """Translate a title and its text blocks while retaining image positions."""
        target_code = cls._target_code(target)
        block_texts = [
            block["text"]
            for block in article.blocks
            if block.get("type") == "text"
        ]
        if block_texts:
            translated = cls._translate_many(
                [article.title, *block_texts],
                target_code,
                app_id,
                secret_key,
            )
            translated_blocks = translated[1:]
            return (
                translated[0],
                "\n\n".join(translated_blocks),
                translated_blocks,
            )
        return (
            cls._translate_text(article.title, target_code, app_id, secret_key),
            cls._translate_text(article.content, target_code, app_id, secret_key),
            None,
        )

    @classmethod
    def _translate_text(
        cls,
        text: str,
        target: str,
        app_id: str,
        secret_key: str,
    ) -> str:
        """Translate paragraphs in API-sized batches and preserve blank lines."""
        paragraphs = text.split("\n\n")
        nonempty = [paragraph for paragraph in paragraphs if paragraph.strip()]
        translated = iter(
            cls._translate_many(nonempty, target, app_id, secret_key)
        )
        return "\n\n".join(
            next(translated) if paragraph.strip() else paragraph
            for paragraph in paragraphs
        )

    @classmethod
    def _translate_many(
        cls,
        texts: list[str],
        target: str,
        app_id: str,
        secret_key: str,
    ) -> list[str]:
        """Batch texts under Baidu's request-size limit and restore their order."""
        if not texts:
            return []
        pieces: list[tuple[int, str]] = []
        for index, text in enumerate(texts):
            pieces.extend(
                (index, piece)
                for piece in cls._split_utf8(text.replace("\n", " "))
            )

        translated_by_index = [""] * len(texts)
        batch: list[tuple[int, str]] = []
        batch_bytes = 0
        for piece in pieces:
            piece_bytes = len(piece[1].encode("utf-8"))
            separator_bytes = 1 if batch else 0
            if batch and batch_bytes + separator_bytes + piece_bytes > cls.MAX_QUERY_BYTES:
                cls._translate_batch(
                    batch,
                    translated_by_index,
                    target,
                    app_id,
                    secret_key,
                )
                batch = []
                batch_bytes = 0
                separator_bytes = 0
            batch.append(piece)
            batch_bytes += separator_bytes + piece_bytes
        if batch:
            cls._translate_batch(
                batch,
                translated_by_index,
                target,
                app_id,
                secret_key,
            )
        return translated_by_index

    @classmethod
    def _translate_batch(
        cls,
        batch: list[tuple[int, str]],
        results: list[str],
        target: str,
        app_id: str,
        secret_key: str,
    ) -> None:
        """Translate one prepared batch and append each result to its source."""
        translated = cls._request(
            "\n".join(piece for _index, piece in batch),
            target,
            app_id,
            secret_key,
        )
        if len(translated) != len(batch):
            raise RuntimeError("Baidu returned an unexpected translation count")
        for (source_index, _piece), value in zip(batch, translated, strict=True):
            results[source_index] += value

    @classmethod
    def _request(
        cls,
        query: str,
        target: str,
        app_id: str,
        secret_key: str,
    ) -> list[str]:
        """Send one signed request and return translated result strings."""
        salt = secrets.token_hex(8)
        signature = hashlib.md5(
            f"{app_id}{query}{salt}{secret_key}".encode("utf-8")
        ).hexdigest()
        response = requests.post(
            cls.ENDPOINT,
            data={
                "q": query,
                "from": "auto",
                "to": target,
                "appid": app_id,
                "salt": salt,
                "sign": signature,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        if "error_code" in payload:
            raise RuntimeError(
                f"Baidu Translate error {payload['error_code']}: "
                f"{payload.get('error_msg', 'unknown error')}"
            )
        items = payload.get("trans_result")
        if not isinstance(items, list):
            raise RuntimeError("Baidu Translate returned an invalid response")
        return [str(item.get("dst", "")) for item in items]

    @classmethod
    def _split_utf8(cls, text: str) -> list[str]:
        """Split text without breaking characters at the UTF-8 byte limit."""
        if not text:
            return [""]
        pieces: list[str] = []
        current: list[str] = []
        current_bytes = 0
        for character in text:
            size = len(character.encode("utf-8"))
            if current and current_bytes + size > cls.MAX_QUERY_BYTES:
                pieces.append("".join(current))
                current = []
                current_bytes = 0
            current.append(character)
            current_bytes += size
        if current:
            pieces.append("".join(current))
        return pieces

    @classmethod
    def _target_code(cls, language: str) -> str:
        """Convert an operating-system locale to a Baidu language code."""
        short_code = TranslationService.short_code(language)
        target = cls.LANGUAGE_CODES.get(short_code)
        if target is None:
            raise RuntimeError(f"Baidu Translate does not support: {short_code}")
        return target


def translate_article_with_fallback(
    article: Article,
    target: str,
    app_id: str,
    secret_key: str,
) -> TranslationResult | None:
    """Use configured Baidu translation, falling back to local Argos on failure."""
    if app_id and secret_key:
        try:
            return BaiduTranslationService.translate_article(
                article,
                target,
                app_id,
                secret_key,
            )
        except (requests.RequestException, RuntimeError, ValueError):
            pass
    return TranslationService.translate_article(article, target)
