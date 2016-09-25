import yagmail
from smtplib import SMTPAuthenticationError
import sys


def try_login(login):
    try:
        yag = yagmail.SMTP(login)
    except SMTPAuthenticationError:
        print("Wrong password, try again...")
        try_login(login)

    return yag


def send(login, file_name, kindle):
    yag = try_login(login)

    yag.send(to=kindle, contents=[file_name + ".mobi"])


def test(a, b, c):
    print(a, b, c)

send(*sys.argv[1:])
