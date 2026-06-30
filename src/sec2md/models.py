from typing import Literal, NotRequired, TypedDict

type PeriodType = Literal["FY", "Q1", "Q2", "Q3", "Q4"]
type FilingType = Literal["10-K", "10-Q", "20-F", "8-K", "SC 13D", "SC 13G"]

type TopicTag = Literal[
    "revenue_recognition",
    "leases",
    "debt",
    "income_taxes",
    "stock_based_compensation",
    "business_combinations",
    "goodwill_and_intangibles",
    "commitments_and_contingencies",
    "segment_reporting",
    "subsequent_events",
    "fair_value_measurements",
    "derivatives_and_hedging",
    "pension_and_benefits",
    "related_party_transactions",
    "risk_factors",
    "legal_proceedings",
    "internal_controls",
    "executive_compensation",
    "cybersecurity",
    "liquidity_and_capital_resources",
    "other",
]


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
    filing_date: str  # YYYY-MM-DD

    fiscal_year: int
    period_type: PeriodType
    period_end: str  # YYYY-MM-DD

    taxonomy_url: str
    sections: NotRequired[list[DocumentSection]]
