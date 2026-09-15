import html
import re
import unicodedata

from bs4 import BeautifulSoup


_WHITESPACE_RE = re.compile(r"\s+")


def clean_description(raw_html):
    """
    Convert Tiki HTML description into normalized plain text.
    - remove script/style
    - decode HTML entities
    - normalize Unicode
    - collapse repeated whitespace
    """
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "lxml")

    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ")
    text = _WHITESPACE_RE.sub(" ", text).strip()

    return text


def transform(data):
    if not data:
        return None

    images = []
    for image in data.get("images") or []:
        url = (
            image.get("base_url")
            or image.get("large_url")
            or image.get("medium_url")
            or image.get("thumbnail_url")
        )
        if url:
            images.append(url)

    # Stable de-duplication of image URLs.
    images = list(dict.fromkeys(images))

    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "url_key": data.get("url_key"),
        "price": data.get("price"),
        "description": clean_description(data.get("description")),
        "images": images,
    }
