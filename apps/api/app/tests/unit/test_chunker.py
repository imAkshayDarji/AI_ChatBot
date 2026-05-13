"""Unit tests for document chunker."""

import pytest

from app.services.rag.chunker import Chunker


def test_chunk_text_basic() -> None:
    chunks = Chunker().chunk_text("A " * 2000)
    assert len(chunks) > 1
    assert all(len(c.text) <= 1500 for c in chunks)


def test_chunk_overlap() -> None:
    chunks = Chunker(overlap=50).chunk_text("word " * 500)
    assert len(chunks) >= 2
    shared = set(chunks[0].text.split()) & set(chunks[1].text.split())
    assert "word" in shared


def test_chunk_faq_keeps_pairs() -> None:
    faqs = [
        {"q": "How much is a small tattoo?", "a": "Starting from ₹2000 depending on..."},
        {"q": "Do you do walk-ins?", "a": "Yes, but appointments preferred..."},
    ]
    chunks = Chunker().chunk_faq(faqs)
    assert len(chunks) == 2
    assert "How much" in chunks[0].text
    assert "₹2000" in chunks[0].text


def test_empty_text_returns_empty() -> None:
    assert Chunker().chunk_text("") == []


def test_short_text_returns_single_chunk() -> None:
    chunks = Chunker().chunk_text("Short text")
    assert len(chunks) == 1


def test_chunk_faq_rejects_empty_q() -> None:
    with pytest.raises(ValueError, match="empty"):
        Chunker().chunk_faq([{"q": "", "a": "Answer"}])
