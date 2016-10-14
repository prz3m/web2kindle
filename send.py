import yagmail
from smtplib import SMTPAuthenticationError
import sys
import configparser


def try_login(login):
    try:
        yag = yagmail.SMTP(login)
    except SMTPAuthenticationError:
        print("Wrong password, try again")
        try_login(login)

    return yag


def send(login, file_name, kindle):
    yag = try_login(login)
    yag.send(to=kindle, contents=[file_name + ".mobi"])


config = configparser.ConfigParser()
config.read("web2kindle.conf")
if "web2kindle" in config.keys() and "gmail_login" in config["web2kindle"]:
    login = config["web2kindle"]["gmail_login"]
else:
    login = input("gmail login: ")
if "web2kindle" in config.keys() and "kindle_address" in config["web2kindle"]:
    kindle = config["web2kindle"]["kindle_address"]
else:
    kindle = input("kindle address: ")

send(login, sys.argv[1], kindle)
