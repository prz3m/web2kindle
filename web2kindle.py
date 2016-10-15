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
from urllib.parse import urlparse
from shutil import copyfile, rmtree
from PIL import Image
from multiprocessing import Process




class Converter:
    def __init__(self, url=None, path=None, send_by_mail=False, clean=False):
        self.send_by_mail = send_by_mail
        self.clean = clean
        self.url = url
        self.path = path

        if url:
            self.url = url.split("?")[0].strip("/")
            self.parent_path = "/".join(self.url.split("/")[:-1])
            self.file_name = self.url.split("/")[-1].split(".")[0]
        elif path:
            self.path = path.replace('\\', '/')
            self.path = self.path.strip("/")
            self.parent_path = "/".join(self.path.split("/")[:-1])
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
        if len(self.soup.find_all("h1")) == 0:
            self.insert_title()
        self.save_html()
        try:
            self.convert_to_mobi()
        except FileNotFoundError:
            print("""ERROR: cannot find kindlegen
                  Please download kindlegen from Amazon""")
        if self.send_by_mail:
            self.send_to_kindle()
        if self.clean:
            self.do_cleaning()

    def process_images(self):
        for image in self.soup.find_all("img"):
            local_file = False
            if len(urlparse(image["src"]).scheme) == 0:
                image["src"] = self.parent_path + "/" + image["src"]
                if self.path is not None:
                    local_file = True
            local_name = self.img_directory + image["src"].split("/")[-1]
            local_name = local_name.replace("+", "_")
            if not local_file:
                urllib.request.urlretrieve(image["src"], local_name)
            else:
                copyfile(image["src"], local_name)
            image["src"] = local_name
            self.resize_image(image["src"])
            image.attrs = {k: v for k, v in image.attrs.items()
                           if k in ["src", "alt"]}

    def resize_image(self, img_path):
        with Image.open(img_path) as im:
            im.thumbnail((800, 800), Image.ANTIALIAS)
            im.save(img_path)

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
        p = subprocess.Popen([kindlegen_path, self.file_name + ".html"],
                             creationflags=CREATE_NO_WINDOW)
        p.wait()

    def send_to_kindle(self):
        # config = configparser.ConfigParser()
        # config.read("web2kindle.conf")
        # if "web2kindle" in config.keys() and "gmail_login" in config["web2kindle"]:
        #     login = config["web2kindle"]["gmail_login"]
        # else:
        #     login = input("gmail login: ")
        # if "web2kindle" in config.keys() and "kindle_address" in config["web2kindle"]:
        #     kindle = config["web2kindle"]["kindle_address"]
        # else:
        #     kindle = input("kindle address: ")

        p = subprocess.Popen(["python", "send.py", self.file_name])
        p.wait()
        # try:
        #     # p = Process(target=yagmail.SMTP, args=(login,))
        #     # p.start()
        #     # p.join()
        #     # yag = p.get()
        #     yag = yagmail.SMTP(login)
        # except SMTPAuthenticationError:
        #     print("Wrong password, try again...")
        #     self.send_to_kindle()
        #
        # yag.send(to=kindle, contents=[self.file_name + ".mobi"])

    def do_cleaning(self):
        os.remove(self.file_name + ".mobi")
        os.remove(self.file_name + ".html")
        rmtree(self.file_name + "_img")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="""
        convert webpage to mobi file""")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-u", "--url", help='webpage url', type=str)
    group.add_argument("-p", "--path", help='saved webpage path', type=str)
    parser.add_argument("-s",  "--send", help="send to kindle", action="store_true")
    parser.add_argument("-c",  "--clean", help="delete created files after sending", action="store_true")

    args = parser.parse_args()

    c = Converter(args.url, args.path, args.send, args.clean)
    c.convert()
