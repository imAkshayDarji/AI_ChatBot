"""Parse model output helpers."""

from __future__ import annotations

import json
import re


def strip_html_scripts(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", text)
    return without_tags.replace("<", "").replace(">", "")


def split_suggestions(content: str) -> tuple[str, list[str]]:
    marker = "SUGGESTED_REPLIES_JSON:"
    if marker not in content:
        return content.strip(), []
    front, tail = content.rsplit(marker, 1)
    raw_json = tail.strip().splitlines()[0] if tail.strip() else "[]"
    try:
        data = json.loads(raw_json.strip())
        if isinstance(data, list):
            cleaned = [str(x).strip() for x in data if str(x).strip()]
            return front.strip(), cleaned[:6]
    except json.JSONDecodeError:
        pass
    return front.strip(), []


def build_conversation_preview(
    history: list[dict[str, str]],
    user_message: str,
    max_chars: int = 400,
) -> str:
    chunks: list[str] = []
    for m in history[-8:]:
        if m["role"] == "user":
            chunks.append(m["content"])
    chunks.append(user_message)
    text = " | ".join(chunks).strip()
    return text[:max_chars]
