from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString

from sec2md.absolute_table_parser import AbsolutelyPositionedTableParser
from sec2md.filing_types import build_item_title_lookup_for_type
from sec2md.models import FilingHeader, PeriodType
from sec2md.table_parser import TableParser
from sec2md.utils import clean_text, is_boilerplate

if TYPE_CHECKING:
    from sec2md.filing_types import FilingType


_PART_REGEX = re.compile(r"^PART\s+(I{1,3}|IV|V)\b", re.IGNORECASE)
_ITEM_REGEX = re.compile(r"^(ITEM\s+[1-9][0-9]?[A-C]?(\.\d{2})?)\b\.?", re.IGNORECASE)
_PAGE_NUMBER_REGEX = re.compile(r"^-?\s*(?:[A-Z]-)?[0-9]+\s*-?$", re.IGNORECASE)
_BOLD_STYLE_RE = re.compile(r"font-weight\s*:\s*(?:bold|[7-9]00)", re.IGNORECASE)
_BR_SPLIT_RE = re.compile(r"(?:<br\s*/?>\s*)+", re.IGNORECASE)
_ABS_POS_RE = re.compile(r"position\s*:\s*absolute", re.IGNORECASE)
_UNICODE_BULLETS: frozenset[str] = frozenset({"•", "●", "◦", "·", "\u25e6"})  # noqa: B033
_SENTENCE_TERMINAL: frozenset[str] = frozenset(".!?:;)]\u201d\u2019")
_HEADER_REGEX = re.compile(
    r"^(?P<cik>\d{7,10})\s+"
    r"(?P<fiscal_year>\d{4})\s+"
    r"(?P<period_type>FY|Q[1-4])\s+"
    r"(?P<is_amendment>True|False)\s+"
    r"(?P<taxonomy_url>https?://[^\s#]+)",
    re.IGNORECASE,
)
_FOOTNOTE_PARA_RE = re.compile(r"^(?:[1-9]\d?\s+[A-Z]|Note\s*:)", re.IGNORECASE)
_PAREN_SPACE_RE = re.compile(r"\(\s+([\d,. ]+?)\s+\)")


def _remove_empty_sections(lines: list[str]) -> list[str]:
    """Drop H2 headings that have no body content before the next H1/H2."""
    result: list[str] = []
    n = len(lines)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            has_body = False
            for j in range(i + 1, n):
                if not lines[j]:
                    continue
                if lines[j].startswith("# ") or lines[j].startswith("## "):
                    break
                has_body = True
                break
            if not has_body:
                continue
        result.append(line)
    return result


def _join_broken_paragraphs(lines: list[str]) -> list[str]:
    """Join consecutive prose lines where the prior line ends mid-sentence."""
    result: list[str] = []
    for line in lines:
        if (
            result
            and line
            and line[0].islower()
            and not line.startswith(("#", "|", "-", " "))
            and result[-1]
            and not result[-1].startswith(("#", "|", "-", " "))
            and result[-1][-1] not in _SENTENCE_TERMINAL
        ):
            result[-1] += " " + line
        else:
            result.append(line)
    return result


class Parser:
    _STOP_ITEMS: frozenset[str] = frozenset({"ITEM 15", "ITEM 6.P2"})

    @staticmethod
    def _indent_depth(px: float, base_px: float = 0.0, step_px: float = 18.0) -> int:
        """Convert an absolute CSS left-indent to a relative list-nesting depth.

        Returns 0 for unindented or baseline-level text.  Each additional
        *step_px* of indentation beyond *base_px* increments the depth by 1.
        A half-step tolerance prevents jitter from creating spurious depth changes.
        """
        relative = px - base_px
        if relative < step_px / 2:
            return 0
        return max(1, int(relative / step_px))

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

    @classmethod
    def _is_likely_subheading(cls, tag: Tag, text: str) -> bool:
        """Return True if *tag* looks like a bold/underlined section subheading."""
        if len(text) > 80:
            return False
        style = str(tag.get("style", ""))
        is_bold = (
            "bold" in style
            or "700" in style
            or "800" in style
            or bool(_BOLD_STYLE_RE.search(style))
            or tag.find(["b", "strong"]) is not None
            or cls._is_fully_bold_inline(tag)
        )
        is_underlined = "underline" in style.lower()
        return (is_bold or is_underlined) and not text.endswith(".")

    @staticmethod
    def _is_fully_bold_inline(tag: Tag) -> bool:
        """Detect run-in subheadings rendered via inline-styled bold spans."""
        text_nodes = [node for node in tag.descendants if isinstance(node, NavigableString) and node.strip()]
        if not text_nodes:
            return False

        for node in text_nodes:
            is_bold_run = False
            for ancestor in node.parents:
                if ancestor is tag:
                    break
                if isinstance(ancestor, Tag) and _BOLD_STYLE_RE.search(str(ancestor.get("style", ""))):
                    is_bold_run = True
                    break
            if not is_bold_run:
                return False

        return True

    @classmethod
    def _split_leading_runin_title(cls, block: Tag) -> tuple[str | None, str]:
        """Split a 'Title<br>Paragraph text…' block into ``(title, rest)``."""
        if block.find("br") is None:
            return None, ""

        parts = _BR_SPLIT_RE.split(block.decode_contents(), maxsplit=1)
        if len(parts) != 2:
            return None, ""

        lead_text = clean_text(BeautifulSoup(parts[0], "html.parser").get_text(separator=" "))
        rest_text = clean_text(BeautifulSoup(parts[1], "html.parser").get_text(separator=" "))
        if not lead_text or not rest_text:
            return None, ""

        return lead_text, rest_text

    # ------------------------------------------------------------------
    # Header parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise_item_key(raw: str) -> str:
        """Collapse whitespace and upper-case for stable title-lookup keys."""
        return re.sub(r"\s+", " ", raw).strip().upper()

    @staticmethod
    def _title_redundant(item_text: str, title: str) -> bool:
        """Return True when significant title words already appear in the item text."""
        stop = {"a", "an", "and", "for", "in", "of", "on", "or", "the", "to", "with"}
        sig = {w for w in re.sub(r"[^a-z\s]", "", title.lower()).split() if w not in stop and len(w) > 2}
        item_words = set(re.sub(r"[^a-z\s]", "", item_text.lower()).split())
        return bool(sig) and len(sig & item_words) / len(sig) >= 0.7

    @staticmethod
    def _parse_header(text: str) -> FilingHeader | None:
        """Try to parse *text* as an XBRL filing header line."""
        m = _HEADER_REGEX.match(text.strip())
        if not m:
            return None
        return FilingHeader(
            cik=m.group("cik"),
            fiscal_year=int(m.group("fiscal_year")),
            period_type=cast("PeriodType", m.group("period_type").upper()),
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
        """Pre-render every div that contains ``position:absolute`` children."""
        rendered: dict[int, str] = {}
        skip_ids: set[int] = set()

        for container in soup.find_all("div"):
            if id(container) in skip_ids:
                continue

            abs_children: list[Tag] = [
                child
                for child in container.children
                if isinstance(child, Tag) and _ABS_POS_RE.search(str(child.get("style", "") or ""))
            ]
            if len(abs_children) < 6:
                continue

            abs_parser = AbsolutelyPositionedTableParser(abs_children)
            md = abs_parser.to_markdown() if abs_parser.is_table_like() else abs_parser.to_text()

            if md:
                rendered[id(container)] = md

            for desc in container.descendants:
                if isinstance(desc, Tag):
                    skip_ids.add(id(desc))

        return rendered, skip_ids

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def transform(
        cls, soup: BeautifulSoup, filing_type: FilingType | None = None, stop_items: frozenset[str] | None = None
    ) -> tuple[FilingHeader | None, str]:
        # ---- pre-pass: resolve position:absolute layout blocks ----
        abs_rendered, abs_skip = cls._collect_abs_containers(soup)

        _stop = stop_items if stop_items is not None else cls._STOP_ITEMS
        _indent_base: float | None = None  # first indented block in each item sets this
        _last_h4: str = ""

        item_title_lookup = build_item_title_lookup_for_type(filing_type)

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
                    md = TableParser(block).to_markdown()
                    if md:
                        lines.append(md)
                continue

            if block.find_parent("table"):
                continue
            if block.find(["p", "div", "table"]):
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
            if not body_started and "table of contents" not in _last_h4:
                if _PART_REGEX.match(text) and len(text) < 40:
                    body_started = True
                else:
                    continue

            # ---- normalised body content ----
            if cls._is_page_number(text):
                continue

            if _FOOTNOTE_PARA_RE.match(text):
                lines.append(f"*{text}*")
                continue

            # PART heading → H1
            if _PART_REGEX.match(text) and len(text) < 40:
                lines.append(cls._heading_to_md(1, text.upper()))
                continue

            # # ITEM heading → single H2 combining the item reference and its title
            item_match = _ITEM_REGEX.match(text)
            if item_match and len(text) < 120:
                key = cls._normalise_item_key(item_match.group(1))
                if key in _stop:
                    break
                title = item_title_lookup.get(key)
                heading = (
                    f"{text.upper()} — {title}" if title and not cls._title_redundant(text, title) else text.upper()
                )
                lines.append(cls._heading_to_md(2, heading))
                _indent_base = None

                continue

            # Bold/underlined short block → H3 (major sub-section within an item)
            if cls._is_likely_subheading(block, text):
                _last_h4 = text.lower()
                lines.append(cls._heading_to_md(3, text))
                continue

            # ---- boilerplate stripping (FLS disclaimers, cover-page filler) ----
            if is_boilerplate(text):
                continue

            # # Body paragraph — may have a run-in subheading glued to it via
            # <br> (e.g. "Gross Profit Margin<br>Gross profit margin is …").
            run_in_title, run_in_rest = cls._split_leading_runin_title(block)
            if run_in_title is not None:
                lines.append(cls._heading_to_md(4, run_in_title))
                text = run_in_rest

            m_ind = re.search(
                r"(?:margin|padding)-left\s*:\s*(\d+(?:\.\d+)?)px",
                str(block.get("style", "")),
                re.IGNORECASE,
            )
            px = float(m_ind.group(1)) if m_ind else 0.0
            if px > 0.0 and _indent_base is None:
                _indent_base = px
            depth = cls._indent_depth(px, _indent_base or 0.0)
            for _b in _UNICODE_BULLETS:
                if text.startswith(_b):
                    text = text[len(_b) :].lstrip()
                    if depth == 0:
                        depth = 1
                    break
            lines.append("  " * (depth - 1) + "- " + text if depth > 0 else text)

        # Deduplicate repeated paragraphs
        seen_paragraphs: set[str] = set()
        deduped: list[str] = []
        for line in lines:
            if len(line) > 100 and not line.startswith("#") and not line.startswith("|") and not line.startswith("  "):
                if line in seen_paragraphs:
                    continue
                seen_paragraphs.add(line)
            deduped.append(line)

        deduped = _remove_empty_sections(deduped)
        deduped = _join_broken_paragraphs(deduped)
        markdown = "\n\n".join(deduped).replace("\xa0", " ")
        return header, markdown
