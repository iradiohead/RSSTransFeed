"""Offline language detection and Argos translation."""

from __future__ import annotations

import locale
import os
import re
import threading

from models import Article, TranslationResult


class TranslationService:
    """Detect article language and translate locally to the system language."""

    _lock = threading.Lock()

    class _Sentencizer:
        """Split text locally so Argos never downloads an external tokenizer."""

        @staticmethod
        def split_sentences(text: str) -> list[str]:
            """Split sentences at common western and CJK punctuation."""
            return [
                part
                for part in re.split(r"(?<=[.!?。！？])\s+", text)
                if part.strip()
            ]

    @staticmethod
    def os_language() -> str:
        """Return the operating-system UI locale as a standard language tag."""
        if os.name == "nt":
            import ctypes

            value = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(value, len(value)):
                return value.value
        language = locale.getlocale()[0] or os.environ.get("LANG", "en")
        return language.split(".", 1)[0].replace("_", "-") or "en"

    @staticmethod
    def short_code(language: str) -> str:
        """Normalize a locale such as zh-CN or en_US to an Argos language code."""
        return (language or "").replace("_", "-").split("-", 1)[0].lower()

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detect the dominant language from a bounded local text sample."""
        from langdetect import detect

        sample = (text or "").strip()[:2000]
        return cls.short_code(detect(sample)) if sample else ""

    @classmethod
    def needs_translation(cls, text: str, target: str | None = None) -> bool:
        """Return whether text language differs from the target system language."""
        return bool(text.strip()) and cls.detect_language(text) != cls.short_code(
            target or cls.os_language()
        )

    @classmethod
    def _installed_translator(cls, source: str, target: str):
        """Return an installed Argos translator, or None when its model is absent."""
        import argostranslate.translate

        languages = {
            language.code: language
            for language in argostranslate.translate.get_installed_languages()
        }
        if source not in languages or target not in languages:
            return None
        try:
            translator = languages[source].get_translation(languages[target])
            cls._use_local_sentencizer(translator)
            return translator
        except (AttributeError, RuntimeError, ValueError):
            return None

    @classmethod
    def _use_local_sentencizer(cls, translator) -> None:
        """Replace Argos tokenizers recursively with the local sentence splitter."""
        if hasattr(translator, "sentencizer"):
            translator.sentencizer = cls._Sentencizer()
        for name in ("underlying", "t1", "t2"):
            child = getattr(translator, name, None)
            if child is not None:
                cls._use_local_sentencizer(child)

    @classmethod
    def _get_translator(cls, source: str, target: str):
        """Load a local model, downloading direct or English-pivot models once."""
        translator = cls._installed_translator(source, target)
        if translator:
            return translator

        import argostranslate.package

        argostranslate.package.update_package_index()
        packages = argostranslate.package.get_available_packages()
        direct = any(
            item.from_code == source and item.to_code == target for item in packages
        )
        pairs = cls._translation_pairs(source, target, direct)
        for from_code, to_code in pairs:
            if cls._installed_translator(from_code, to_code):
                continue
            package = next(
                (
                    item
                    for item in packages
                    if item.from_code == from_code and item.to_code == to_code
                ),
                None,
            )
            if package is None:
                raise RuntimeError(
                    f"No local Argos model is available for {from_code} → {to_code}"
                )
            argostranslate.package.install_from_path(package.download())

        translator = cls._installed_translator(source, target)
        if translator is None:
            raise RuntimeError(f"Cannot load local model: {source} → {target}")
        return translator

    @staticmethod
    def _translation_pairs(
        source: str, target: str, direct_available: bool
    ) -> list[tuple[str, str]]:
        """Choose a direct model or the minimal set of English-pivot models."""
        if direct_available:
            return [(source, target)]
        return [
            pair
            for pair in ((source, "en"), ("en", target))
            if pair[0] != pair[1]
        ]

    @staticmethod
    def _translate_text(text: str, translator) -> str:
        """Translate text in bounded paragraphs to avoid model token limits."""
        return "\n\n".join(
            TranslationService._translate_paragraph(paragraph, translator)
            for paragraph in text.split("\n\n")
        )

    @staticmethod
    def _translate_paragraph(paragraph: str, translator) -> str:
        """Translate one paragraph in chunks small enough for Argos models."""
        if not paragraph.strip():
            return paragraph
        return "".join(
            translator.translate(paragraph[index : index + 500])
            for index in range(0, len(paragraph), 500)
        )

    @classmethod
    def translate_article(
        cls, article: Article, target: str | None = None
    ) -> TranslationResult | None:
        """Translate an article and preserve text-block positions around images."""
        target_code = cls.short_code(target or cls.os_language())
        source_code = cls.detect_language(f"{article.title}\n{article.content}")
        if not source_code or source_code == target_code:
            return None

        with cls._lock:
            translator = cls._get_translator(source_code, target_code)
            texts = [
                block["text"]
                for block in article.blocks
                if block.get("type") == "text"
            ]
            translated_blocks = [
                cls._translate_text(text, translator) for text in texts
            ]
            title = cls._translate_text(article.title, translator)
            content = (
                "\n\n".join(translated_blocks)
                if texts
                else cls._translate_text(article.content, translator)
            )
            return title, content, translated_blocks if texts else None
