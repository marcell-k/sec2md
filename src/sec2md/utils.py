from __future__ import annotations

import re
import statistics

NUMERIC_RE = re.compile(r"\d")
_NIL_MARKER_RE = re.compile(r"^[\u2013\u2014\-]+$")
_CHECKBOX_RE = re.compile(r"[\u2610\u2611\u2612\u2713\u2714]")
_BOILERPLATE_PHRASES = (
    "forward-looking statement",
    "safe harbor",
    "private securities litigation reform act",
    "indicate by check mark",
    "large accelerated filer",
    "accelerated filer",
    "smaller reporting company",
    "emerging growth company",
)


def clean_text(text: str) -> str:
    """Collapse whitespace and normalise non-breaking spaces to regular spaces."""
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def median(values: list[float]) -> float:
    """Return the median of *values*, or ``0.0`` for an empty sequence."""
    return float(statistics.median(values)) if values else 0.0


def is_boilerplate(text: str) -> bool:
    if _CHECKBOX_RE.search(text):
        return True
    text = text.lower()
    return any(phrase in text for phrase in _BOILERPLATE_PHRASES)
