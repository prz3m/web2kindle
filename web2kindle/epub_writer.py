import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from bs4 import BeautifulSoup, Doctype
from bs4.element import Tag

logger = logging.getLogger(__name__)

CONTAINER_NAMESPACE = "urn:oasis:names:tc:opendocument:xmlns:container"
DC_NAMESPACE = "http://purl.org/dc/elements/1.1/"
EPUB_NAMESPACE = "http://www.idpf.org/2007/ops"
OPF_NAMESPACE = "http://www.idpf.org/2007/opf"
XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
XML_NAMESPACE = "http://www.w3.org/XML/1998/namespace"

ARTICLE_PATH = "article.xhtml"
NAVIGATION_PATH = "nav.xhtml"
PACKAGE_PATH = "package.opf"

ElementTree.register_namespace("dc", DC_NAMESPACE)
ElementTree.register_namespace("epub", EPUB_NAMESPACE)


@dataclass(frozen=True, slots=True)
class EpubImage:
    archive_path: str
    media_type: str
    content: bytes


def write_epub(
    output_path: str | Path,
    *,
    html_document: bytes,
    title: str,
    language: str,
    identifier: str,
    source_url: str,
    images: list[EpubImage],
) -> None:
    """Write a single-article EPUB 3 publication without external tools."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validated_images = _validate_images(images)
    _validate_image_references(html_document, validated_images)
    logger.info(
        "Writing EPUB: path=%s title=%r language=%s images=%d",
        output_path,
        title,
        language,
        len(validated_images),
    )

    article_document = _prepare_xhtml(html_document, language)
    navigation_document = _build_navigation_document(title, language)
    package_document = _build_package_document(
        title=title,
        language=language,
        identifier=identifier,
        source_url=source_url,
        images=validated_images,
    )
    container_document = _build_container_document()

    with NamedTemporaryFile(
        dir=output_path.parent,
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        with ZipFile(
            temporary_path,
            mode="w",
            compression=ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            mimetype_entry = ZipInfo("mimetype")
            mimetype_entry.compress_type = ZIP_STORED
            mimetype_entry.create_system = 0
            archive.writestr(
                mimetype_entry,
                b"application/epub+zip",
                compress_type=ZIP_STORED,
            )
            archive.writestr("META-INF/container.xml", container_document)
            archive.writestr(f"EPUB/{PACKAGE_PATH}", package_document)
            archive.writestr(f"EPUB/{NAVIGATION_PATH}", navigation_document)
            archive.writestr(f"EPUB/{ARTICLE_PATH}", article_document)
            for image in validated_images:
                archive.writestr(f"EPUB/{image.archive_path}", image.content)

        temporary_path.replace(output_path)
        logger.info(
            "Finished EPUB: path=%s size=%d images=%d",
            output_path,
            output_path.stat().st_size,
            len(validated_images),
        )
    except Exception:
        logger.exception("Failed to write EPUB: path=%s", output_path)
        raise
    finally:
        temporary_path.unlink(missing_ok=True)


def _validate_images(images: list[EpubImage]) -> list[EpubImage]:
    reserved_paths = {ARTICLE_PATH, NAVIGATION_PATH, PACKAGE_PATH}
    seen_paths: set[str] = set()

    for image in images:
        archive_path = PurePosixPath(image.archive_path)
        if (
            not image.archive_path
            or "\\" in image.archive_path
            or archive_path.is_absolute()
            or archive_path.as_posix() != image.archive_path
            or any(part in {"", ".", ".."} for part in archive_path.parts)
            or image.archive_path in reserved_paths
        ):
            raise ValueError(f"Unsafe EPUB image path: {image.archive_path!r}")
        if image.archive_path in seen_paths:
            raise ValueError(f"Duplicate EPUB image path: {image.archive_path!r}")
        if not image.media_type.startswith("image/"):
            raise ValueError(f"Invalid EPUB image media type: {image.media_type!r}")
        seen_paths.add(image.archive_path)

    return images


def _validate_image_references(
    html_document: bytes,
    images: list[EpubImage],
) -> None:
    packaged_paths = {image.archive_path for image in images}
    referenced_paths: set[str] = set()
    soup = BeautifulSoup(html_document, "html.parser")

    for image_tag in soup.find_all("img"):
        source = image_tag.get("src")
        if not isinstance(source, str) or not source:
            logger.warning("Article contains an image without a usable src")
            continue

        parsed_source = urlsplit(source)
        if parsed_source.scheme or parsed_source.netloc:
            logger.warning(
                "Article image is external and will not be embedded: %s",
                source,
            )
            continue

        archive_path = unquote(parsed_source.path).lstrip("/")
        referenced_paths.add(archive_path)
        if archive_path not in packaged_paths:
            logger.error(
                "Article image is missing from the EPUB package: src=%s",
                source,
            )
            raise ValueError(
                f"Article image is missing from the EPUB package: {source!r}"
            )

    for archive_path in sorted(packaged_paths - referenced_paths):
        logger.warning(
            "EPUB image is packaged but not referenced by the article: %s",
            archive_path,
        )


def _prepare_xhtml(html_document: bytes, language: str) -> bytes:
    soup = BeautifulSoup(html_document, "html.parser")
    for doctype in soup.find_all(string=lambda value: isinstance(value, Doctype)):
        doctype.extract()

    html_tag = soup.find("html")
    if not isinstance(html_tag, Tag):
        raise TypeError("EPUB article is missing its 'html' element")
    if not isinstance(soup.find("head"), Tag):
        raise TypeError("EPUB article is missing its 'head' element")
    if not isinstance(soup.find("body"), Tag):
        raise TypeError("EPUB article is missing its 'body' element")

    html_tag["xmlns"] = XHTML_NAMESPACE
    html_tag["lang"] = language
    html_tag["xml:lang"] = language
    serialized_document = soup.encode("utf-8", formatter="minimal")
    return (
        b'<?xml version="1.0" encoding="utf-8"?>\n'
        b"<!DOCTYPE html>\n" + serialized_document
    )


def _build_container_document() -> bytes:
    container = ElementTree.Element(
        "container",
        {"version": "1.0", "xmlns": CONTAINER_NAMESPACE},
    )
    rootfiles = ElementTree.SubElement(container, "rootfiles")
    ElementTree.SubElement(
        rootfiles,
        "rootfile",
        {
            "full-path": f"EPUB/{PACKAGE_PATH}",
            "media-type": "application/oebps-package+xml",
        },
    )
    return ElementTree.tostring(
        container,
        encoding="utf-8",
        xml_declaration=True,
    )


def _build_package_document(
    *,
    title: str,
    language: str,
    identifier: str,
    source_url: str,
    images: list[EpubImage],
) -> bytes:
    package = ElementTree.Element(
        "package",
        {
            "version": "3.0",
            "unique-identifier": "publication-id",
            "xmlns": OPF_NAMESPACE,
        },
    )
    metadata = ElementTree.SubElement(package, "metadata")
    identifier_tag = ElementTree.SubElement(
        metadata,
        f"{{{DC_NAMESPACE}}}identifier",
        {"id": "publication-id"},
    )
    identifier_tag.text = identifier
    ElementTree.SubElement(metadata, f"{{{DC_NAMESPACE}}}title").text = title
    ElementTree.SubElement(metadata, f"{{{DC_NAMESPACE}}}language").text = language
    ElementTree.SubElement(metadata, f"{{{DC_NAMESPACE}}}source").text = source_url
    modified = ElementTree.SubElement(
        metadata,
        "meta",
        {"property": "dcterms:modified"},
    )
    modified.text = (
        datetime.now(UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    manifest = ElementTree.SubElement(package, "manifest")
    ElementTree.SubElement(
        manifest,
        "item",
        {
            "id": "navigation",
            "href": NAVIGATION_PATH,
            "media-type": "application/xhtml+xml",
            "properties": "nav",
        },
    )
    ElementTree.SubElement(
        manifest,
        "item",
        {
            "id": "article",
            "href": ARTICLE_PATH,
            "media-type": "application/xhtml+xml",
        },
    )
    for index, image in enumerate(images, start=1):
        ElementTree.SubElement(
            manifest,
            "item",
            {
                "id": f"image-{index}",
                "href": image.archive_path,
                "media-type": image.media_type,
            },
        )

    spine = ElementTree.SubElement(package, "spine")
    ElementTree.SubElement(
        spine,
        "itemref",
        {"idref": "article"},
    )
    return ElementTree.tostring(
        package,
        encoding="utf-8",
        xml_declaration=True,
    )


def _build_navigation_document(title: str, language: str) -> bytes:
    html = ElementTree.Element(
        "html",
        {
            "lang": language,
            f"{{{XML_NAMESPACE}}}lang": language,
            "xmlns": XHTML_NAMESPACE,
        },
    )
    head = ElementTree.SubElement(html, "head")
    ElementTree.SubElement(head, "title").text = "Contents"
    body = ElementTree.SubElement(html, "body")
    navigation = ElementTree.SubElement(
        body,
        "nav",
        {f"{{{EPUB_NAMESPACE}}}type": "toc", "id": "toc"},
    )
    ElementTree.SubElement(navigation, "h1").text = "Contents"
    ordered_list = ElementTree.SubElement(navigation, "ol")
    list_item = ElementTree.SubElement(ordered_list, "li")
    article_link = ElementTree.SubElement(
        list_item,
        "a",
        {"href": ARTICLE_PATH},
    )
    article_link.text = title
    return ElementTree.tostring(
        html,
        encoding="utf-8",
        xml_declaration=True,
    )
