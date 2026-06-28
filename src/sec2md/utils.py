from __future__ import annotations

import re
import statistics

NUMERIC_RE = re.compile(r"\d")


def clean_text(text: str) -> str:
    """Collapse whitespace and normalise non-breaking spaces to regular spaces."""
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def median(values: list[float]) -> float:
    """Return the median of *values*, or ``0.0`` for an empty sequence."""
    return float(statistics.median(values)) if values else 0.0
