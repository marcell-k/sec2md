import re
from typing import TYPE_CHECKING

from sec2md.filing_types import build_item_title_lookup
from sec2md.models import FilingHeader

if TYPE_CHECKING:
    from bs4 import BeautifulSoup
    from bs4.element import Tag


_PART_REGEX = re.compile(r"^PART\s+(I{1,3}|IV|V)\b", re.IGNORECASE)
_ITEM_REGEX = re.compile(r"^(ITEM\s+[1-9][0-9]?[A-C]?(\.\d{2})?)\b\.?", re.IGNORECASE)

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

    # ------------------------------------------------------------------
    # Public transform
    # ------------------------------------------------------------------

    @classmethod
    def transform(cls, soup: BeautifulSoup) -> tuple[FilingHeader | None, str]:
        """
        Parse an SEC filing HTML document and return a ``(header, markdown)``
        tuple.

        *header* contains the XBRL metadata extracted from the first matching
        block, or ``None`` when no header block is present.  Either way the
        header block is never included in *markdown*.
        """
        header: FilingHeader | None = None
        body_started = False
        lines: list[str] = []

        for block in soup.find_all(["p", "div", "table"]):
            # Skip containers that own nested block children (avoids duplication)
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
