from __future__ import annotations

from typing import Literal, TypedDict

type PeriodType = Literal["FY", "Q1", "Q2", "Q3", "Q4"]


class FilingHeader(TypedDict):
    """Metadata extracted from the XBRL/iXBRL header block at the top of a filing."""

    cik: str
    fiscal_year: int
    period_type: PeriodType
    is_amendment: bool
    taxonomy_url: str
