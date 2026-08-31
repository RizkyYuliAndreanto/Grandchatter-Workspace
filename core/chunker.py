"""Sentence chunking for long scripts: split at sentence punctuation, then at
commas, then at words. Input MUST already be normalized (pipeline order is law,
see tasks/flows/flow-pipeline.md). Pure string work — no normalizer import here.
"""
import re

SENTENCE_SPLIT = re.compile(r"(?<=[.?!:])\s+")
MAX_CHARS_DEFAULT = 250


def _split_long(sentence: str, max_chars: int) -> list[str]:
    """Split an over-long sentence: commas first, then forced word boundaries."""
    if len(sentence) <= max_chars:
        return [sentence]

    parts = re.split(r"(?<=[,;])\s+", sentence)
    # Merge consecutive short parts greedily (fewer chunks = more natural speech).
    merged: list[str] = []
    buf = ""
    for part in parts:
        candidate = f"{buf} {part}".strip()
        if len(candidate) <= max_chars or not buf:
            buf = candidate
        else:
            merged.append(buf)
            buf = part
    if buf:
        merged.append(buf)

    # Comma split insufficient (single clause > max) -> force at word boundary.
    out: list[str] = []
    for piece in merged:
        while len(piece) > max_chars:
            cut = piece.rfind(" ", 0, max_chars + 1)
            if cut <= 0:  # single monster word — never expected in Indonesian
                cut = max_chars
            out.append(piece[:cut].strip())
            piece = piece[cut:].strip()
        if piece:
            out.append(piece)
    return out


def _reattach_colon(chunks: list[str]) -> list[str]:
    """Sentence split on ':' cuts 'Kalimat ketiga:' from its completion. A colon
    ending a chunk is mid-sentence, not a boundary — glue it to the next chunk."""
    out: list[str] = []
    for c in chunks:
        if out and out[-1].endswith(":"):
            out[-1] = f"{out[-1]} {c}"
        else:
            out.append(c)
    return out


def chunk_text(text: str, max_chars: int = MAX_CHARS_DEFAULT) -> list[str]:
    """Normalized text -> list of chunks, each <= max_chars, punctuation kept."""
    sentences = [s.strip() for s in SENTENCE_SPLIT.split(text.strip()) if s.strip()]
    chunks: list[str] = []
    for sentence in sentences:
        chunks.extend(_split_long(sentence, max_chars))
    return [c for c in _reattach_colon(chunks) if c]


def chunks_with_index(chunks: list[str]) -> list[tuple[int, str]]:
    """1-based (index, text) pairs — used for chunk_0001.wav naming."""
    return list(enumerate(chunks, start=1))
