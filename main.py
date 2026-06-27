import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup, Tag

from sec2md.parser import Parser

# Strict SEC Regex Patterns (Compiled once for speed)
PART_REGEX = re.compile(r"^PART\s+(I{1,3}|IV|V)\b", re.IGNORECASE)
ITEM_REGEX = re.compile(r"^ITEM\s+[1-9][0-9]?[A-C]?\b\.?", re.IGNORECASE)


def _is_likely_subheading(tag: Tag, text: str) -> bool:
    if len(text) > 80:  # Subheadings are rarely longer than one line
        return False

    style = tag.get("style", "").lower()

    is_bold = "bold" in style or tag.find(["b", "strong"]) is not None
    is_underlined = "underline" in style

    # If it's short, bold, and doesn't end in a period, it's a section header
    return (is_bold or is_underlined) and not text.endswith(".")


def transform_to_semantic_markdown(soup: BeautifulSoup) -> str:
    markdown_lines = []

    # Grab all block containers that usually hold text
    blocks = soup.find_all(["p", "div", "table"])

    for block in blocks:
        if block.find(["p", "div"]):
            continue

        text = block.get_text(separator=" ", strip=True)
        if not text:
            continue

        # 1. Test for PART (H2)
        if PART_REGEX.match(text) and len(text) < 40:
            markdown_lines.append(f"\n## {text.upper()}\n")
            continue

        # 2. Test for ITEM (H3)
        if ITEM_REGEX.match(text) and len(text) < 120:
            markdown_lines.append(f"\n### {text.upper()}\n")
            continue

        # 3. Test for custom bold subheadings (H4)
        if _is_likely_subheading(block, text):
            markdown_lines.append(f"\n#### {text}\n")
            continue

        # Standard body paragraph
        markdown_lines.append(text)

    return "\n\n".join(markdown_lines)


def main():

    from urllib.request import urlopen

    from bs4 import BeautifulSoup

    url = "https://www.sec.gov/Archives/edgar/data/0000021344/000162828026010047/ko-20251231.htm"
    response = requests.get(url, headers={"User-Agent": "sec2md-tests integration@sec2md.dev"}, timeout=30)

    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    text = transform_to_semantic_markdown(soup)
    with Path("out.md").open("w") as f:
        f.write(text)


if __name__ == "__main__":
    print(main())
