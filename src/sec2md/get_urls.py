import requests


def get_latest_filing_urls(cik: str | int, limit: int = 40) -> list[str]:
    padded_cik = f"{str(cik).zfill(10)}"

    url = f"https://data.sec.gov/submissions/CIK{padded_cik}.json"
    headers = {"User-Agent": "MyDataPipelineAdmin admin@mycompany.com", "Accept-Encoding": "gzip, deflate"}

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    recent_filings = data["filings"]["recent"]

    accession_numbers = recent_filings["accessionNumber"][:limit]
    primary_documents = recent_filings["primaryDocument"][:limit]
    form_types = recent_filings["form"][:limit]

    urls = []
    for acc, doc, form in zip(accession_numbers, primary_documents, form_types, strict=True):
        acc_no_hyphens = acc.replace("-", "")
        filing_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_hyphens}/{doc}"
        if form in ("10-K", "10-Q"):
            urls.append((form, filing_url))

    return urls


if __name__ == "__main__":
    co_cik = 21344

    print(f"Fetching last 10 filings for CIK: {co_cik}...\n")
    latest_filings = get_latest_filing_urls(co_cik, limit=20)

    for i, (form, url) in enumerate(latest_filings, start=1):
        print(f"{i}. [{form}] -> {url}")
