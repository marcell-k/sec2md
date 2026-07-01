from typing import Literal, NotRequired, TypedDict

type PeriodType = Literal["FY", "Q1", "Q2", "Q3", "Q4"]
type FilingType = Literal["10-K", "10-Q", "20-F", "8-K", "SC 13D", "SC 13G"]


# ---------- FilingHeader ----------
class DocumentSection(TypedDict):
    """One Item/Part as it appears in the converted markdown."""

    item_id: str  # e.g. "Item 7" — must match ChunkMetadata.sec_item
    title: str
    start_line: int
    end_line: int


class FilingHeader(TypedDict):
    """Metadata extracted from the XBRL/iXBRL header block at the top of a filing."""

    schema_version: str

    cik: str
    company_name: str
    company_ticker: list[str]

    filing_type: FilingType
    is_amendment: bool
    accession_number: str

    fiscal_year: int
    period_type: PeriodType
    period_end: str  # YYYY-MM-DD

    taxonomy_url: str
    sections: NotRequired[list[DocumentSection]]
