import logging
from threading import Lock

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from web2kindle.article_queue import ArticleQueue
from web2kindle.converter import Converter
from web2kindle.send_to_kindle import send_to_kindle

logger = logging.getLogger("web2kindle.server.api")

app = FastAPI()
article_queue = ArticleQueue()
send_lock = Lock()


class SendArticlePostRequestModel(BaseModel):
    document: str


@app.get("/health")
def health_get():
    return {"status": "ok"}


@app.post("/queue")
def queue_article_post(
    request_body: SendArticlePostRequestModel,
    page: str,
):
    logger.info("Adding article to queue: page=%s", page)
    article = article_queue.add(document=request_body.document, url=page)
    return {
        "status": "queued",
        "identifier": article.identifier,
        "title": article.title,
    }


@app.post("/send-now")
def send_article_now_post(
    request_body: SendArticlePostRequestModel,
    page: str,
):
    logger.info("Sending article immediately: page=%s", page)
    converter = Converter(
        document=request_body.document,
        url=page,
        send_by_mail=True,
    )
    converter.convert()
    return {"status": "sent"}


@app.post("/send")
def send_queued_articles_post():
    if not send_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A queue send is already running")

    try:
        articles = article_queue.pending()
        if not articles:
            return {"status": "empty", "article_count": 0}

        epub_path, batch_id = article_queue.create_epub(articles)
        send_to_kindle(str(epub_path))
        article_queue.mark_sent(articles, batch_id)
        logger.info(
            "Sent queued articles: batch=%s articles=%d epub=%s",
            batch_id,
            len(articles),
            epub_path,
        )
        return {
            "status": "sent",
            "article_count": len(articles),
            "batch_id": batch_id,
            "epub": str(epub_path),
        }
    finally:
        send_lock.release()
