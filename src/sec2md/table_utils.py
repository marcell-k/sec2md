"""Table processing utilities for converting SEC HTML tables to Markdown.

Pipeline:
  1. Build a 2-D grid, expanding ``colspan`` / ``rowspan`` attributes.
     Cell text extraction purposely excludes text from nested ``<table>``
     elements so that layout tables (whose cells contain data tables) produce
     an empty grid and are silently discarded.
  2. Remove columns that are entirely whitespace (visual spacer columns).
  3. Merge currency-symbol-only columns (``$``, ``€`` …) with the adjacent
     value column to their right.
  4. Remove separator rows (cells composed entirely of dashes / underscores).
  5. Render as a GFM pipe table, using the first non-empty row as the header.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bs4 import NavigableString

if TYPE_CHECKING:
    from bs4.element import Tag

# ---------------------------------------------------------------------------
# Compiled patterns
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r"^[\s\u00a0]*$")
_CURRENCY_RE = re.compile(r"^[\$€£¥₩()]+$")
_SEPARATOR_RE = re.compile(r"^[-\u2013\u2014_\s\u00a0]+$")


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _cell_text(cell: Tag) -> str:
    """Return the stripped text of *cell*, **ignoring** any nested ``<table>`` content.

    SEC layout tables wrap data tables inside their cells.  A naive
    ``get_text()`` call would pull every number from the nested data table into
    a single cell string.  Instead, we walk the descendant text nodes and skip
    any that have a ``<table>`` ancestor between them and *cell*.
    """
    parts: list[str] = []
    for node in cell.descendants:
        if not isinstance(node, NavigableString):
            continue
        # Walk up from the text node; if we hit a nested <table> before
        # reaching our cell, this text belongs to that nested table → skip.
        in_nested_table = False
        for ancestor in node.parents:
            if ancestor is cell:
                break
            if getattr(ancestor, "name", None) == "table":
                in_nested_table = True
                break
        if not in_nested_table:
            parts.append(str(node))
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _parse_int(value: object, default: int = 1) -> int:
    try:
        return max(1, int(str(value)))  # type: ignore[arg-type]
    except ValueError, TypeError:
        return default


def _is_empty(text: str) -> bool:
    return bool(_WHITESPACE_RE.match(text))


def _is_currency_symbol(text: str) -> bool:
    return bool(text) and bool(_CURRENCY_RE.match(text))


def _escape_pipe(text: str) -> str:
    return text.replace("|", "\\|")


# ---------------------------------------------------------------------------
# Step 1 – build the 2-D grid
# ---------------------------------------------------------------------------


def _ensure_rows(grid: list[list[str | None]], min_len: int) -> None:
    while len(grid) < min_len:
        grid.append([])


def _ensure_width(row: list[str | None], min_len: int) -> None:
    while len(row) < min_len:
        row.append(None)


def _build_grid(table: Tag) -> list[list[str]]:
    """Expand an HTML table into a rectangular 2-D grid of strings.

    Only ``<tr>`` elements whose nearest ``<table>`` ancestor is *table* are
    processed; rows that belong to nested tables are skipped (those tables are
    rendered when encountered as their own top-level block).
    """
    grid: list[list[str | None]] = []

    for tr in table.find_all("tr", recursive=True):
        if tr.find_parent("table") is not table:
            continue

        row_idx = len(grid)
        grid.append([])

        col_idx = 0
        for cell in tr.find_all(["td", "th"], recursive=False):
            while col_idx < len(grid[row_idx]) and grid[row_idx][col_idx] is not None:
                col_idx += 1

            text = _cell_text(cell)
            colspan = _parse_int(cell.get("colspan", 1))
            rowspan = _parse_int(cell.get("rowspan", 1))

            _ensure_width(grid[row_idx], col_idx + colspan)
            for c in range(colspan):
                grid[row_idx][col_idx + c] = text

            for r in range(1, rowspan):
                future = row_idx + r
                _ensure_rows(grid, future + 1)
                _ensure_width(grid[future], col_idx + colspan)
                for c in range(colspan):
                    grid[future][col_idx + c] = text

            col_idx += colspan

    if not grid:
        return []

    num_cols = max(len(row) for row in grid)
    result: list[list[str]] = []
    for row in grid:
        padded = [(cell if cell is not None else "") for cell in row]
        padded += [""] * (num_cols - len(padded))
        result.append(padded)
    return result


# ---------------------------------------------------------------------------
# Step 2 – remove empty columns
# ---------------------------------------------------------------------------


def _remove_empty_columns(grid: list[list[str]]) -> list[list[str]]:
    if not grid:
        return grid
    num_cols = len(grid[0])
    keep = [c for c in range(num_cols) if any(not _is_empty(row[c]) for row in grid)]
    if len(keep) == num_cols:
        return grid
    return [[row[c] for c in keep] for row in grid]


# ---------------------------------------------------------------------------
# Step 3 – merge currency-symbol columns
# ---------------------------------------------------------------------------


def _merge_currency_columns(grid: list[list[str]]) -> list[list[str]]:
    if not grid or len(grid[0]) < 2:
        return grid

    num_cols = len(grid[0])
    currency_cols: set[int] = set()
    for c in range(num_cols - 1):
        non_empty = [row[c] for row in grid if not _is_empty(row[c])]
        if non_empty and all(_is_currency_symbol(v) for v in non_empty):
            currency_cols.add(c)

    if not currency_cols:
        return grid

    result: list[list[str]] = []
    for row in grid:
        new_row: list[str] = []
        skip = False
        for c, val in enumerate(row):
            if skip:
                skip = False
                continue
            if c in currency_cols:
                sym = val.strip()
                nxt = row[c + 1].strip() if c + 1 < len(row) else ""
                new_row.append(f"{sym} {nxt}".strip() if sym and nxt else sym or nxt)
                skip = True
            else:
                new_row.append(val)
        result.append(new_row)
    return result


# ---------------------------------------------------------------------------
# Step 4 – remove separator rows
# ---------------------------------------------------------------------------


def _remove_separator_rows(grid: list[list[str]]) -> list[list[str]]:
    result: list[list[str]] = []
    for row in grid:
        non_empty = [c for c in row if not _is_empty(c)]
        if non_empty and all(_SEPARATOR_RE.match(c) for c in non_empty):
            continue
        result.append(row)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def table_to_markdown(table: Tag) -> str:
    """Convert an HTML ``<table>`` element to a GFM pipe-table string.

    Returns an empty string for layout tables (cells empty after nested-table
    text is stripped) or tables with fewer than two rows of content.
    """
    grid = _build_grid(table)
    if not grid:
        return ""

    grid = _remove_empty_columns(grid)
    grid = _merge_currency_columns(grid)
    grid = _remove_separator_rows(grid)
    grid = [row for row in grid if any(not _is_empty(c) for c in row)]

    if len(grid) < 2:  # need at least a header row + one data row
        return ""

    num_cols = len(grid[0])
    if num_cols == 0:
        return ""

    header = [_escape_pipe(c) for c in grid[0]]
    separator = ["---"] * num_cols
    data_rows = [[_escape_pipe(c) for c in row] for row in grid[1:]]

    def _fmt(cells: list[str]) -> str:
        return "| " + " | ".join(cells) + " |"

    lines = [_fmt(header), _fmt(separator)]
    lines.extend(_fmt(row) for row in data_rows)
    return "\n".join(lines)
