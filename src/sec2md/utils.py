from __future__ import annotations

import re
import statistics

NUMERIC_RE = re.compile(r"\d")
_PAREN_SPACE_RE = re.compile(r"\(\s+([\d,. ]+?)\s+\)")
_NIL_MARKER_RE = re.compile(r"^[\u2013\u2014\-]+$")


def clean_text(text: str) -> str:
    """Collapse whitespace and normalise non-breaking spaces to regular spaces."""
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def median(values: list[float]) -> float:
    """Return the median of *values*, or ``0.0`` for an empty sequence."""
    return float(statistics.median(values)) if values else 0.0
