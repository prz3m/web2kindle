import requests
import urllib.request
import subprocess
import os
import time
from readability import Document
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, quote, urlsplit
from urllib.error import HTTPError
from shutil import rmtree, copyfileobj
from PIL import Image
from slugify import slugify_filename  # awesome-slugify
import re
from pathlib import Path

from .send_to_kindle import send_to_kindle

DOCUMENTS_DIR = Path("documents")
HEADERS = {"User-agent": "Mozilla/5.0"}


class Converter:
    def __init__(self, document, url, send_by_mail=False, clean=False):
        self.send_by_mail = send_by_mail
        self.clean = clean
        self.document = document
        self.url = url.split("?")[0].strip("/")

        self.parent_path = urlparse(self.url).scheme + "://" + urlparse(self.url).netloc
        self.file_name = DOCUMENTS_DIR / f'w2k_{self.url.split("/")[-1].split(".")[0]}'
        self.img_directory = f"{self.file_name}_img/"

    def convert(self):
        self._prepare_directories()
        encoding = self._get_document_encoding()

        doc = Document(
            self.document.decode(encoding, "ignore")
            if type(self.document) is not str
            else self.document
        )

        kindle_soup = KindleSoup(
            readability_document=doc,
            source_url=self.url,
            img_directory=self.img_directory,
        )
        html_document = kindle_soup.prepare_formatted_html()
        self._save_html(html_document)
        self.convert_to_mobi()

        if self.send_by_mail:
            send_to_kindle(f"{self.file_name}.mobi")
        if self.clean:
            self.do_cleaning()

    def _prepare_directories(self):
        if not os.path.exists(DOCUMENTS_DIR):
            os.makedirs(DOCUMENTS_DIR)
        if not os.path.exists(self.img_directory):
            os.makedirs(self.img_directory)

    def _get_document_encoding(self):
        soup = BeautifulSoup(self.document, "html.parser")
        try:
            return get_encoding(soup)
        except ValueError:
            return soup.original_encoding

    def _save_html(self, html_document):
        with open(str(self.file_name) + ".html", "wb") as f:
            f.write(html_document)

    def convert_to_mobi(self):
        CREATE_NO_WINDOW = 0x08000000
        if os.path.isfile("kindlegen.exe"):
            kindlegen_path = "kindlegen.exe"
        elif os.path.isfile("kindlegen"):
            kindlegen_path = "kindlegen"
        else:
            raise KindlegenNotFoundError("cannot find kindlegen")
        p = subprocess.Popen(
            [kindlegen_path, str(self.file_name) + ".html"],
            creationflags=CREATE_NO_WINDOW,
        )
        p.wait()

    def do_cleaning(self):
        os.remove(str(self.file_name) + ".mobi")
        os.remove(str(self.file_name) + ".html")
        rmtree(self.img_directory)


def get_encoding(soup):
    """
    source: http://stackoverflow.com/a/18359215
    returns encoding from html document's (BeautifulSoup object) meta tags
    """
    encod = soup.meta.get("charset")
    if encod is None:
        encod = soup.meta.get("content-type")
        if encod is None:
            content = soup.meta.get("content")
            match = re.search("charset=(.*)", content, re.IGNORECASE)
            if match:
                encod = match.group(1)
            else:
                raise ValueError("unable to find encoding")
    return encod


class KindlegenNotFoundError(FileNotFoundError):
    pass


class KindleSoup:
    def __init__(self, readability_document, source_url, img_directory):
        self.document = readability_document
        self.source_url = source_url
        self.parent_path = (
            urlparse(source_url).scheme + "://" + urlparse(source_url).netloc
        )
        self.img_directory = img_directory
        self.soup = BeautifulSoup(readability_document.summary(), "html.parser")

    def prepare_formatted_html(self):
        title = (
            self.document.title() if len(self.document.title()) > 0 else "Unknown title"
        )
        self._add_head(title)
        if len(self.soup.find_all("h1")) == 0:
            self._insert_title(title)
        self._insert_link_to_source()
        self._process_images()

        return self.soup.prettify().encode("utf-8")

    def _process_images(self):
        for image in self.soup.find_all("img"):
            image["src"] = image["src"].strip("//")
            if "." in image["src"].split("/")[0]:
                image["src"] = "http://" + image["src"]
            if len(urlparse(image["src"]).scheme) == 0:
                image["src"] = urljoin(self.parent_path, image["src"])
            local_name = image["src"].split("/")[-1].split("?")[0]
            local_name = slugify_filename(local_name)

            if "." not in local_name:
                local_name = "{}.{}".format(int(time.time() * 10 ** 5), local_name)

            local_name = local_name.encode("ascii", "ignore").decode("ascii")

            local_path = os.path.join(self.img_directory, local_name[-50:])

            try:
                u = urlsplit(image["src"])
                response = requests.get(image["src"], stream=True, headers=HEADERS)
                with open(local_path, "wb") as out_file:
                    response.raw.decode_content = True
                    copyfileobj(response.raw, out_file)

            except HTTPError:
                local_path = "404"

            if local_path != "404":
                local_path = self._resize_image(local_path)

            image["src"] = quote(os.path.relpath(local_path, DOCUMENTS_DIR))
            image.attrs = {k: v for k, v in image.attrs.items() if k in ["src", "alt"]}

    def _add_head(self, title):
        head_tag = self.soup.new_tag("head")
        self.soup.html.insert(0, head_tag)
        meta_tag = self.soup.new_tag("meta")
        meta_tag.attrs["http-equiv"] = "Content-Type"
        meta_tag.attrs["content"] = "text/html;charset=utf-8"
        self.soup.head.insert(0, meta_tag)
        title_tag = self.soup.new_tag("title")
        title_tag.string = "w2k " + title
        self.soup.head.insert(1, title_tag)

    def _insert_title(self, title):
        h1_tag = self.soup.new_tag("h1")
        h1_tag.string = title
        self.soup.body.insert(0, h1_tag)

    def _insert_link_to_source(self):
        tag = self.soup.new_tag("a", href=self.source_url)
        tag.string = self.source_url
        self.soup.body.append(self.soup.new_tag("hr"))
        self.soup.body.append(tag)

    def _resize_image(self, img_path):
        with Image.open(img_path) as im:
            im.thumbnail((800, 800), Image.ANTIALIAS)
            try:
                im.save(img_path)
                return img_path
            except Exception:
                format = im.format
                img_path_with_extension = f"{img_path}.{format}"
                im.save(img_path_with_extension, format=format)
                return img_path_with_extension
