from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bs4.element import Tag


class Parser:
    def __init__(self) -> None:
        pass

    @staticmethod
    def _img_to_md(el: Tag) -> str:
        """Convert an <img> to markdown syntax."""
        src = el.get("src", "")
        alt = el.get("alt", "")
        if not src:
            return ""
        return f"![{alt}]({src})"

    # parse heading to md
