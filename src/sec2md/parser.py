from __future__ import annotations

import re
from typing import TYPE_CHECKING

from bs4 import NavigableString, Tag

from sec2md.absolute_table_parser import AbsolutelyPositionedTableParser
from sec2md.filing_types import build_item_title_lookup
from sec2md.models import FilingHeader
from sec2md.table_utils import table_to_markdown

if TYPE_CHECKING:
    from bs4 import BeautifulSoup


_PART_REGEX = re.compile(r"^PART\s+(I{1,3}|IV|V)\b", re.IGNORECASE)
_ITEM_REGEX = re.compile(r"^(ITEM\s+[1-9][0-9]?[A-C]?(\.\d{2})?)\b\.?", re.IGNORECASE)
_PAGE_NUMBER_REGEX = re.compile(r"^-?\s*(?:[A-Z]-)?[0-9]+\s*-?$", re.IGNORECASE)

# Detects position:absolute in an element's style attribute.
_ABS_POS_RE = re.compile(r"position\s*:\s*absolute", re.IGNORECASE)

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
    # ------------------------------------------------------------------
    # Heading / image helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _img_to_md(el: Tag) -> str:
        """Convert an ``<img>`` element to markdown image syntax."""
        src = el.get("src", "")
        alt = el.get("alt", "")
        if not src:
            return ""
        return f"![{alt}]({src})"

    @staticmethod
    def _heading_to_md(level: int, text: str) -> str:
        """Return a markdown heading at *level* (1-6)."""
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
    # Header parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_item_key(raw: str) -> str:
        """Collapse whitespace and upper-case for stable title-lookup keys."""
        return re.sub(r"\s+", " ", raw).strip().upper()

    @staticmethod
    def _parse_header(text: str) -> FilingHeader | None:
        """Try to parse *text* as an XBRL filing header line."""
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
    # Positioned-element (PDF→HTML) pre-pass
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_abs_containers(
        soup: BeautifulSoup,
    ) -> tuple[dict[int, str], set[int]]:
        """Pre-render every div that contains ``position:absolute`` children.

        SEC filings converted from PDF use hundreds of absolutely positioned
        ``<div>`` elements to simulate a page layout.  This pre-pass groups
        them by their nearest containing ``<div>`` and renders each group with
        ``AbsolutelyPositionedTableParser`` — either as a markdown table (when
        the elements form a grid-like structure) or as plain paragraphed text.

        Returns
        -------
        rendered
            ``{id(container_div): markdown_or_text_string}`` for every
            container that produced non-empty output.
        skip_ids
            ``id()`` values of all descendant elements of handled containers.
            The main loop must skip these to avoid double-processing.
        """
        rendered: dict[int, str] = {}
        skip_ids: set[int] = set()

        for container in soup.find_all("div"):
            # If already inside a handled container, skip.
            if id(container) in skip_ids:
                continue

            # Collect only the direct children that are absolutely positioned.
            abs_children: list[Tag] = [
                child
                for child in container.children
                if isinstance(child, Tag) and _ABS_POS_RE.search(child.get("style", "") or "")
            ]
            # AbsolutelyPositionedTableParser requires at least 6 elements to
            # make any meaningful determination.
            if len(abs_children) < 6:
                continue

            abs_parser = AbsolutelyPositionedTableParser(abs_children)
            if abs_parser.is_table_like():
                md = abs_parser.to_markdown()
            else:
                md = abs_parser.to_text()

            if md:
                rendered[id(container)] = md

            # Mark every descendant so the main loop skips them regardless of
            # whether this container produced output (we don't want individual
            # positioned divs processed as prose paragraphs).
            for desc in container.descendants:
                if isinstance(desc, Tag):
                    skip_ids.add(id(desc))

        return rendered, skip_ids

    # ------------------------------------------------------------------
    # Main transform
    # ------------------------------------------------------------------

    @classmethod
    def transform(cls, soup: BeautifulSoup) -> tuple[FilingHeader | None, str]:
        # ---- pre-pass: resolve position:absolute layout blocks ----
        abs_rendered, abs_skip = cls._collect_abs_containers(soup)

        header: FilingHeader | None = None
        body_started = False
        lines: list[str] = []

        for block in soup.find_all(["p", "div", "table"]):
            # ---- positioned-layout containers (PDF→HTML filings) ----
            if id(block) in abs_skip:
                # Child of a handled container — skip to avoid double output.
                continue
            if id(block) in abs_rendered:
                if body_started:
                    lines.append(abs_rendered[id(block)])
                continue

            # ---- standard HTML tables ----
            if block.name == "table":
                if body_started:
                    md = table_to_markdown(block)
                    if md:
                        lines.append(md)
                continue

            # Skip elements that are inside a <table> (handled above) or that
            # contain nested block elements (we only want leaf text blocks).
            if block.find_parent("table"):
                continue
            if block.find(["p", "div"]):
                continue

            text = block.get_text(separator=" ", strip=True)
            if not text:
                continue

            # ---- XBRL filing-header metadata ----
            if header is None:
                parsed = cls._parse_header(text)
                if parsed is not None:
                    header = parsed
                    continue

            # ---- body gating: drop cover page / TOC content ----
            if not body_started:
                if _PART_REGEX.match(text) and len(text) < 40:
                    body_started = True
                else:
                    continue

            # ---- normalised body content ----
            if cls._is_page_number(text):
                continue

            # PART heading → H2
            if _PART_REGEX.match(text) and len(text) < 40:
                lines.append(cls._heading_to_md(2, text.upper()))
                continue

            # ITEM heading → H1 (human-readable title) + H3 (item reference)
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
