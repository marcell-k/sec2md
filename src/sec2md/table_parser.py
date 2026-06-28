from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bs4 import Tag

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

BULLETS = {"•", "●", "◦", "–", "-", "—", "·", ""}


@dataclass
class Cell:
    """A single cell in a table, potentially containing XBRL data"""

    text: str
    rowspan: int = 1
    colspan: int = 1

    def __bool__(self) -> bool:
        return bool(self.text.strip())

    def __repr__(self) -> str:
        return f"Cell(text={self.text!r}, rowspan={self.rowspan}, colspan={self.colspan})"


class GridCell:
    """A cell in the final grid, possibly part of a spanning cell"""

    def __init__(self, cell: Cell, is_spanning: bool = False):
        self.cell = cell
        self.is_spanning = is_spanning

    @property
    def text(self) -> str:
        return self.cell.text if not self.is_spanning else ""

    def __bool__(self) -> bool:
        return bool(self.text.strip())

    def __repr__(self) -> str:
        return f"GridCell(cell={self.cell!r}, is_spanning={self.is_spanning})"


class TableParser:
    """A table within a filing document"""

    def __init__(self, table_element: Tag):
        """
        Initialize table from a BS4 table tag

        Args:
            table_element: The specific table BS4 tag
        """
        if not isinstance(table_element, Tag) or table_element.name != "table":
            raise ValueError("table_element must be a table tag")

        self.table_element = table_element

        self.cells = self._extract_cells()
        self.grid = self._create_grid()

    def _extract_cells(self) -> list[list[Cell]]:
        rows = []
        for tr in self.table_element.find_all("tr"):
            row = []
            for td in tr.find_all(["td", "th"]):
                text = td.get_text(separator=" ", strip=True).replace("\xa0", " ")
                if not text:
                    if td.find("img"):
                        text = "●"
                rowspan = self._safe_parse_int(td.get("rowspan"))
                colspan = self._safe_parse_int(td.get("colspan"))
                row.append(Cell(text=text, rowspan=rowspan, colspan=colspan))
            if row:
                rows.append(row)
        return rows or [[Cell(text="")]]

    @staticmethod
    def _safe_parse_int(value: str, default: int = 1) -> int:
        """Safely parse an integer value, returning default if parsing fails"""
        try:
            if not value or not isinstance(value, str):
                return default
            cleaned = "".join(c for c in value if c.isdigit())
            return int(cleaned) if cleaned else default
        except ValueError, TypeError:
            return default

    def _create_grid(self) -> list[list[GridCell]]:
        """Create grid with spanning cells handled"""
        if not self.cells:
            return []

        max_cols = max(sum(cell.colspan for cell in row) for row in self.cells)
        grid: list[list[GridCell | None]] = [[None for _ in range(max_cols)] for _ in range(len(self.cells))]

        for i, row in enumerate(self.cells):
            col = 0
            for cell in row:
                while col < max_cols and grid[i][col] is not None:
                    col += 1

                if col >= max_cols:
                    break

                grid[i][col] = GridCell(cell)

                for r in range(cell.rowspan):
                    for c in range(cell.colspan):
                        if r == 0 and c == 0:
                            continue
                        ri, ci = i + r, col + c
                        if ri < len(grid) and ci < max_cols:
                            grid[ri][ci] = GridCell(cell, is_spanning=True)

                col += cell.colspan

        grid = self._clean_grid(grid)  # type: ignore[arg-type]
        grid = self._merge_grid(grid)  # type: ignore[arg-type]

        return grid  # type: ignore[return-value]

    def _should_merge_cells(self, val1: GridCell | None, val2: GridCell | None) -> bool:
        """Check if two cells should be merged based on the rules"""
        if not val1 or not val2:
            return True

        s1 = val1.text.strip()
        s2 = val2.text.strip()

        if not s1 or not s2:
            return True

        if self.is_footnote(s2):
            return True

        if s1 == "$":
            return True

        if s2 == "%":
            return True

        return False

    @staticmethod
    def is_footnote(text: str) -> bool:
        """Check if string is a number or letter within square brackets, e.g. [1], [b]"""
        return bool(re.match(r"^\[[a-zA-Z0-9]+\]$", text))

    @staticmethod
    def _clean_grid(
        grid: list[list[GridCell | None]],
    ) -> list[list[GridCell | None]]:
        """Drop rows and columns that contain only empty cells"""
        if not grid:
            return grid

        rows_to_keep = [i for i, row in enumerate(grid) if any(cell is not None and cell.text.strip() for cell in row)]
        columns_to_keep = [
            j
            for j in range(len(grid[0]))
            if any(grid[i][j] is not None and grid[i][j].text.strip() for i in range(len(grid)))
        ]

        return [[grid[i][j] for j in columns_to_keep] for i in rows_to_keep]

    def _merge_grid(self, grid: list[list[GridCell | None]]) -> list[list[GridCell | None]]:
        """Merge columns in one clean pass"""
        if not grid or not grid[0]:
            return grid

        result: list[list[GridCell | None]] = []
        current_col: list[GridCell | None] | None = None

        for col_idx in range(len(grid[0])):
            col = [row[col_idx] for row in grid]

            if current_col is None:
                current_col = col
                continue

            cell_pairs = list(zip(current_col[1:], col[1:]))
            should_merge = all(self._should_merge_cells(c1, c2) for c1, c2 in cell_pairs)

            if should_merge:
                merged: list[GridCell | None] = [current_col[0]]
                for c1, c2 in cell_pairs:
                    if not c1:
                        merged.append(c2)
                    elif not c2:
                        merged.append(c1)
                    else:
                        text = f"{c1.text} {c2.text}".strip()
                        merged.append(GridCell(Cell(text=text)))
                current_col = merged
            else:
                result.append(current_col)
                current_col = col

        if current_col is not None:
            result.append(current_col)

        return list(map(list, zip(*result)))  # type: ignore[arg-type]

    def to_matrix(self) -> list[list[str]]:
        """Convert grid to text matrix"""
        return [[cell.text if cell else "" for cell in row] for row in self.grid]

    def _normalize_text(self, text: str) -> str:
        if text is None:
            return ""
        return str(text).replace("\xa0", " ").strip()

    def _process_headers(self, matrix: list[list[str]]) -> tuple[list[str], list[list[str]]]:
        """Process table headers with smart header fusion."""
        if not matrix or len(matrix) < 1:
            return [], []

        nrows = len(matrix)
        ncols = len(matrix[0]) if matrix else 0

        if nrows < 2:
            return [self._normalize_text(v) for v in matrix[0]], []

        row0 = [self._normalize_text(v) for v in matrix[0]]
        row1 = [self._normalize_text(v) for v in matrix[1]]

        nonempty_row1 = sum(1 for v in row1 if v)
        many_blanks_in_row0 = sum(1 for v in row0 if v == "") >= max(2, ncols // 2)

        if nonempty_row1 >= max(2, ncols // 2) and many_blanks_in_row0:
            fused = []
            for j in range(ncols):
                top = row0[j] if j < len(row0) else ""
                bot = row1[j] if j < len(row1) else ""
                if top and bot:
                    fused.append(f"{top} — {bot}")
                elif top:
                    fused.append(top)
                elif bot:
                    fused.append(bot)
                else:
                    fused.append("")
            return fused, matrix[2:]
        else:
            return row0, matrix[1:]

    def _clean_empty_rows_and_cols(
        self, headers: list[str], data: list[list[str]]
    ) -> tuple[list[str], list[list[str]]]:
        """Remove completely empty rows and columns"""
        if not data:
            return headers, data

        ncols = len(headers)
        cleaned_data = [row for row in data if any(self._normalize_text(cell) for cell in row)]

        if not cleaned_data:
            return headers, []

        cols_with_content: set[int] = set()
        for row in cleaned_data:
            for j, cell in enumerate(row):
                if j < ncols and self._normalize_text(cell):
                    cols_with_content.add(j)

        if not cols_with_content:
            return [], []

        cols_to_keep = sorted(cols_with_content)
        new_headers = [headers[j] for j in cols_to_keep if j < len(headers)]
        new_data = [[row[j] if j < len(row) else "" for j in cols_to_keep] for row in cleaned_data]

        return new_headers, new_data

    def _looks_like_list_table(self) -> bool:
        """Special case — some quirky files format lists as tables"""
        if len(self.cells) != 1:
            return False
        row = self.cells[0]
        texts = [c.text.strip() for c in row]
        has_bullet = any(t in BULLETS for t in texts)
        has_payload = any(t for t in texts[1:])
        return has_bullet and has_payload

    def to_markdown(self) -> str:
        """Convert table to markdown format."""
        if self._looks_like_list_table():
            row = self.cells[0]
            payload = ""
            for c in reversed(row):
                t = c.text.strip()
                if t and t not in BULLETS:
                    payload = t
                    break
            return f"- {payload}" if payload else ""

        matrix = self.to_matrix()
        if not matrix:
            return ""

        headers, data = self._process_headers(matrix)
        headers, data = self._clean_empty_rows_and_cols(headers, data)

        if not headers and not data:
            return ""

        lines = []
        if headers:
            escaped_headers = [str(h).replace("|", "\\|") for h in headers]
            lines.append("| " + " | ".join(escaped_headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        for row in data:
            while len(row) < len(headers):
                row.append("")
            escaped_row = [str(cell).replace("|", "\\|") for cell in row[: len(headers)]]
            lines.append("| " + " | ".join(escaped_row) + " |")

        return "\n".join(lines)

    def md(self) -> str:
        """Alias for to_markdown() for backwards compatibility"""
        return self.to_markdown()
