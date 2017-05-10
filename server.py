import http.server
from urllib.parse import urlparse, parse_qs

from web2kindle import Converter


def get_page(path):
    """
    gets value of page argument in path
    """
    page = parse_qs(urlparse(path).query).get("page", None)
    return page[0] if page else None


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        p = get_page(self.path)

        if p:
            print("Sending article from: {}".format(p))
            c = Converter(url=p, send_by_mail=True)
            c.convert()

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<script>window.close();</script>")


def run(server_class=http.server.HTTPServer, handler_class=http.server.BaseHTTPRequestHandler):
    server_address = ('', 8666)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == "__main__":
    run(handler_class=Handler)
