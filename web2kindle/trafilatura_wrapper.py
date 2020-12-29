from functools import wraps
from typing import Any

from lxml import html
from trafilatura import extract as _extract


# Fix a regression in trafilatura
# A `graphic` tag is not replaced with a correct `img` HTML tag
# and the images are missing. It should be fixed in the next version
@wraps(_extract)
def extract(*args: Any, **kwargs: Any) -> str | None:
    result = _extract(*args, **kwargs)

    if result is None or "<graphic" not in result:
        return result

    if kwargs.get("output_format") != "html":
        return result

    document = html.fromstring(result)

    for element in document.iter("graphic"):
        element.tag = "img"

    serialized_document = html.tostring(
        document,
        encoding="unicode",
        method="html",
    )
    if not isinstance(serialized_document, str):
        raise TypeError("Expected lxml to serialize HTML as text")
    return serialized_document
