import base64
import configparser
import logging
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

config = configparser.ConfigParser()
config.read("web2kindle.conf")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
]


def create_message_with_attachment(sender, to, subject, message_text, filename):
    message = MIMEMultipart()
    message["to"] = to
    message["from"] = sender
    message["subject"] = subject

    msg = MIMEText(message_text)
    message.attach(msg)

    with open(filename, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    part.add_header(
        "Content-Disposition", "attachment", filename=os.path.basename(filename)
    )

    encoders.encode_base64(part)
    message.attach(part)

    return {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")}


def send_to_kindle(file_name: str) -> str:
    secrets_dir = Path(os.environ.get("WEB2KINDLE_SECRETS_DIR", "."))
    config_path = secrets_dir / "web2kindle.conf"
    token_path = secrets_dir / "token.json"
    client_secret_path = secrets_dir / "client_secret.json"

    config = configparser.ConfigParser()
    try:
        if not config.read(config_path):
            logger.error("Cannot send article: web2kindle.conf is missing")
            raise RuntimeError("web2kindle.conf is missing")
        sender = config["web2kindle"]["gmail_address"]
        recipient = config["web2kindle"]["kindle_address"]
    except configparser.Error, KeyError, UnicodeError:
        logger.error("Cannot send article: web2kindle.conf is invalid")
        raise RuntimeError("web2kindle.conf is invalid")

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail credentials")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path),
                SCOPES,
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    try:
        service = build("gmail", "v1", credentials=creds)

        msg = create_message_with_attachment(
            sender,
            recipient,
            "",
            "",
            file_name,
        )

        response = service.users().messages().send(userId="me", body=msg).execute()
        logger.info("Sent article to Kindle: message_id=%s", response["id"])
        return response["id"]

    except HttpError:
        logger.exception("Failed to send article through Gmail")
        raise
