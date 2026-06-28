"""Table processing utilities for converting SEC HTML tables to Markdown.

Pipeline (in order):
  1. ``_build_grid``              – expand colspan/rowspan into a 2-D string grid;
                                    nested-table text is excluded so layout tables
                                    produce an empty grid and are silently discarded.
  2. ``_remove_empty_columns``    – drop visual spacer columns (pass 1).
  3. ``_merge_currency_prefixes`` – **(new)** row-level: move a bare ``$``/``€``
                                    cell into the adjacent value cell so the now-
                                    empty currency slot allows dedup to fire.
  4. ``_remove_empty_columns``    – drop the newly-emptied currency-symbol columns
                                    (pass 2); prevents them from being absorbed by
                                    the description column during dedup.
  5. ``_merge_percent_suffixes``  – **(new)** row-level: append a bare ``%`` cell
                                    to the preceding numeric value cell.
  6. ``_deduplicate_columns``     – collapse adjacent columns that carry identical
                                    information (handles iXBRL / Workiva ``colspan``
                                    header duplication correctly after passes 3-5).
  7. ``_remove_empty_columns``    – mop up any residual empty columns (pass 3).
  8. ``_merge_currency_columns``  – fallback for simple tables where an entire
                                    column contains only currency symbols.
  9. ``_remove_separator_rows``   – drop rows composed entirely of dashes/underscores.
  10. drop all-empty rows.
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
# Matches any decimal digit — used to guard currency/percent merges so they
# never fire on alphabetic header cells such as "Amount" or "Average Rate".
_NUMERIC_RE = re.compile(r"\d")


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _cell_text(cell: Tag) -> str:
    """Return the stripped text of *cell*, **ignoring** any nested ``<table>`` content.

    SEC layout tables wrap data tables inside their cells.  A naive
    ``get_text()`` call would pull every number from the nested data table into
    a single cell string.  Instead we walk the descendant text nodes and skip
    any that have a ``<table>`` ancestor between them and *cell*.
    """
    parts: list[str] = []
    for node in cell.descendants:
        if not isinstance(node, NavigableString):
            continue
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
    processed; rows that belong to nested tables are skipped.
    """
    grid: list[list[str | None]] = []

    # Use an explicit counter so that rowspan pre-filling (which calls
    # _ensure_rows and inserts future rows into grid) does not advance
    # row_idx for subsequent <tr> elements.  Without this, tr[1] would be
    # placed at len(grid)==3 instead of row 1 when tr[0] had rowspan=3.
    tr_index = 0

    for tr in table.find_all("tr", recursive=True):
        if tr.find_parent("table") is not table:
            continue

        row_idx = tr_index
        tr_index += 1
        _ensure_rows(grid, row_idx + 1)

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
# Step 2 / 4 / 7 – remove empty columns
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
# Step 3 – merge bare currency-symbol cells into adjacent value cells (row-level)
# ---------------------------------------------------------------------------


def _merge_currency_prefixes(grid: list[list[str]]) -> list[list[str]]:
    """Row-level pass: move a bare currency symbol into the adjacent value cell.

    Transforms ``(col_A="$", col_B="26,945")`` →
                ``(col_A="",  col_B="$ 26,945")``.

    The guard ``_NUMERIC_RE.search(col_B)`` ensures the merge only fires when
    *col_B* contains at least one digit, preventing a ``"$"`` header cell from
    being glued to an alphabetic column-name header such as ``"Amount"``.

    After this pass the now-empty ``col_A`` cells allow the subsequent
    ``_remove_empty_columns`` + ``_deduplicate_columns`` steps to collapse the
    duplicate column pair that arises in iXBRL / Workiva tables, where:

    * currency-prefixed rows use  ``<td>$</td><td>value</td>``
    * plain-value rows use        ``<td colspan="2">value</td>``
    """
    result = []
    for row in grid:
        new_row = list(row)
        for c in range(len(new_row) - 1):
            if (
                _is_currency_symbol(new_row[c].strip())
                and not _is_empty(new_row[c + 1])
                and bool(_NUMERIC_RE.search(new_row[c + 1]))
            ):
                new_row[c + 1] = f"{new_row[c].strip()} {new_row[c + 1]}".strip()
                new_row[c] = ""
        result.append(new_row)
    return result


# ---------------------------------------------------------------------------
# Step 5 – merge bare percent-sign cells into preceding value cells (row-level)
# ---------------------------------------------------------------------------


def _merge_percent_suffixes(grid: list[list[str]]) -> list[list[str]]:
    """Row-level pass: append a bare ``%`` cell to the preceding numeric cell.

    Transforms ``(col_A="3.6", col_B="%")`` →
                ``(col_A="3.6%", col_B="")``.

    The guard ``_NUMERIC_RE.search(col_A)`` ensures the merge only fires when
    *col_A* contains at least one digit, so header cells (e.g. ``"Average
    Rate¹"``) and ``"N/A"`` values are left untouched — neither would produce
    ``"Average Rate¹%"`` or ``"N/A%"``.

    Combined with ``_merge_currency_prefixes`` this enables
    ``_deduplicate_columns`` to collapse *both* duplicate column pairs that
    arise from iXBRL ``colspan`` header rows (one pair for the amount column,
    one pair for the rate column).
    """
    result = []
    for row in grid:
        new_row = list(row)
        for c in range(1, len(new_row)):
            if new_row[c].strip() == "%" and not _is_empty(new_row[c - 1]) and bool(_NUMERIC_RE.search(new_row[c - 1])):
                new_row[c - 1] = f"{new_row[c - 1].strip()}%"
                new_row[c] = ""
        result.append(new_row)
    return result


# ---------------------------------------------------------------------------
# Step 6 – deduplicate adjacent columns
# ---------------------------------------------------------------------------


def _deduplicate_columns(grid: list[list[str]]) -> list[list[str]]:
    """Collapse adjacent columns that carry identical information.

    Two neighbouring columns *A* and *B* are merged when, for **every** row,
    the pair satisfies at least one of:

    * ``row[A] == row[B]``  – identical values (e.g. colspan-expanded header), or
    * ``row[A]`` is blank   – A carries no extra information, or
    * ``row[B]`` is blank   – B carries no extra information.

    The merged column takes the non-blank value (or either when both are equal
    and non-blank).

    The scan is left-to-right and stays at the current index after each merge
    so that a run of N identical columns collapses in a single pass.

    **Why this works after** ``_merge_currency_prefixes`` **+**
    ``_merge_percent_suffixes``:

    Before those passes the ``$`` rows had ``(col_A="$", col_B="26,945")``,
    which is neither equal nor blank — blocking the merge.  After the
    row-level passes the same rows become ``(col_A="", col_B="$ 26,945")``,
    which satisfies the blank-A condition, so the entire column pair is now
    mergeable.
    """
    if not grid or len(grid[0]) < 2:
        return grid

    num_rows = len(grid)
    num_cols = len(grid[0])

    cols: list[list[str]] = [[grid[r][c] for r in range(num_rows)] for c in range(num_cols)]

    i = 0
    while i < len(cols) - 1:
        a_col, b_col = cols[i], cols[i + 1]
        mergeable = all(_is_empty(va) or _is_empty(vb) or va == vb for va, vb in zip(a_col, b_col))
        if mergeable:
            cols[i] = [va if not _is_empty(va) else vb for va, vb in zip(a_col, b_col)]
            cols.pop(i + 1)
        else:
            i += 1

    if not cols:
        return []
    return [[cols[c][r] for c in range(len(cols))] for r in range(num_rows)]


# ---------------------------------------------------------------------------
# Step 8 – merge currency-symbol-only columns (fallback for simple tables)
# ---------------------------------------------------------------------------


def _merge_currency_columns(grid: list[list[str]]) -> list[list[str]]:
    """Fallback: collapse a column whose every non-empty cell is a currency symbol.

    This handles simple tables (e.g. a standalone ``$`` column that was not
    caught by ``_merge_currency_prefixes`` because its adjacent cell was empty).
    After passes 3-6 this rarely fires, but it is kept as a safety net.
    """
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
# Step 9 – remove separator rows
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

    grid = _remove_empty_columns(grid)  # pass 1: visual spacer cols
    grid = _merge_currency_prefixes(grid)  # row-level: $ → adjacent value cell
    grid = _remove_empty_columns(grid)  # pass 2: newly-emptied $ cols
    grid = _merge_percent_suffixes(grid)  # row-level: % appended to rate cell
    grid = _deduplicate_columns(grid)  # collapse colspan-duplicate col pairs
    grid = _remove_empty_columns(grid)  # pass 3: residual empties after dedup
    grid = _merge_currency_columns(grid)  # fallback: remaining pure-symbol cols
    grid = _remove_separator_rows(grid)
    grid = [row for row in grid if any(not _is_empty(c) for c in row)]

    if len(grid) < 2:
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
