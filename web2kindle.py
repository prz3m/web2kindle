import requests
import urllib.request
import subprocess
import os
from readability import Document
from bs4 import BeautifulSoup
import argparse
import configparser
import yagmail
from smtplib import SMTPAuthenticationError

parser = argparse.ArgumentParser(
    description="""
    convert webpage to mobi file""")
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument("-u", "--url", help='webpage url', type=str)
group.add_argument("-p", "--path", help='saved webpage path', type=str)
parser.add_argument("-s",  "--send", help="send to kindle", action="store_true")
args = parser.parse_args()


class Converter:
    def __init__(self, url=None, path=None, send_by_mail=False):
        self.send_by_mail = send_by_mail
        self.url = url
        self.path = path
        if url:
            self.url = url.split("?")[0].strip("/")
            self.file_name = self.url.split("/")[-1].split(".")[0]
        elif path:
            self.path = path.strip("/")
            self.file_name = self.path.split("/")[-1].split(".")[0]
        else:
            raise Exception("what should I convert dumbass?")

        self.img_directory = self.file_name + "_img/"
        if not os.path.exists(self.img_directory):
            os.makedirs(self.img_directory)

        self.headers = {'User-agent': 'Mozilla/5.0'}
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)

    def convert(self):
        if self.url:
            response = requests.get(self.url, headers=self.headers)
            response.encoding = "utf-8"
            doc = Document(response.text.encode("utf-8"))
        elif self.path:
            with open(self.path, 'rb') as f:
                doc = Document(f.read())

        self.title = doc.title() if len(doc.title()) > 0 else "Awesome article"

        self.soup = BeautifulSoup(doc.summary(), 'html.parser')

        self.process_images()
        self.add_head()
        self.insert_title()
        self.save_html()
        try:
            self.convert_to_mobi()
        except FileNotFoundError:
            print("""ERROR: cannot find kindlegen
                  Please download kindlegen from Amazon""")
        if self.send_by_mail:
            self.send_to_kindle()


    def process_images(self):
        for image in self.soup.findAll("img"):
            local_name = self.img_directory + image["src"].split("/")[-1]
            urllib.request.urlretrieve(image["src"], local_name)
            image["src"] = local_name
            image.attrs = {k: v for k, v in image.attrs.items()
                           if k in ["src", "alt"]}

    def add_head(self):
        head_tag = self.soup.new_tag('head')
        self.soup.html.insert(0, head_tag)
        meta_tag = self.soup.new_tag('meta')
        meta_tag.attrs["http-equiv"] = "Content-Type"
        meta_tag.attrs["content"] = "text/html;charset=utf-8"
        self.soup.head.insert(0, meta_tag)
        title_tag = self.soup.new_tag('title')
        title_tag.string = self.title
        self.soup.head.insert(1, title_tag)

    def insert_title(self):
        h1_tag = self.soup.new_tag('h1')
        h1_tag.string = self.title
        self.soup.body.insert(0, h1_tag)

    def save_html(self):
        with open(self.file_name + ".html", "wb") as f:
            f.write(self.soup.prettify().encode("utf-8"))

    def convert_to_mobi(self):
        CREATE_NO_WINDOW = 0x08000000
        if os.path.isfile("kindlegen.exe"):
            kindlegen_path = "kindlegen.exe"
        elif os.path.isfile("kindlegen"):
            kindlegen_path = "kindlegen"
        else:
            raise FileNotFoundError("cannot find kindlegen")
        subprocess.call([kindlegen_path, self.file_name + ".html"],
                        creationflags=CREATE_NO_WINDOW)

    def send_to_kindle(self):
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

        try:
            yag = yagmail.SMTP(login)
        except SMTPAuthenticationError:
            print("Wrong password, try again...")
            self.send_to_kindle()

        yag.send(to=kindle, contents=[self.file_name + ".mobi"])

if __name__ == "__main__":
    c = Converter(args.url, args.path, send_by_mail=args.send)
    c.convert()
