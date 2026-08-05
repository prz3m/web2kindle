import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PurePosixPath
from shutil import rmtree
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from bs4 import BeautifulSoup

from .converter import DOCUMENTS_DIR, Converter
from .epub_writer import EpubArticle, EpubImage, write_epub

logger = logging.getLogger(__name__)

QUEUE_DIRECTORY = DOCUMENTS_DIR / "queue"


def collection_title(created_at: datetime) -> str:
    """Return the publication title for a queued collection."""
    return f"web2kindle — {created_at:%Y-%m-%d %H:%M UTC}"


@dataclass(frozen=True, slots=True)
class QueuedArticle:
    identifier: str
    title: str
    language: str
    source_url: str
    captured_at: str
    directory: Path

    @property
    def html_path(self) -> Path:
        return self.directory / "article.html"


class ArticleQueue:
    def __init__(self, root: str | Path = QUEUE_DIRECTORY) -> None:
        self.root = Path(root)
        self.pending_directory = self.root / "pending"
        self.sent_directory = self.root / "sent"
        self.staging_directory = self.root / ".staging"
        self.epub_directory = self.root / "epubs"

    def add(self, document: str | bytes, url: str) -> QueuedArticle:
        self._prepare_directories()
        captured_at = datetime.now(UTC).isoformat()
        identifier = uuid4().hex
        staging_path = self.staging_directory / identifier
        pending_path = self.pending_directory / identifier

        try:
            converter = Converter(
                document=document,
                url=url,
                output_directory=staging_path,
            )
            prepared = converter.prepare()
            metadata = {
                "identifier": identifier,
                "title": prepared.title,
                "language": prepared.language,
                "source_url": prepared.source_url,
                "captured_at": captured_at,
            }
            (staging_path / "metadata.json").write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            staging_path.replace(pending_path)
        except Exception:
            rmtree(staging_path, ignore_errors=True)
            raise

        article = self._load_article(pending_path)
        logger.info(
            "Added article to queue: id=%s title=%r url=%s",
            article.identifier,
            article.title,
            article.source_url,
        )
        return article

    def pending(self) -> list[QueuedArticle]:
        self._prepare_directories()
        articles = [
            self._load_article(path)
            for path in self.pending_directory.iterdir()
            if path.is_dir()
        ]
        return sorted(
            articles,
            key=lambda article: (article.captured_at, article.identifier),
        )

    def create_epub(
        self,
        queued_articles: list[QueuedArticle],
    ) -> tuple[Path, str]:
        if not queued_articles:
            raise ValueError("Cannot create an EPUB from an empty queue")

        self._prepare_directories()
        created_at = datetime.now(UTC)
        batch_id = created_at.strftime("%Y%m%dT%H%M%S%fZ")
        title = collection_title(created_at)
        output_path = self.epub_directory / f"web2kindle_{batch_id}.epub"
        identifier_source = "\n".join(
            article.identifier for article in queued_articles
        )
        publication_identifier = (
            f"urn:sha256:{sha256(identifier_source.encode()).hexdigest()}"
        )
        epub_articles = [
            self._to_epub_article(article) for article in queued_articles
        ]
        write_epub(
            output_path,
            title=title,
            language=queued_articles[0].language or "en",
            identifier=publication_identifier,
            articles=epub_articles,
        )
        return output_path, batch_id

    def mark_sent(
        self,
        queued_articles: list[QueuedArticle],
        batch_id: str,
    ) -> None:
        batch_directory = self.sent_directory / batch_id
        batch_directory.mkdir(parents=True, exist_ok=False)
        for article in queued_articles:
            source_path = self.pending_directory / article.identifier
            if source_path.is_dir():
                source_path.replace(batch_directory / article.identifier)
        logger.info(
            "Marked queued articles as sent: batch=%s articles=%d",
            batch_id,
            len(queued_articles),
        )

    def _to_epub_article(self, article: QueuedArticle) -> EpubArticle:
        html_document = article.html_path.read_bytes()
        soup = BeautifulSoup(html_document, "html.parser")
        article_archive_path = f"articles/{article.identifier}/article.xhtml"
        article_archive_directory = PurePosixPath(article_archive_path).parent
        images: dict[str, EpubImage] = {}

        for image_tag in soup.find_all("img"):
            source = image_tag.get("src")
            if not isinstance(source, str) or not source:
                continue
            parsed_source = urlsplit(source)
            if parsed_source.scheme or parsed_source.netloc:
                continue

            relative_source = unquote(parsed_source.path).lstrip("/")
            image_path = (article.directory / relative_source).resolve()
            if (
                not relative_source
                or not image_path.is_relative_to(article.directory.resolve())
                or not image_path.is_file()
            ):
                raise ValueError(
                    f"Queued article has an invalid image reference: {source!r}"
                )

            archive_path = (
                article_archive_directory / PurePosixPath(relative_source)
            ).as_posix()
            images[archive_path] = EpubImage(
                archive_path=archive_path,
                media_type=Converter._image_media_type(image_path),
                content=image_path.read_bytes(),
            )

        return EpubArticle(
            archive_path=article_archive_path,
            title=article.title,
            language=article.language or "en",
            source_url=article.source_url,
            html_document=html_document,
            images=list(images.values()),
        )

    def _prepare_directories(self) -> None:
        self.pending_directory.mkdir(parents=True, exist_ok=True)
        self.sent_directory.mkdir(parents=True, exist_ok=True)
        self.staging_directory.mkdir(parents=True, exist_ok=True)
        self.epub_directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _load_article(directory: Path) -> QueuedArticle:
        metadata = json.loads(
            (directory / "metadata.json").read_text(encoding="utf-8")
        )
        return QueuedArticle(
            identifier=metadata["identifier"],
            title=metadata["title"],
            language=metadata["language"],
            source_url=metadata["source_url"],
            captured_at=metadata["captured_at"],
            directory=directory,
        )
