import re
from typing import TYPE_CHECKING

from sec2md.filing_types import build_item_title_lookup
from sec2md.models import FilingHeader
from sec2md.table_utils import table_to_markdown

if TYPE_CHECKING:
    from bs4 import BeautifulSoup
    from bs4.element import Tag


_PART_REGEX = re.compile(r"^PART\s+(I{1,3}|IV|V)\b", re.IGNORECASE)
_ITEM_REGEX = re.compile(r"^(ITEM\s+[1-9][0-9]?[A-C]?(\.\d{2})?)\b\.?", re.IGNORECASE)
_CURRENCY_SYMBOL_RE = re.compile(r"^[\$€£¥]$")


_PAGE_NUMBER_REGEX = re.compile(r"^-?\s*(?:[A-Z]-)?[0-9]+\s*-?$", re.IGNORECASE)

_HEADER_REGEX = re.compile(
    r"^(?P<cik>\d{7,10})\s+"
    r"(?P<fiscal_year>\d{4})\s+"
    r"(?P<period_type>FY|Q[1-4])\s+"
    r"(?P<is_amendment>True|False)\s+"
    r"(?P<taxonomy_url>https?://\S+)",
    re.IGNORECASE,
)

_ITEM_TITLE_LOOKUP: dict[str, str] = build_item_title_lookup()


class Parser:
    @staticmethod
    def _img_to_md(el: Tag) -> str:
        """Convert an <img> element to markdown image syntax."""
        src = el.get("src", "")
        alt = el.get("alt", "")
        if not src:
            return ""
        return f"![{alt}]({src})"

    @staticmethod
    def _heading_to_md(level: int, text: str) -> str:
        """Convert heading text to a markdown heading at the given level (1-6)."""
        return f"{'#' * level} {text}"

    @staticmethod
    def _table_to_md(table: Tag) -> str:
        """Convert <table> to GFM markdown; handles colspan and Workiva-style currency-prefix cells."""
        rows = [tr for tr in table.find_all("tr") if not tr.find_parent("tr")]
        if not rows:
            return ""

        def _text(cell: Tag) -> str:
            return re.sub(r"\s+", " ", cell.get_text(separator=" ", strip=True)).replace("|", "\\|")

        # Step 1: expand colspan into a virtual grid
        max_cols = max(sum(int(c.get("colspan", 1)) for c in r.find_all(["th", "td"])) for r in rows)
        virtual: list[list[str]] = []
        for row in rows:
            vrow = [""] * max_cols
            col = 0
            for cell in row.find_all(["th", "td"]):
                span = int(cell.get("colspan", 1))
                if col < max_cols:
                    vrow[col] = _text(cell)
                col += span
            virtual.append(vrow)

        # Drop fully empty rows
        virtual = [r for r in virtual if any(r)]
        if not virtual:
            return ""

        # Step 2: merge bare currency-symbol cells into the following cell (row-by-row)
        for row in virtual:
            for c in range(max_cols - 1):
                if _CURRENCY_SYMBOL_RE.match(row[c]):
                    row[c + 1] = row[c] + row[c + 1] if row[c + 1] else row[c]
                    row[c] = ""

        # Step 3: consolidate paired columns — where each row has content in at most one
        # Handles the pattern where col N has direct values and col N+1 has $-prefixed values
        for c in range(max_cols - 1):
            c_has = [bool(r[c]) for r in virtual]
            c1_has = [bool(r[c + 1]) for r in virtual]
            if any(c_has) and any(c1_has) and all(not (a and b) for a, b in zip(c_has, c1_has, strict=True)):
                for row in virtual:
                    if row[c + 1]:
                        row[c] = row[c + 1]
                        row[c + 1] = ""

        # Step 4: drop columns that are now fully empty
        keep = [c for c in range(max_cols) if any(r[c] for r in virtual)]
        if not keep:
            return ""

        cleaned = [[row[c] for c in keep] for row in virtual]
        n_cols = len(keep)
        lines = []
        for i, row in enumerate(cleaned):
            lines.append("| " + " | ".join(row) + " |")
            if i == 0:
                lines.append("| " + " | ".join(["---"] * n_cols) + " |")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Block classifiers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_page_number(text: str) -> bool:
        """Return True if *text* looks like a standalone SEC page number."""
        return bool(_PAGE_NUMBER_REGEX.match(text.strip()))

    @staticmethod
    def _is_likely_subheading(tag: Tag, text: str) -> bool:
        """Return True if *tag* looks like a bold/underlined section subheading."""
        if len(text) > 80:
            return False
        style = str(tag.get("style", "")).lower()
        is_bold = "bold" in style or tag.find(["b", "strong"]) is not None
        is_underlined = "underline" in style
        return (is_bold or is_underlined) and not text.endswith(".")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_item_key(raw: str) -> str:
        """Collapse whitespace and upper-case for stable title-lookup keys."""
        return re.sub(r"\s+", " ", raw).strip().upper()

    @staticmethod
    def _parse_header(text: str) -> FilingHeader | None:
        """
        Try to parse *text* as an XBRL filing header line.

        Returns a ``FilingHeader`` on success, ``None`` if the text does not
        match the expected format.
        """
        m = _HEADER_REGEX.match(text.strip())
        if not m:
            return None
        return FilingHeader(
            cik=m.group("cik"),
            fiscal_year=int(m.group("fiscal_year")),
            period_type=m.group("period_type").upper(),
            is_amendment=m.group("is_amendment").capitalize() == "True",
            taxonomy_url=m.group("taxonomy_url"),
        )

    @classmethod
    def transform(cls, soup: BeautifulSoup) -> tuple[FilingHeader | None, str]:
        header: FilingHeader | None = None
        body_started = False
        lines: list[str] = []

        for block in soup.find_all(["p", "div", "table"]):
            if block.name == "table":
                if body_started:
                    md = table_to_markdown(block)
                    if md:
                        lines.append(md)
                continue

            if block.find_parent("table"):
                continue
            if block.find(["p", "div"]):
                continue

            text = block.get_text(separator=" ", strip=True)
            if not text:
                continue

            # Extract XBRL header metadata and strip the block from output
            if header is None:
                parsed = cls._parse_header(text)
                if parsed is not None:
                    header = parsed
                    continue

            # Drop everything before the first PART heading (cover page, TOC, etc.)
            if not body_started:
                if _PART_REGEX.match(text) and len(text) < 40:
                    body_started = True
                else:
                    continue

            # Drop standalone page numbers
            if cls._is_page_number(text):
                continue

            # PART → H2
            if _PART_REGEX.match(text) and len(text) < 40:
                lines.append(cls._heading_to_md(2, text.upper()))
                continue

            # ITEM → H1 (human-readable title) + H3 (item reference)
            item_match = _ITEM_REGEX.match(text)
            if item_match and len(text) < 120:
                key = cls._normalise_item_key(item_match.group(1))
                if key in {"ITEM 15", "ITEM 6.P2"}:
                    break
                title = _ITEM_TITLE_LOOKUP.get(key)
                if title:
                    lines.append(cls._heading_to_md(1, title))
                lines.append(cls._heading_to_md(3, text.upper()))
                continue

            # Bold/underlined short block → H4
            if cls._is_likely_subheading(block, text):
                lines.append(cls._heading_to_md(4, text))
                continue

            # Body paragraph
            lines.append(text)

        return header, "\n\n".join(lines)
