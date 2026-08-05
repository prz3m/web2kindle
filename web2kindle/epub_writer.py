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


@dataclass(frozen=True, slots=True)
class EpubArticle:
    archive_path: str
    title: str
    language: str
    source_url: str
    html_document: bytes
    images: list[EpubImage]


def write_epub(
    output_path: str | Path,
    *,
    title: str,
    language: str,
    identifier: str,
    articles: list[EpubArticle] | None = None,
    html_document: bytes | None = None,
    source_url: str | None = None,
    images: list[EpubImage] | None = None,
) -> None:
    """Write an EPUB 3 publication without external tools.

    The single-article arguments remain available for callers that have not yet
    moved to ``articles``.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if articles is None:
        if html_document is None or source_url is None:
            raise ValueError("A publication must contain at least one article")
        articles = [
            EpubArticle(
                archive_path=ARTICLE_PATH,
                title=title,
                language=language,
                source_url=source_url,
                html_document=html_document,
                images=images or [],
            )
        ]
    elif html_document is not None or source_url is not None or images is not None:
        raise ValueError(
            "Use either 'articles' or the single-article arguments, not both"
        )

    validated_articles = _validate_articles(articles)
    image_count = sum(len(article.images) for article in validated_articles)
    logger.info(
        "Writing EPUB: path=%s title=%r language=%s articles=%d images=%d",
        output_path,
        title,
        language,
        len(validated_articles),
        image_count,
    )

    article_documents = [
        _prepare_xhtml(article.html_document, article.language)
        for article in validated_articles
    ]
    navigation_document = _build_navigation_document(
        validated_articles,
        title,
        language,
    )
    package_document = _build_package_document(
        title=title,
        language=language,
        identifier=identifier,
        articles=validated_articles,
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
            for article, article_document in zip(
                validated_articles,
                article_documents,
                strict=True,
            ):
                archive.writestr(f"EPUB/{article.archive_path}", article_document)
                for image in article.images:
                    archive.writestr(f"EPUB/{image.archive_path}", image.content)

        temporary_path.replace(output_path)
        logger.info(
            "Finished EPUB: path=%s size=%d articles=%d images=%d",
            output_path,
            output_path.stat().st_size,
            len(validated_articles),
            image_count,
        )
    except Exception:
        logger.exception("Failed to write EPUB: path=%s", output_path)
        raise
    finally:
        temporary_path.unlink(missing_ok=True)


def _validate_articles(articles: list[EpubArticle]) -> list[EpubArticle]:
    if not articles:
        raise ValueError("A publication must contain at least one article")

    reserved_paths = {NAVIGATION_PATH, PACKAGE_PATH}
    seen_paths: set[str] = set()

    for article in articles:
        _validate_archive_path(article.archive_path, "article")
        if article.archive_path in reserved_paths:
            raise ValueError(f"Reserved EPUB article path: {article.archive_path!r}")
        if article.archive_path in seen_paths:
            raise ValueError(f"Duplicate EPUB path: {article.archive_path!r}")
        seen_paths.add(article.archive_path)

        for image in article.images:
            _validate_archive_path(image.archive_path, "image")
            if image.archive_path in reserved_paths:
                raise ValueError(f"Reserved EPUB image path: {image.archive_path!r}")
            if image.archive_path in seen_paths:
                raise ValueError(f"Duplicate EPUB path: {image.archive_path!r}")
            if not image.media_type.startswith("image/"):
                raise ValueError(
                    f"Invalid EPUB image media type: {image.media_type!r}"
                )
            seen_paths.add(image.archive_path)

        _validate_image_references(article)

    return articles


def _validate_archive_path(value: str, kind: str) -> None:
    archive_path = PurePosixPath(value)
    if (
        not value
        or "\\" in value
        or archive_path.is_absolute()
        or archive_path.as_posix() != value
        or any(part in {"", ".", ".."} for part in archive_path.parts)
    ):
        raise ValueError(f"Unsafe EPUB {kind} path: {value!r}")


def _validate_image_references(
    article: EpubArticle,
) -> None:
    packaged_paths = {image.archive_path for image in article.images}
    referenced_paths: set[str] = set()
    article_directory = PurePosixPath(article.archive_path).parent
    soup = BeautifulSoup(article.html_document, "html.parser")

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

        referenced_path = PurePosixPath(unquote(parsed_source.path))
        archive_path = (article_directory / referenced_path).as_posix()
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
    articles: list[EpubArticle],
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
    for source_url in dict.fromkeys(article.source_url for article in articles):
        ElementTree.SubElement(
            metadata,
            f"{{{DC_NAMESPACE}}}source",
        ).text = source_url
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
    for article_index, article in enumerate(articles, start=1):
        article_id = (
            "article" if len(articles) == 1 else f"article-{article_index}"
        )
        ElementTree.SubElement(
            manifest,
            "item",
            {
                "id": article_id,
                "href": article.archive_path,
                "media-type": "application/xhtml+xml",
            },
        )
        for image_index, image in enumerate(article.images, start=1):
            image_id = (
                f"image-{image_index}"
                if len(articles) == 1
                else f"image-{article_index}-{image_index}"
            )
            ElementTree.SubElement(
                manifest,
                "item",
                {
                    "id": image_id,
                    "href": image.archive_path,
                    "media-type": image.media_type,
                },
            )

    spine = ElementTree.SubElement(package, "spine")
    if len(articles) > 1:
        ElementTree.SubElement(
            spine,
            "itemref",
            {"idref": "navigation"},
        )
    for article_index, _article in enumerate(articles, start=1):
        article_id = (
            "article" if len(articles) == 1 else f"article-{article_index}"
        )
        ElementTree.SubElement(
            spine,
            "itemref",
            {"idref": article_id},
        )
    return ElementTree.tostring(
        package,
        encoding="utf-8",
        xml_declaration=True,
    )


def _build_navigation_document(
    articles: list[EpubArticle],
    title: str,
    language: str,
) -> bytes:
    html = ElementTree.Element(
        "html",
        {
            "lang": language,
            f"{{{XML_NAMESPACE}}}lang": language,
            "xmlns": XHTML_NAMESPACE,
        },
    )
    head = ElementTree.SubElement(html, "head")
    ElementTree.SubElement(head, "title").text = title
    body = ElementTree.SubElement(html, "body")
    ElementTree.SubElement(body, "h1").text = title
    navigation = ElementTree.SubElement(
        body,
        "nav",
        {f"{{{EPUB_NAMESPACE}}}type": "toc", "id": "toc"},
    )
    ElementTree.SubElement(navigation, "h2").text = "Contents"
    ordered_list = ElementTree.SubElement(navigation, "ol")
    for article in articles:
        list_item = ElementTree.SubElement(ordered_list, "li")
        article_link = ElementTree.SubElement(
            list_item,
            "a",
            {"href": article.archive_path},
        )
        article_link.text = article.title
    return ElementTree.tostring(
        html,
        encoding="utf-8",
        xml_declaration=True,
    )
