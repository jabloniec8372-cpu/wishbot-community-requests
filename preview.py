"""Reads the title of a linked page (Open Graph title, then <title>)."""
import urllib.request
from html.parser import HTMLParser


class _TitleParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.og_title = ""
        self.page_title = ""
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("property") == "og:title":
            self.og_title = attrs.get("content") or ""
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.page_title += data


def parse_title(html: str) -> str:
    parser = _TitleParser()
    parser.feed(html)
    return (parser.og_title or parser.page_title).strip()


def fetch_title(url: str, timeout: int = 15) -> str:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Only http(s) links are supported")
    request = urllib.request.Request(url, headers={"User-Agent": "WishBot/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        html = response.read(300_000).decode("utf-8", errors="replace")
    return parse_title(html)
