import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from sec2md.get_urls import get_latest_filing_urls
from sec2md.parser import Parser


def get_md(url: str) -> None:

    response = requests.get(url, headers={"User-Agent": "sec2md-tests integration@sec2md.dev"}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    header, markdown = Parser.transform(soup, url=url)

    DATA_PATH = Path(__file__).parents[3] / "rag" / "data"

    if header:
        print("\n--- SEC Filing Metadata ---")
        print(f"Company:      {header['company_name']}")
        print(f"CIK:          {header['cik']}")
        print(f"Tickers:      {header['company_ticker']}")
        print(f"Fiscal year:  {header['fiscal_year']}")
        print(f"Period type:  {header['period_type']}")
        print(f"Filing type:  {header['filing_type']}")
        print(f"Accession:    {header['accession_number']}")
        print(f"Period end:   {header['period_end']}")
        print(f"Amendment:    {header['is_amendment']}")
        print(f"Taxonomy URL: {header['taxonomy_url']}")

        accession_number_path = DATA_PATH / str(header["cik"]) / str(header["accession_number"])
        accession_number_path.mkdir(parents=True, exist_ok=True)
        file_base_name = f"{header['company_ticker'][0]}_{header['accession_number']}"
        md_file_path = accession_number_path / f"{file_base_name}.md"
        json_file_path = accession_number_path / f"{file_base_name}.json"

        md_file_path.write_text(markdown)
        json_file_path.write_text(json.dumps(header, indent=0))

        print("---------------------------\n")
        print(f"Saved files successfully to: {accession_number_path}")


def main() -> None:
    ciks = [
        "0000789019",  # Microsoft (MSFT)
        "0000320193",  # Apple (AAPL)
        "0001045810",  # NVIDIA (NVDA)
        "0001652044",  # Alphabet / Google (GOOGL)
        "0001018724",  # Amazon (AMZN)
        "0001326801",  # Meta (META)
        "0001067983",  # Berkshire Hathaway (BRK.B)
        "0001318605",  # Tesla (TSLA)
        "0000104169",  # Walmart (WMT)
        "0000019617",  # JPMorgan Chase (JPM)
        "0001418091",  # Twitter / X (Historical)
    ]

    limit = 60
    for cik in ciks:
        urls = get_latest_filing_urls(cik, limit=limit)
        for _, url in urls:
            get_md(url)


if __name__ == "__main__":
    main()
