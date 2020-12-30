from pydantic import BaseModel

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from web2kindle.converter import Converter

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
def send_article_post(page: str, requestBody: SendArticlePostRequestModel):
    print("Sending article from: {}".format(page))
    c = Converter(document=requestBody.document, url=page, send_by_mail=False)
    c.convert()
    return "OK"
