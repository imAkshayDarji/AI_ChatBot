"""Character-window chunking with overlap (PLAN.md §7.3 MVP)."""

from __future__ import annotations

from dataclasses import dataclass, field

# Character-based windows (no tokenizer in MVP).
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
MIN_CHUNK_SIZE = 100
MAX_CHUNK_CHARS = 1500


@dataclass
class Chunk:
    text: str
    index: int
    metadata: dict[str, object] = field(default_factory=dict)


class Chunker:
    def __init__(
        self,
        chunk_size: int = CHUNK_SIZE,
        overlap: int = CHUNK_OVERLAP,
        min_chunk_size: int = MIN_CHUNK_SIZE,
        max_chunk_chars: int = MAX_CHUNK_CHARS,
    ) -> None:
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_chars = max_chunk_chars

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        """Split text into overlapping chunks with metadata."""
        base_meta: dict[str, object] = dict(metadata) if metadata else {}
        if not text or not text.strip():
            return []

        window = min(self.chunk_size, self.max_chunk_chars)
        step = max(1, window - self.overlap)
        chunks: list[Chunk] = []
        start = 0
        idx = 0

        while start < len(text):
            end = min(start + window, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        index=idx,
                        metadata={**base_meta, "chunker": "overlap_window"},
                    )
                )
                idx += 1
            if end >= len(text):
                break
            start += step

        merged = _merge_undersized(chunks, self.min_chunk_size, self.max_chunk_chars)
        sized = _enforce_max_size(merged, self.max_chunk_chars)
        return [Chunk(text=c.text, index=i, metadata=c.metadata) for i, c in enumerate(sized)]

    def chunk_faq(self, questions: list[dict]) -> list[Chunk]:
        """Keep FAQ Q&A pairs together. Each Q&A is one chunk."""
        chunks: list[Chunk] = []
        for i, row in enumerate(questions):
            if not isinstance(row, dict):
                raise ValueError(f"FAQ row {i} must be a dict with 'q' and 'a' keys")
            q = row.get("q")
            a = row.get("a")
            if not isinstance(q, str) or not isinstance(a, str):
                raise ValueError(f"FAQ row {i} requires string 'q' and 'a'")
            if not q.strip() or not a.strip():
                raise ValueError(f"FAQ row {i} has empty 'q' or 'a'")
            text = f"Q: {q.strip()}\nA: {a.strip()}"
            if len(text) > self.max_chunk_chars:
                raise ValueError(
                    f"FAQ row {i} exceeds max chunk length ({self.max_chunk_chars} chars)",
                )
            chunks.append(
                Chunk(
                    text=text,
                    index=i,
                    metadata={"chunker": "faq_pair"},
                )
            )
        return chunks


def _merge_undersized(chunks: list[Chunk], min_size: int, max_chars: int) -> list[Chunk]:
    if not chunks:
        return []
    out: list[Chunk] = []
    acc = chunks[0]

    for nxt in chunks[1:]:
        if len(acc.text) < min_size:
            joined = f"{acc.text}\n\n{nxt.text}"
            if len(joined) <= max_chars:
                acc = Chunk(
                    text=joined,
                    index=acc.index,
                    metadata={**acc.metadata, **nxt.metadata, "merged_undersized": True},
                )
                continue
        out.append(acc)
        acc = nxt
    out.append(acc)
    return out


def _enforce_max_size(chunks: list[Chunk], max_chars: int) -> list[Chunk]:
    """Hard-cap any chunk that still exceeds max (should be rare after window sizing)."""
    result: list[Chunk] = []
    for c in chunks:
        if len(c.text) <= max_chars:
            result.append(c)
            continue
        start = 0
        sub_idx = 0
        while start < len(c.text):
            result.append(
                Chunk(
                    text=c.text[start : start + max_chars],
                    index=len(result),
                    metadata={**c.metadata, "split_max": sub_idx},
                )
            )
            start += max_chars
            sub_idx += 1
    return result
