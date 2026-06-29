from __future__ import annotations

import re

from bs4 import Tag
from bs4.element import NavigableString

from sec2md.utils import _NIL_MARKER_RE, _PAREN_SPACE_RE, NUMERIC_RE

_WHITESPACE_RE = re.compile(r"^[\s\u00a0]*$")
_CURRENCY_RE = re.compile(r"^[\$€£¥₩()]+$")
_SEPARATOR_RE = re.compile(r"^[-\u2013\u2014_\s\u00a0]+$")
_DEDUP_STRIP_RE = re.compile(r"[\$€£¥₩%,\s]")
_BORDER_TOP_RE = re.compile(r"border-top\s*:[^;]*\b(?:solid|double)\b", re.IGNORECASE)

_CSS_SUPERSCRIPT_RE = re.compile(r"top\s*:\s*-\d", re.IGNORECASE)


def _is_css_superscript(tag: Tag) -> bool:
    if tag.name not in ("span", "sup"):
        return False
    if not _CSS_SUPERSCRIPT_RE.search(str(tag.get("style", ""))):
        return False
    return len(tag.get_text(strip=True)) <= 4


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _cell_text(cell: Tag) -> str:
    parts: list[str] = []
    for node in cell.descendants:
        if not isinstance(node, NavigableString):
            continue
        skip = False
        for ancestor in node.parents:
            if ancestor is cell:
                break
            if getattr(ancestor, "name", None) == "table":
                skip = True
                break
            if isinstance(ancestor, Tag) and _is_css_superscript(ancestor):
                skip = True
                break
        if not skip:
            parts.append(str(node))
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def _is_empty(text: str) -> bool:
    return bool(_WHITESPACE_RE.match(text))


def _is_currency_symbol(text: str) -> bool:
    return bool(text) and bool(_CURRENCY_RE.match(text))


def _escape_pipe(text: str) -> str:
    return text.replace("|", "\\|")


# ---------------------------------------------------------------------------
# Step 1 - build table
# ---------------------------------------------------------------------------


def _build_grid(table: Tag) -> list[list[str]]:
    """Build table."""
    grid: list[list[str | None]] = []

    tr_index = 0

    for tr in table.find_all("tr", recursive=True):
        if tr.find_parent("table") is not table:
            continue

        row_idx = tr_index
        tr_index += 1

        while len(grid) <= row_idx:
            grid.append([])

        col_idx = 0
        for cell in tr.find_all(["td", "th"], recursive=False):
            while col_idx < len(grid[row_idx]) and grid[row_idx][col_idx] is not None:
                col_idx += 1

            text = _cell_text(cell)
            colspan = int(str(cell.get("colspan", "1")))
            rowspan = int(str(cell.get("rowspan", "1")))

            for r in range(rowspan):
                future_row = row_idx + r
                while len(grid) <= future_row:
                    grid.append([])

                target_width = col_idx + colspan
                if len(grid[future_row]) < target_width:
                    grid[future_row].extend([None] * (target_width - len(grid[future_row])))

                for c in range(colspan):
                    grid[future_row][col_idx + c] = text

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
# Step 2 - remove empty columns
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
# Step 3 - merge bare currency-symbol cells into adjacent value cells (row-level)
# ---------------------------------------------------------------------------


def _merge_currency_prefixes(grid: list[list[str]]) -> list[list[str]]:
    """Row-level pass: move a bare currency symbol into the adjacent value cell."""
    result = []
    for row in grid:
        new_row = list(row)
        for c in range(len(new_row) - 1):
            next_val = new_row[c + 1].strip()
            if (
                _is_currency_symbol(new_row[c].strip())
                and not _is_empty(new_row[c + 1])
                and (bool(NUMERIC_RE.search(next_val)) or bool(_NIL_MARKER_RE.match(next_val)))
            ):
                new_row[c + 1] = f"{new_row[c].strip()} {next_val}".strip()
                new_row[c] = ""
        result.append(new_row)
    return result


# ---------------------------------------------------------------------------
# Step 5 - merge bare percent-sign cells into preceding value cells (row-level)
# ---------------------------------------------------------------------------


def _merge_percent_suffixes(grid: list[list[str]]) -> list[list[str]]:
    """Row-level pass: append a bare ``%`` cell to the preceding numeric cell."""
    result = []
    for row in grid:
        new_row = list(row)
        for c in range(1, len(new_row)):
            if new_row[c].strip() == "%" and not _is_empty(new_row[c - 1]) and bool(NUMERIC_RE.search(new_row[c - 1])):
                new_row[c - 1] = f"{new_row[c - 1].strip()}%"
                new_row[c] = ""
        result.append(new_row)
    return result


# ---------------------------------------------------------------------------
# Step 6 - deduplicate adjacent columns
# ---------------------------------------------------------------------------


def _deduplicate_columns(grid: list[list[str]]) -> list[list[str]]:
    """Collapse adjacent columns that carry identical information."""
    if not grid or len(grid[0]) < 2:
        return grid

    num_rows = len(grid)
    num_cols = len(grid[0])

    cols: list[list[str]] = [[grid[r][c] for r in range(num_rows)] for c in range(num_cols)]

    i = 0
    while i < len(cols) - 1:
        a_col, b_col = cols[i], cols[i + 1]
        mergeable = all(_is_empty(va) or _is_empty(vb) or va == vb for va, vb in zip(a_col, b_col, strict=False))
        if mergeable:
            cols[i] = [va if not _is_empty(va) else vb for va, vb in zip(a_col, b_col, strict=False)]
            cols.pop(i + 1)
        else:
            i += 1

    if not cols:
        return []
    return [[cols[c][r] for c in range(len(cols))] for r in range(num_rows)]


# ---------------------------------------------------------------------------
# Step 8 - merge currency-symbol-only columns (fallback for simple tables)
# ---------------------------------------------------------------------------


def _merge_currency_columns(grid: list[list[str]]) -> list[list[str]]:
    """Fallback: collapse a column whose every non-empty cell is a currency symbol."""
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
# Detect total / subtotal rows via border-top CSS (Issue 5)
# ---------------------------------------------------------------------------


def _detect_total_mask(table: Tag) -> list[bool]:
    """Return a per-row bool mask aligned with ``_build_grid``'s row ordering."""
    mask: list[bool] = []
    for tr in table.find_all("tr", recursive=True):
        if tr.find_parent("table") is not table:
            continue
        is_total = bool(_BORDER_TOP_RE.search(str(tr.get("style", ""))))
        if not is_total:
            for td in tr.find_all(["td", "th"], recursive=False):
                if _BORDER_TOP_RE.search(str(td.get("style", ""))):
                    is_total = True
                    break
        mask.append(is_total)
    return mask


# ---------------------------------------------------------------------------
# Fuse two-row spanning headers into one (Issue 4)
# ---------------------------------------------------------------------------


def _fuse_header_rows(grid: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    """Collapse header rows into compound column names."""
    if not grid:
        return [], []

    ncols = len(grid[0])

    # Pattern 1: two-row blank-fill (original logic)
    if len(grid) >= 2:
        row0, row1 = grid[0], grid[1]
        threshold = max(2, ncols // 2)
        blanks_in_row0 = sum(1 for c in row0 if _is_empty(c))
        filled_in_row1 = sum(1 for c in row1 if not _is_empty(c))

        if blanks_in_row0 >= threshold and filled_in_row1 >= threshold:
            fused: list[str] = []
            for top_cell, bot_cell in zip(row0, row1, strict=False):
                top, bot = top_cell.strip(), bot_cell.strip()
                fused.append(f"{top} \u2014 {bot}" if top and bot else top or bot)
            return fused, grid[2:]

    # Pattern 2: multi-level colspan headers
    header_count = 0
    for row in grid:
        non_empty = [c.strip() for c in row if not _is_empty(c)]
        if not non_empty:
            break
        if any(NUMERIC_RE.search(c) for c in non_empty):
            break
        header_count += 1
        if header_count >= 5:  # sanity cap
            break

    if header_count <= 1:
        return (grid[0] if grid else []), grid[1:]

    header_rows = grid[:header_count]
    flat_headers: list[str] = []
    for c in range(ncols):
        parts: list[str] = []
        last = ""
        for row in header_rows:
            val = row[c].strip() if c < len(row) else ""
            if val and val != last:
                parts.append(val)
                last = val
        flat_headers.append(" > ".join(parts) if parts else "")

    return flat_headers, grid[header_count:]


def _normalize_negatives(text: str) -> str:
    """Remove internal whitespace from parenthetical numbers: ``( 11 )`` → ``(11)``."""
    return _PAREN_SPACE_RE.sub(lambda m: f"({m.group(1).strip().replace(' ', '')})", text)


# ---------------------------------------------------------------------------
# Inline XBRL concept extraction — standalone utility (Issue 6)
# ---------------------------------------------------------------------------


def _cell_xbrl_concepts(cell: Tag) -> list[str]:
    """Return XBRL concept names (e.g. ``us-gaap:ProfitLoss``) found in *cell*."""
    return [
        str(tag.get("name"))
        for tag in cell.descendants
        if isinstance(tag, Tag) and getattr(tag, "name", "").startswith("ix:") and tag.get("name")
    ]


def extract_table_xbrl_concepts(table: Tag) -> dict[tuple[int, int], list[str]]:
    """Map raw ``(row_idx, col_idx)`` → XBRL concept names for *table*.

    Indices reflect the original ``<tr>``/``<td>`` structure **before** any
    grid transformations (colspan/rowspan expansion, column dedup, etc.).

    Intended for downstream pipelines that populate ``ChunkMetadata.topics``
    with GAAP/IFRS concept names attached to each numeric figure.
    """
    result: dict[tuple[int, int], list[str]] = {}
    ri = 0
    for tr in table.find_all("tr", recursive=True):
        if tr.find_parent("table") is not table:
            continue
        for ci, cell in enumerate(tr.find_all(["td", "th"], recursive=False)):
            concepts = _cell_xbrl_concepts(cell)
            if concepts:
                result[(ri, ci)] = concepts
        ri += 1
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

    # Snapshot total-row mask before any row-removal steps (indices align with
    # _build_grid's tr_index convention).  Pad to grid length so zip() is safe
    # when rowspan expansion creates more grid rows than <tr> elements.
    total_mask = _detect_total_mask(table)
    while len(total_mask) < len(grid):
        total_mask.append(False)

    grid = _remove_empty_columns(grid)  # pass 1: visual spacer cols
    grid = _merge_currency_prefixes(grid)  # row-level: $ → adjacent value cell
    grid = _remove_empty_columns(grid)  # pass 2: newly-emptied $ cols
    grid = _merge_percent_suffixes(grid)  # row-level: % appended to rate cell
    grid = _deduplicate_columns(grid)  # collapse colspan-duplicate col pairs
    grid = _remove_empty_columns(grid)  # pass 3: residual empties after dedup
    grid = _merge_currency_columns(grid)  # fallback: remaining pure-symbol cols
    # Row-removal steps: keep total_mask in sync so indices stay aligned.
    paired = list(zip(grid, total_mask, strict=False))
    paired = [  # drop separator rows
        (row, m)
        for row, m in paired
        if not (any(not _is_empty(c) for c in row) and all(_SEPARATOR_RE.match(c) for c in row if not _is_empty(c)))
    ]
    paired = [(row, m) for row, m in paired if any(not _is_empty(c) for c in row)]

    if len(paired) < 2:
        return ""

    grid = [row for row, _ in paired]
    total_mask = [m for _, m in paired]

    num_cols = len(grid[0])
    if num_cols == 0:
        return ""

    # Fuse two-row spanning headers; slice the mask to match data_rows.
    header_cells, data_rows = _fuse_header_rows(grid)
    rows_consumed = len(grid) - len(data_rows)
    data_mask = total_mask[rows_consumed:]

    header = [_escape_pipe(_normalize_negatives(c)) for c in header_cells]
    separator = ["---"] * num_cols

    def _fmt(cells: list[str]) -> str:
        return "| " + " | ".join(cells) + " |"

    lines = [_fmt(header), _fmt(separator)]
    for row, is_total in zip(data_rows, data_mask, strict=False):
        escaped = [_escape_pipe(_normalize_negatives(c)) for c in row]
        if is_total:
            escaped = [f"**{c}**" if c.strip() else c for c in escaped]
        lines.append(_fmt(escaped))
    return "\n".join(lines)


def normalize_nil_cells(grid: list[list[str]], nil_marker: str = "\u2014") -> list[list[str]]:
    """Replace empty cells in numeric columns with *nil_marker* (``—`` by default).

    After grid-building, a ``<td></td>`` cell and a span-padded placeholder cell
    are both ``""``, making them indistinguishable.  In columns where more than
    half the non-empty data cells contain digits, an empty cell is almost
    certainly an intentional "not applicable / nil" rather than a structural
    gap — this function restores that semantic for downstream consumers.

    **Not called by** ``table_to_markdown`` — invoke explicitly on the raw grid
    from ``_build_grid`` when your pipeline needs the nil/empty distinction.
    """
    if len(grid) < 2:
        return grid
    result = [list(row) for row in grid]
    for c in range(len(result[0])):
        data_vals = [result[r][c] for r in range(1, len(result))]
        non_empty = [v for v in data_vals if not _is_empty(v)]
        if not non_empty:
            continue
        numeric_frac = sum(1 for v in non_empty if NUMERIC_RE.search(v)) / len(non_empty)
        if numeric_frac > 0.5:
            for r in range(1, len(result)):
                if _is_empty(result[r][c]):
                    result[r][c] = nil_marker
    return result
