"""Shared fixtures and helpers for sec2md tests."""

from __future__ import annotations

import textwrap

from bs4 import BeautifulSoup, Tag


def make_table(html: str) -> Tag:
    """Parse an HTML fragment and return the first ``<table>`` element."""
    soup = BeautifulSoup(textwrap.dedent(html).strip(), "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("No <table> element found in the supplied HTML")
    return table  # type: ignore[return-value]


def md_rows(md: str) -> list[list[str]]:
    """Parse a GFM pipe-table string into a list of cell-string rows.

    Separator lines (``| --- | --- |``) are skipped automatically.
    """
    rows: list[list[str]] = []
    for line in md.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        inner = stripped.strip("|")
        # Skip GFM separator / alignment rows: after removing -, |, :, and
        # spaces nothing should remain.  The pipe check is necessary because
        # split-on-| of "| --- | --- |" leaves " --- " segments that still
        # contain pipes after strip("|").
        if not inner.replace("-", "").replace("|", "").replace(":", "").replace(" ", ""):
            continue
        cells = [c.strip() for c in inner.split("|")]
        rows.append(cells)
    return rows
