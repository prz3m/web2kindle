import logging

from pydantic import BaseModel

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web2kindle.converter import Converter

logger = logging.getLogger("web2kindle.server.api")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SendArticlePostRequestModel(BaseModel):
    document: str


@app.post("/")
def send_article_post(
    requestBody: SendArticlePostRequestModel,
    page: str,
):
    logger.info("Sending article: page=%s", page)
    c = Converter(document=requestBody.document, url=page, send_by_mail=True)
    c.convert()
    return "OK"
