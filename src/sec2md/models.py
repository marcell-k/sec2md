from __future__ import annotations

from typing import TYPE_CHECKING, Literal, TypedDict

if TYPE_CHECKING:
    from sec2md.filing_types import FilingType

type PeriodType = Literal["FY", "Q1", "Q2", "Q3", "Q4"]


class FilingHeader(TypedDict):
    """Metadata extracted from the XBRL/iXBRL header block at the top of a filing."""

    cik: str
    fiscal_year: int
    period_type: PeriodType
    is_amendment: bool
    taxonomy_url: str


class ChunkMetadata(TypedDict):
    # Entity Identifiers
    cik: str
    company_ticker: str | None
    company_name: str

    # Filing Identifiers
    filing_type: FilingType
    filing_date: str  # Format: YYYY-MM-DD
    period_of_report: str | None  # Format: YYYY-MM-DD (End of Q1, Q2, Q3, or FY)
    fiscal_year: int | None
    accession_number: str
    is_amendment: bool  # True if filing_type ends in '/A'

    # Document Hierarchy
    sec_item: str
    sec_title: str
    subsection: str | None

    # Chunk Specifics
    chunk_id: int  # hash (cik + chunk_index)
    chunk_index: int

    # Enrichment
    topics: list[str]

    # Flattened Vector DB Flags
    is_table: bool
    is_footnote: bool
    is_boilerplate: bool
    contains_numbers: bool
