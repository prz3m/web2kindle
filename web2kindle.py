import requests
import urllib.request
import subprocess
import os
import time
from readability import Document
from bs4 import BeautifulSoup
import argparse
import configparser
import yagmail
from smtplib import SMTPAuthenticationError
from urllib.parse import urlparse, urljoin
from shutil import copyfile, rmtree
from PIL import Image
from multiprocessing import Process
import threading
import re


class Converter:
    def __init__(self, url=None, path=None, send_by_mail=False, clean=False):
        self.send_by_mail = send_by_mail
        self.clean = clean
        self.url = url
        self.path = path

        self.encoding = "utf-8"

        if url:
            self.url = url.split("?")[0].strip("/")
            # print("url: {}".format(self.url))
            # self.parent_path = "/".join(self.url.split("/")[:-1])
            self.parent_path = urlparse(self.url).scheme + "://" + urlparse(self.url).netloc
            # print(self.url.split("/"))
            print("parent path: {}".format(self.parent_path))
            self.file_name = "w2k_" + self.url.split("/")[-1].split(".")[0]
        elif path:
            self.path = path.replace('\\', '/')
            self.path = self.path.strip("/")
            self.parent_path = "/".join(self.path.split("/")[:-1])
            self.file_name = "w2k_" + self.path.split("/")[-1].split(".")[0]
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
            # print("encoding: {}".format(response.encoding))
            #
            # if response.encoding != "utf-8":
            #     print("apparent_encoding: {}".format(response.apparent_encoding))
            #     response.encoding = response.apparent_encoding
            # self.encoding = response.apparent_encoding
            # doc = Document(response.text.encode("utf-8"))
            # print(response.text)
            # print(response.text.encode(self.encoding)[:400])
            # print("====")
            # print(response.text[:400])
            content = response.content

        elif self.path:
            with open(self.path, 'rb') as f:
                content = f.read()
                # doc = Document(f.read())

        soup = BeautifulSoup(content, 'html.parser')
        try:
            self.encoding = get_encoding(soup)
        except ValueError:
            self.encoding = soup.original_encoding
        doc = Document(content.decode(self.encoding, "ignore"))

        self.title = doc.title() if len(doc.title()) > 0 else "Awesome article"

        # print(doc.summary().encode("utf-8"))
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

            image["src"] = image["src"].strip("//")
            if "." in image["src"].split("/")[0]:
                image["src"] = "http://" + image["src"]
            if len(urlparse(image["src"]).scheme) == 0:
                # image["src"] = self.parent_path + "/" + image["src"]
                image["src"] = urljoin(self.parent_path, image["src"])
                if self.path is not None:
                    local_file = True
            local_name = image["src"].split("/")[-1]
            local_name = local_name.replace("+", "_")

            if "." not in local_name:
                local_name = "{}.{}".format(int(time.time()*10**5), local_name)

            local_path = self.img_directory + local_name
            # print(local_name)
            if not local_file:
                try:
                    urllib.request.urlretrieve(image["src"], local_path)
                except Exception as e:
                    print(image["src"])
                    print(e)

            else:
                copyfile(image["src"], local_path)
            image["src"] = local_path
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
        # meta_tag.attrs["content"] = "text/html;charset=" + self.encoding
        meta_tag.attrs["content"] = "text/html;charset=utf-8"
        self.soup.head.insert(0, meta_tag)
        title_tag = self.soup.new_tag('title')
        title_tag.string = self.title
        self.soup.head.insert(1, title_tag)

    def insert_title(self):
        h1_tag = self.soup.new_tag("h1")
        h1_tag.string = self.title
        self.soup.body.insert(0, h1_tag)
        if self.url:
            tag = self.soup.new_tag("a", href=self.url)
            tag.string = self.url
            self.soup.body.append(self.soup.new_tag("hr"))
            self.soup.body.append(tag)

    def save_html(self):
        with open(self.file_name + ".html", "wb") as f:
            # print(self.soup.prettify().encode("utf-8")[:800])
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
        #
        # t = threading.Thread(target=send, args=(login, self.file_name, kindle))
        # t.start()
        # t.join()

        p = subprocess.Popen(["python", "send.py", self.file_name])
        # p = subprocess.Popen(["send.exe", self.file_name])
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


def get_encoding(soup):
    """
    source: http://stackoverflow.com/a/18359215
    returns encoding from html document's (BeautifulSoup object) meta tags
    """
    encod = soup.meta.get('charset')
    if encod is None:
        encod = soup.meta.get('content-type')
        if encod is None:
            content = soup.meta.get('content')
            match = re.search('charset=(.*)', content, re.IGNORECASE)
            if match:
                encod = match.group(1)
            else:
                raise ValueError('unable to find encoding')
    return encod


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
