import logging
import os
import re
import subprocess
import unicodedata
from hashlib import sha256
from pathlib import Path
from shutil import rmtree
from urllib.parse import quote, unquote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup, UnicodeDammit
from bs4.element import Tag
from PIL import Image
from trafilatura import extract, extract_metadata

from .send_to_kindle import send_to_kindle

DOCUMENTS_DIR = Path("documents")
HEADERS = {"User-Agent": "Mozilla/5.0"}
IMAGE_MAX_SIZE = (800, 800)
REQUEST_TIMEOUT_SECONDS = 30

logger = logging.getLogger(__name__)


def _safe_filename(value: str, fallback: str) -> str:
    """Return an ASCII filename containing no path-sensitive characters."""
    ascii_value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if character.isascii()
    )
    sanitized_value = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_value)
    return sanitized_value.strip("._-") or fallback


class Converter:
    def __init__(
        self,
        document: str | bytes,
        url: str,
        send_by_mail: bool = False,
        clean: bool = False,
    ) -> None:
        self.document = document
        self.url = self._normalize_url(url)
        self.send_by_mail = send_by_mail
        self.clean = clean

        parsed_url = urlsplit(self.url)
        source_name = Path(unquote(parsed_url.path)).stem or parsed_url.netloc
        safe_name = _safe_filename(source_name, fallback="article")
        self.file_name = DOCUMENTS_DIR / f"w2k_{safe_name}"
        self.img_directory = Path(f"{self.file_name}_img")

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed_url = urlsplit(url.strip())
        return parsed_url._replace(query="", fragment="").geturl()

    @property
    def html_path(self) -> Path:
        return Path(f"{self.file_name}.html")

    @property
    def epub_path(self) -> Path:
        return Path(f"{self.file_name}.epub")

    def convert(self) -> None:
        self._prepare_directories()
        raw_document = self._decode_document()
        article_html = extract(
            raw_document,
            output_format="html",
            favor_recall=True,
            include_images=True,
        )
        if not article_html:
            raise ValueError("Unable to extract article content from the document")

        metadata = extract_metadata(raw_document)
        metadata_title = metadata.title if metadata else None
        title = self._get_title(raw_document, metadata_title)
        kindle_soup = KindleSoup(
            readability_document=article_html,
            source_url=self.url,
            img_directory=self.img_directory,
            title=title,
        )

        self._save_html(kindle_soup.prepare_formatted_html())
        self.convert_to_epub()

        if self.send_by_mail:
            send_to_kindle(str(self.epub_path))
        if self.clean:
            self.do_cleaning()

    def _prepare_directories(self) -> None:
        DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.img_directory.mkdir(parents=True, exist_ok=True)

    def _decode_document(self) -> str:
        if isinstance(self.document, str):
            return self.document

        decoded_document = UnicodeDammit(self.document, is_html=True).unicode_markup
        if decoded_document is None:
            raise UnicodeError("Unable to decode the source document")
        return decoded_document

    @staticmethod
    def _get_title(raw_document: str, metadata_title: str | None) -> str:
        if metadata_title:
            return metadata_title

        soup = BeautifulSoup(raw_document, "html.parser")
        title_tag = soup.find("title")
        if isinstance(title_tag, Tag) and title_tag.string:
            return title_tag.string.strip()
        return "Article"

    def _save_html(self, html_document: bytes) -> None:
        self.html_path.write_bytes(html_document)

    def convert_to_epub(self) -> None:
        try:
            subprocess.run(
                [
                    "ebook-convert",
                    str(self.html_path),
                    str(self.epub_path),
                    "--no-default-epub-cover",
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"ebook-convert failed with exit code {exc.returncode}:\n{exc.stdout}"
            ) from exc

    def do_cleaning(self) -> None:
        self.epub_path.unlink()
        self.html_path.unlink()
        rmtree(self.img_directory)


def get_encoding(soup: BeautifulSoup) -> str:
    """Return the character encoding declared in an HTML meta tag."""
    charset_meta = soup.find("meta", charset=True)
    if charset_meta:
        charset = charset_meta.get("charset")
        if isinstance(charset, str):
            return charset

    for meta in soup.find_all("meta", content=True):
        content = meta.get("content")
        if not isinstance(content, str):
            continue
        match = re.search(
            r"charset\s*=\s*[\"']?([^;\s\"']+)",
            content,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

    raise ValueError("Unable to find a declared document encoding")


class KindleSoup:
    def __init__(
        self,
        readability_document: str,
        source_url: str,
        img_directory: str | Path,
        title: str,
    ) -> None:
        self.source_url = source_url
        self.img_directory = Path(img_directory)
        self.soup: BeautifulSoup = BeautifulSoup(readability_document, "html.parser")
        self.title = title
        self._ensure_document_structure()

    def _ensure_document_structure(self) -> None:
        html = self.soup.find("html")
        if not isinstance(html, Tag):
            html = self.soup.new_tag("html")
            for child in list(self.soup.contents):
                html.append(child.extract())
            self.soup.append(html)

        body = self.soup.find("body")
        if not isinstance(body, Tag):
            body = self.soup.new_tag("body")
            for child in list(html.contents):
                if getattr(child, "name", None) != "head":
                    body.append(child.extract())
            html.append(body)

    def prepare_formatted_html(self) -> bytes:
        self._add_head(self.title)
        if self.soup.find("h1") is None:
            self._insert_title(self.title)
        self._insert_link_to_source()
        self._process_images()
        formatted_html = self.soup.prettify(encoding="utf-8")
        if not isinstance(formatted_html, bytes):
            raise TypeError("Beautiful Soup returned text despite an output encoding")
        return formatted_html

    def _process_images(self) -> None:
        for image in self.soup.find_all("img"):
            source = image.get("src")
            if not isinstance(source, str) or not source:
                image.decompose()
                continue

            image_url = urljoin(self.source_url, source)
            if urlsplit(image_url).scheme not in {"http", "https"}:
                self._keep_safe_image_attributes(image)
                continue

            local_path = self._download_image(image_url)
            if local_path is None:
                image.decompose()
                continue

            try:
                local_path = self._resize_image(local_path)
            except OSError, ValueError:
                logger.warning("Unable to resize image %s", image_url, exc_info=True)

            relative_path = Path(os.path.relpath(local_path, DOCUMENTS_DIR))
            image["src"] = quote(relative_path.as_posix())
            self._keep_safe_image_attributes(image)

    def _download_image(self, image_url: str) -> Path | None:
        parsed_url = urlsplit(image_url)
        source_name = _safe_filename(
            Path(unquote(parsed_url.path)).name,
            fallback="image",
        )[-40:]
        url_hash = sha256(image_url.encode()).hexdigest()[:12]
        local_path = self.img_directory / f"{url_hash}-{source_name}"

        try:
            with requests.get(
                image_url,
                stream=True,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                response.raise_for_status()
                with local_path.open("wb") as output_file:
                    for chunk in response.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            output_file.write(chunk)
        except OSError, requests.RequestException:
            local_path.unlink(missing_ok=True)
            logger.warning("Unable to download image %s", image_url, exc_info=True)
            return None

        return local_path

    @staticmethod
    def _keep_safe_image_attributes(image: Tag) -> None:
        image.attrs = {
            key: value for key, value in image.attrs.items() if key in {"src", "alt"}
        }

    def _add_head(self, title: str) -> None:
        html = self._required_tag("html")
        head = self.soup.find("head")
        if not isinstance(head, Tag):
            head = self.soup.new_tag("head")
            html.insert(0, head)

        meta_tag = self.soup.new_tag("meta")
        meta_tag.attrs["http-equiv"] = "Content-Type"
        meta_tag.attrs["content"] = "text/html;charset=utf-8"
        head.insert(0, meta_tag)

        title_tag = head.find("title")
        if not isinstance(title_tag, Tag):
            title_tag = self.soup.new_tag("title")
            head.append(title_tag)
        title_tag.string = f"w2k {title}"

    def _insert_title(self, title: str) -> None:
        h1_tag = self.soup.new_tag("h1")
        h1_tag.string = title
        self._required_tag("body").insert(0, h1_tag)

    def _insert_link_to_source(self) -> None:
        source_link = self.soup.new_tag("a", href=self.source_url)
        source_link.string = self.source_url
        body = self._required_tag("body")
        body.append(self.soup.new_tag("hr"))
        body.append(source_link)

    def _required_tag(self, name: str) -> Tag:
        tag = self.soup.find(name)
        if not isinstance(tag, Tag):
            raise ValueError(f"Formatted document is missing its {name!r} element")
        return tag

    @staticmethod
    def _resize_image(image_path: Path) -> Path:
        with Image.open(image_path) as image:
            image_format = image.format
            if image_format is None:
                raise ValueError(f"Unknown image format: {image_path}")
            image.thumbnail(IMAGE_MAX_SIZE, Image.Resampling.LANCZOS)
            image.save(image_path, format=image_format)
        return image_path
