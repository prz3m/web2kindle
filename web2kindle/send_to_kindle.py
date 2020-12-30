import yagmail
from smtplib import SMTPAuthenticationError
import configparser

config = configparser.ConfigParser()
config.read("web2kindle.conf")


def try_login(login):
    yag = None
    try:
        yag = yagmail.SMTP(login)
    except SMTPAuthenticationError:
        print("Wrong password, try again")
        yag = try_login(login)
    return yag


def send_to_kindle(file_name):
    yag = try_login(config["web2kindle"]["gmail_login"])
    print("WILL SEND!")
    yag.send(to=config["web2kindle"]["kindle_address"], contents=[file_name])
