"""Unit tests for RAG text cleaner."""

from app.services.rag.cleaner import (
    clean_text,
    detect_language,
    normalize_whitespace,
    remove_html_tags,
)


def test_clean_html() -> None:
    assert clean_text("<p>Hello <b>world</b></p>") == "Hello world"


def test_normalize_whitespace() -> None:
    assert normalize_whitespace("hello   \n\n  world") == "hello\nworld"


def test_empty_string() -> None:
    assert clean_text("") == ""
    assert clean_text("   ") == ""


def test_detect_english() -> None:
    assert detect_language("Hello, how much is a tattoo?") == "en"


def test_detect_hindi() -> None:
    assert detect_language("टैटू कितने का होता है?") == "hi"


def test_detect_gujarati() -> None:
    assert detect_language("ટેટૂ કેટલાનો આવે છે?") == "gu"


def test_remove_html_tags_plain() -> None:
    assert remove_html_tags("no tags") == "no tags"
