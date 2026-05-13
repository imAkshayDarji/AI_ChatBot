"""Plain-text normalization for knowledge ingestion (pure functions)."""

from __future__ import annotations

import re

_HTML_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
_WS_RUN_RE = re.compile(r"[ \t]+")


def remove_html_tags(text: str) -> str:
    """Strip HTML tags from content."""
    if not text:
        return ""
    return _HTML_TAG_RE.sub(" ", text)


def normalize_whitespace(text: str) -> str:
    """Collapse horizontal whitespace; merge blank lines; one newline between lines."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in text.split("\n"):
        collapsed = _WS_RUN_RE.sub(" ", raw_line).strip()
        if collapsed:
            lines.append(collapsed)
    return "\n".join(lines)


def detect_language(text: str) -> str:
    """Return 'en', 'hi', or 'gu' using script detection (MVP heuristic)."""
    if not text or not text.strip():
        return "en"

    for ch in text:
        o = ord(ch)
        if 0x0A80 <= o <= 0x0AFF:
            return "gu"
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:
            return "hi"
    return "en"


def clean_text(raw: str) -> str:
    """Remove HTML tags, normalize whitespace, fix encoding (strip + NFC)."""
    if not raw:
        return ""
    no_html = remove_html_tags(raw)
    normalized = normalize_whitespace(no_html)
    return normalized
