"""Core logic of WishBot: confirmation flow and duplicate catalog.

Pure Python (stdlib only). All network access is injected, so the flow is easy to test.
"""
import re
import sqlite3
import unicodedata

URL_RE = re.compile(r"https?://\S+")
YES = {"yes", "y", "tak", "ok", "ja", "j"}
NO = {"no", "n", "nie", "cancel", "nein"}


def normalize_title(title: str) -> str:
    """Build a duplicate-matching key that works for any language.

    Case-folds, removes accents (so "Żółw" and "zolw" match), turns punctuation into
    single spaces. Letters and digits of every script are kept, so Polish, German or
    Cyrillic titles never collapse into an empty or shared key.
    """
    text = unicodedata.normalize("NFKD", title.casefold().replace("ł", "l"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[\W_]+", " ", text).strip()


class Store:
    """SQLite storage: catalog of already requested/available titles."""

    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS catalog (key TEXT PRIMARY KEY, title TEXT NOT NULL);
            """
        )

    def in_catalog(self, title: str) -> bool:
        row = self.db.execute("SELECT 1 FROM catalog WHERE key = ?", (normalize_title(title),)).fetchone()
        return row is not None

    def add_title(self, title: str) -> None:
        self.db.execute(
            "INSERT OR IGNORE INTO catalog (key, title) VALUES (?, ?)", (normalize_title(title), title)
        )
        self.db.commit()

    def catalog_size(self) -> int:
        return self.db.execute("SELECT COUNT(*) FROM catalog").fetchone()[0]


class RequestFlow:
    """Member message -> title -> confirmation -> duplicate check -> form submission."""

    def __init__(self, store: Store, fetch_title, submit_form):
        self.store = store
        self.fetch_title = fetch_title  # callable(url) -> title
        self.submit_form = submit_form  # callable(title, url, member_name) -> None
        self.pending = {}  # user_id -> (title, url)

    def handle(self, user_id, member_name: str, text: str) -> str:
        user_id = str(user_id)
        text = (text or "").strip()
        if not text:
            return "Send me a title or a link to request it."

        if user_id in self.pending:
            answer = text.lower()
            if answer in YES:
                return self._confirm(user_id, member_name)
            if answer in NO:
                del self.pending[user_id]
                return "Cancelled. Send another title or link any time."
            del self.pending[user_id]  # a new request replaces the old one

        return self._start(user_id, text)

    def _start(self, user_id: str, text: str) -> str:
        match = URL_RE.search(text)
        url = match.group(0) if match else ""
        if url:
            try:
                title = (self.fetch_title(url) or "").strip()
            except Exception:
                return "I could not read that link. Please send the title as text."
        else:
            title = text
        if not normalize_title(title):
            return "I could not find a title there. Please send it as text."

        if self.store.in_catalog(title):
            return f"'{title}' is already in the library. Please check it before requesting."

        self.pending[user_id] = (title, url)
        return f"Is this what you mean?\n{title}\nReply YES to submit or NO to cancel."

    def _confirm(self, user_id: str, member_name: str) -> str:
        title, url = self.pending[user_id]
        try:
            self.submit_form(title, url, member_name)
        except Exception:
            return "The request could not be submitted right now. Reply YES to try again."
        self.store.add_title(title)
        del self.pending[user_id]
        return f"Submitted: {title}"
