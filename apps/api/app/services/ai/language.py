"""Lightweight script-based language detection."""

from __future__ import annotations

_DEVANAGARI_START = "\u0900"
_DEVANAGARI_END = "\u097f"
_GUJARATI_START = "\u0a80"
_GUJARATI_END = "\u0aff"


class LanguageService:
    def detect(self, text: str) -> str:
        has_gujarati = any(_GUJARATI_START <= c <= _GUJARATI_END for c in text)
        if has_gujarati:
            return "gu"

        has_devanagari = any(_DEVANAGARI_START <= c <= _DEVANAGARI_END for c in text)
        if has_devanagari:
            return "hi"

        return "en"

    def get_language_name(self, code: str) -> str:
        names = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}
        if code not in names:
            raise ValueError(f"Unsupported language code: {code}")
        return names[code]

    def get_supported_languages(self) -> list[dict[str, str]]:
        return [
            {"code": "en", "name": "English"},
            {"code": "hi", "name": "Hindi"},
            {"code": "gu", "name": "Gujarati"},
        ]
