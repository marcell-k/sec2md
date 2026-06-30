from pathlib import Path

import requests
from bs4 import BeautifulSoup

from sec2md.parser import Parser


def main() -> None:
    url = "https://www.sec.gov/Archives/edgar/data/21344/000002134415000041/a2015100210-q.htm"
    url = "https://www.sec.gov/Archives/edgar/data/0000021344/000162828026010047/ko-20251231.htm"
    response = requests.get(url, headers={"User-Agent": "sec2md-tests integration@sec2md.dev"}, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    header, markdown = Parser.transform(soup, url=url)
    print(header)

    if header:
        print(f"CIK:          {header['cik']}")
        print(f"Fiscal year:  {header['fiscal_year']}")
        print(f"Period type:  {header['period_type']}")
        print(f"Amendment:    {header['is_amendment']}")
        print(f"Taxonomy URL: {header['taxonomy_url']}")
        print(f"Company:      {header['company_name']}")
        print(f"Tickers:      {header['company_ticker']}")
        print(f"Filing type:  {header['filing_type']}")
        print(f"Accession:    {header['accession_number']}")
        print(f"Period end:   {header['period_end']}")

    Path("out.md").write_text(markdown)


if __name__ == "__main__":
    main()
