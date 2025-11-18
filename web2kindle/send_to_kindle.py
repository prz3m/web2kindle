import yagmail
from smtplib import SMTPAuthenticationError
import configparser
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as CredentialsSA
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64

config = configparser.ConfigParser()
config.read("web2kindle.conf")

SCOPES = [
    'https://www.googleapis.com/auth/gmail.labels',
    'https://www.googleapis.com/auth/gmail.send',
]



def try_login(login):
    yag = None
    try:
        yag = yagmail.SMTP(login)
    except SMTPAuthenticationError:
        print("Wrong password, try again")
        yag = try_login(login)
    return yag


# def send_to_kindle(file_name):
#     yag = try_login(config["web2kindle"]["gmail_login"])
#     print("WILL SEND!")
#     yag.send(to=config["web2kindle"]["kindle_address"], contents=[file_name])

## to refactor lol


def create_message_with_attachment(sender, to, subject, message_text, filename):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    msg = MIMEText(message_text)
    message.attach(msg)

    with open(filename, "rb") as attachment:
        # Add file as application/octet-stream
        # Email client can usually download this automatically as attachment
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())

    part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(filename))

    encoders.encode_base64(part)

    message.attach(part)
    text = message.as_string()

    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')}


def send_to_kindle(file_name):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print('remfresh')
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret_713695827274-5ak7heqn5vf11rf52segves9f2sipol9.apps.googleusercontent.com.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # creds = CredentialsSA.from_service_account_file("web2kindle-348320-1fd22c09dd6f.json")

    try:
        service = build('gmail', 'v1', credentials=creds)

        msg = create_message_with_attachment(
            'pmog3000@gmail.com',
            'pmog3000+amazon_zHewpk_gowno@kindle.com',
            '',
            '',
            file_name,
        )

        response = service.users().messages().send(userId='me', body=msg).execute()
        print('Message Id: ' + response['id'])

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f'An error occurred: {error}')
