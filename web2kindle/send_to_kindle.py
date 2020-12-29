import base64
import configparser
import logging
import os.path
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

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


def send_to_kindle(file_name):
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired Gmail credentials")
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secret.json",
                SCOPES,
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)

        msg = create_message_with_attachment(
            config["web2kindle"]["gmail_address"],
            config["web2kindle"]["kindle_address"],
            "",
            "",
            file_name,
        )

        response = service.users().messages().send(userId="me", body=msg).execute()
        logger.info("Sent article to Kindle: message_id=%s", response["id"])

    except HttpError:
        logger.exception("Failed to send article through Gmail")
